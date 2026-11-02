"""Read an independently recalculated COPY of the closed workbook; never modify accounting sources.
Output is private member-report HTML, not a static-public asset.
"""
import argparse
import datetime
import collections
import hashlib
import html
import json
import re
from pathlib import Path

COLS = [3,4,5,7,8,9,11,12,13,15,16,17]
CATEGORIES = {'급여':'경상비','복리후생비':'경상비','사무비':'경상비','식음료비(경상)':'경상비','사무실임차료':'경상비','CMS비용':'경상비','대여금':'경상비','강사비':'사업비','연구지원비':'사업비','식음료비(사업)':'사업비','장소사용료':'사업비','홍보비':'사업비','행사비':'사업비','참가비환불':'사업비','퇴직금':'퇴직금','차입금변제':'기타지출','잡지출':'기타지출'}
# Human-confirmation items stay unconfirmed until the user answers; override with --notes / --questions JSON files.
DEFAULT_NOTES=[dict(months=[8],text='8월 사업비가 늘어난 주된 이유는 세미나 강사료 지급이 한 달에 모였기 때문입니다. 지급 대상 역할·단가·일부 지급 여부는 확인 대기이며, 확정 전에는 장부를 바꾸지 않았습니다.')]
DEFAULT_QUESTIONS=['8/5 동일 금액 지급 건의 강의 역할 확인 대기','강사료 단가 차이의 지급 기준 확인 대기','7/28 강의분 지급 여부·다른 지급 경로 확인 대기']
CSP="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'"


SAFE_NAMES = ('한빛누리','아지트솜니움','한예연')
ORG = r'[가-힣A-Za-z·㈜]{1,40}(교회|연구소|주식회사|재단|통신|은행|공사)'
DELIVERY = re.compile('배달|배민|요기요|쿠팡이츠')
CARD_ONLY_FROM = 10  # 2026-10 onward: card only, delivery orders are the only proxy-payment exception (사용자 지시 2026-11-02)
CARD_RULE = '2026년 10월부터는 카드 사용이 원칙이며, 배달 주문만 대표 대납의 예외입니다.'


def mask_person(s):
    """김*환 / 김* / 남궁*수: keep the surname part and the last character only."""
    if len(s) == 2:
        return s[0] + '*'
    if len(s) == 3:
        return s[0] + '*' + s[2]
    return s[:2] + '*' * (len(s) - 3) + s[-1]


def kind_of(value):
    s = str(value or '').strip()
    if s in SAFE_NAMES or re.fullmatch(ORG, s) or (re.fullmatch(r'[가-힣]{2,4}', s) and s.endswith(('교회','재단','은행'))):
        return 'org'
    return 'person' if re.fullmatch(r'[가-힣]{2,4}', s) else 'none'


def mask_name(value, anonymous=frozenset()):
    s = str(value or '').strip()
    # Whitelist the shape of a name, never copy arbitrary bank memos or phone/account numbers.
    if s in anonymous:
        return '익명'
    k = kind_of(s)
    if k == 'org':
        return s
    if k == 'person':
        return mask_person(s)
    return '내역 비공개' if s else '미기록'


class People:
    """Stable anonymous index per distinct raw name (for «1~2명뿐인 항목은 합계만»); raw names never leave this object
    except for the leak check in build()."""
    def __init__(self, anonymous=(), aliases=None):
        # aliases: raw name -> neutral label shown instead of a masked name (e.g. a sole designer -> «디자이너»)
        self.ids = {}; self.anonymous = frozenset(anonymous); self.aliases = dict(aliases or {})
    def pid(self, value):
        s = str(value or '').strip()
        s = self.aliases.get(s, s)
        if s in self.aliases.values() or s in self.anonymous or kind_of(s) != 'none':
            return self.ids.setdefault(s, len(self.ids) + 1)
        return None
    def mask(self, value):
        s = str(value or '').strip()
        return self.aliases.get(s) or mask_name(s, self.anonymous)
    def raw_person_names(self):
        return ({n for n in self.ids if (kind_of(n) == 'person' or n in self.anonymous) and n not in self.aliases.values()}) | set(self.aliases)


def number(value):
    if type(value) not in (int,float):
        raise ValueError('missing or invalid recalculated amount')
    return round(value)


def month_states(w):
    """Month -> '확정' | '잠정' from the workbook's own reconciliation verdicts (대사 sheet, 판정 column).
    A month is 확정 only if every batch of that month says OK; any other verdict than OK/잠정 refuses."""
    states = {}
    for r in list(w['대사'].values)[4:]:
        batch = re.match(r'26-(\d{2})', str(r[0] or ''))
        if not batch:
            continue
        verdict = str(r[4] or '').strip() if len(r) > 4 else ''
        if verdict not in ('OK', '잠정'):
            raise ValueError('unknown reconciliation verdict: ' + verdict)
        m = int(batch[1])
        states[m] = '잠정' if verdict == '잠정' or states.get(m) == '잠정' else '확정'
    return states


def closed_through(w, states):
    """Last month of the unbroken run of months that have reconciliation rows and a numeric-zero bank check."""
    summary = w['결산']
    n = 0
    for m in range(1, 13):
        v = summary.cell(3, COLS[m-1]).value
        if m in states and type(v) in (int, float) and v == 0:
            n = m
        else:
            break
    return n


def extract_donors(w, sheets, through, previous, people):
    """후원자현황 (masked names) and 후원자_변동 (CMS 신규/중단) for the closed months only."""
    import openpyxl
    rows = list(w['후원자현황'].values)
    head = next(i for i, r in enumerate(rows) if r[0] == '후원자명')
    donors = []
    for r in rows[head+1:]:
        name, cat = str(r[0] or '').strip(), str(r[1] or '').strip()
        if not name or not cat or '소계' in name or '합계' in name:
            continue
        values = [number(r[2+i]) if r[2+i] is not None else 0 for i in range(through)]
        if not any(values):
            continue
        if '익명' in str(r[18] or '') and kind_of(name) != 'none':
            people.anonymous = people.anonymous | {name}
        donors.append(dict(name=people.mask(name), pid=people.pid(name), category=cat, values=values, _raw=name))
    for d in donors:  # re-mask after the whole sheet was scanned for anonymity marks
        d['name'] = people.mask(d.pop('_raw'))
    change = None
    if '후원자_변동' in sheets:
        prior = {}
        if previous:
            pw = openpyxl.load_workbook(previous, data_only=True, read_only=True)
            for r in list(pw.active.values)[2:]:
                if r[1] == '한빛누리CMS':
                    nz = [number(c or 0) for c in r[2:14] if number(c or 0)]
                    prior[str(r[0]).strip()] = nz[-1] if nz else 0
        paid = {}
        for r in rows[head+1:]:
            if str(r[1] or '').strip() == '한빛누리CMS후원금':
                vs = [number(r[2+i]) if r[2+i] is not None else 0 for i in range(through)]
                paid[str(r[0]).strip()] = vs
        new, stopped, section = [], [], None
        for r in w['후원자_변동'].values:
            c0 = str(r[0] or '')
            if c0.startswith('★'): section = 'new'
            elif c0.startswith('■'): section = 'stop'
            elif c0.startswith('●') or c0.startswith('※'): section = None
            elif section and r[1]:
                n = str(r[1]).strip()
                vs = paid.get(n, [0]*through)
                if section == 'new':
                    m = re.search(r'월\s*([\d,]+)\s*원', str(r[3] or ''))
                    if not m:
                        raise ValueError('new CMS donor without monthly amount')
                    new.append(dict(name=people.mask(n), pid=people.pid(n), monthly=int(m[1].replace(',', ''))))
                else:
                    if previous and n not in prior:
                        raise ValueError('stopped CMS donor missing from 2025 data')
                    stopped.append(dict(name=people.mask(n), pid=people.pid(n), last2025=prior.get(n)))
        change = dict(new=new, stopped=stopped,
                      monthly_delta=sum(x['monthly'] for x in new) - sum(x['last2025'] or 0 for x in stopped))
    return donors, change


def confirmed_notes(path):
    """수기확인.csv 사유 by (거래일시, 금액): the human-written memo attached to a ledger row (read only)."""
    if not path:
        return {}
    import csv
    out = {}
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(l for l in f if not l.lstrip().startswith('#')):
            try:
                out[(r['거래일시'], int(r['금액']))] = r['사유']
            except (KeyError, ValueError, TypeError):
                continue
    return out


def extract_proxy(w, sheets, through, ledger, people, fixed=(), notes=None):
    """대표대납_정산 rows matched one-to-one against the bank ledger. Anything unmatched, a changed account, or a
    returned amount (possible reimbursement) means a possible double count: refuse instead of publishing."""
    ledger_out = collections.defaultdict(list)
    for i, r in enumerate(ledger):
        if r[1] and (r[3] or 0) > 0:
            ledger_out[(str(r[1])[:16], str(r[2]).strip(), round(r[3]))].append((i, r))
    used, rows, sheet_total, sheet_rows = set(), [], None, []
    for r in w['대표대납_정산'].values:
        if str(r[2] or '').strip() == '합계' and type(r[3]) in (int, float):
            sheet_total = round(r[3])
        if re.fullmatch(r'\d+', str(r[0] or '')):
            sheet_rows.append(r)
    if sheet_total is not None and sheet_total != sum(round(r[3]) for r in sheet_rows):
        raise ValueError('proxy sheet total differs from its rows')
    names = {str(r[2]).strip() for r in sheet_rows}
    if any((r[4] or 0) > 0 and str(r[2]).strip() in names for r in ledger):
        raise ValueError('possible proxy reimbursement in ledger: stop and ask a person')
    for r in sheet_rows:
        month = int(r[0])
        key = (str(r[1])[:16], str(r[2]).strip(), round(r[3]))
        cand = [x for x in ledger_out.get(key, []) if x[0] not in used]
        if not cand:
            raise ValueError('proxy payment not found once in the bank ledger: possible double count')
        used.add(cand[0][0]); lr = cand[0][1]
        final = str(r[6] or r[5] or '')
        if str(lr[9] or '') != final:
            raise ValueError('proxy account differs from ledger account')
        if month > through:
            continue
        memo = (notes or {}).get((str(lr[1]), round(r[3])), '')
        delivery = bool(DELIVERY.search(' '.join(str(x or '') for x in (r[4], lr[6], lr[7], lr[8], memo))))
        status = '상계 제외' if final == '상계(제외)' else ('정정 반영' if r[6] else '자동분류')
        regular = next((f for f in fixed if str(r[2]).strip() in f['names']), None)
        row = dict(month=month, date=str(r[1])[:10].replace('.', '-'), name=people.mask(r[2]), pid=people.pid(r[2]),
                   amount=round(r[3]), account=final, status=status)
        if regular:
            # person-to-person standing payment (not a card/proxy case): shown apart, never flagged by the card rule
            row.update(regular=regular['label'], via=str(lr[8] or ''))
        elif month >= CARD_ONLY_FROM:
            row['rule'] = '배달 예외(확인됨)' if delivery and '영수증' in memo else ('배달 예외' if delivery else '배달 표시 없음')
        rows.append(row)
    regular_info = [dict(label=f['label'], note=f.get('note', '')) for f in fixed]
    return dict(rows=[x for x in rows if 'regular' not in x], regular_rows=[x for x in rows if 'regular' in x], regular=regular_info,
                rule=CARD_RULE, matched=len(rows), ledger_checked=len(sheet_rows))


def extract(book, previous, through='auto', notes=None, questions=None, anonymous=(), fixed=None, confirm_csv=None):
    import openpyxl
    w = openpyxl.load_workbook(book, data_only=True, read_only=True)
    sheets = set(w.sheetnames)
    states = month_states(w)
    if through == 'auto':
        through = closed_through(w, states)
        if not through:
            raise ValueError('no closed month found')
    summary = w['결산']
    columns = COLS[:through]
    for c in columns:
        if summary.cell(3,c).value != 0 or type(summary.cell(3,c).value) not in (int,float):
            raise ValueError('monthly reconciliation must be numeric zero')
    seen=set()
    for r in list(w['대사'].values)[4:]:
        batch = re.match(r'26-(\d{2})', str(r[0] or ''))
        if batch and int(batch[1]) <= through:
            seen.add(int(batch[1]))
            if r[1] is None or r[2] is None or number(r[3]) != 0:
                raise ValueError('donation reconciliation must be zero')
    if seen != set(range(1,through+1)):
        raise ValueError('confirmed donation months missing')
    accounts=[]; side='income'
    income=expense=None
    for row in summary.values:
        label=str(row[0] or '')
        if label=='<지출>':side='expense'
        if label=='수입합계':income=[number(row[c-1]) for c in columns]
        if label=='지출합계':expense=[number(row[c-1]) for c in columns]
        if re.match(r'\s+\(\d+\)',label):
            name=re.sub(r'^\s*\(\d+\)\s*','',label)
            accounts.append(dict(name=name,side=side,group=CATEGORIES.get(name,'수입' if side=='income' else '기타지출'),values=[number(row[c-1]) for c in columns],prior_year=round(row[1]) if type(row[1]) in (int,float) else None))
    if income is None or expense is None:raise ValueError('summary totals missing')
    for kind, totals in [('income',income),('expense',expense)]:
        if [sum(a['values'][i] for a in accounts if a['side']==kind) for i in range(through)]!=totals:
            raise ValueError('account totals differ from workbook summary')
    ledger = list(w['원장'].values)[1:]
    # An explicit anonymity request in the books («익명» in 표시/메모/적요) or in --anonymous turns the name into «익명».
    anon = set(anonymous)
    for row in ledger:
        if any('익명' in str(x) for x in row[6:9] if x) and kind_of(row[2]) != 'none':
            anon.add(str(row[2]).strip())
    fixed = fixed or []
    people = People(anon, {n: f['label_name'] for f in fixed for n in f['names']})
    transactions=[]
    for row in ledger:
        date=str(row[1] or '')
        m=re.match(r'(\d{4})[.-](\d{2})[.-](\d{2})',date)
        if not m or int(m[2])>through:continue
        account=str(row[9] or '')
        if account=='상계(제외)':continue
        if not account or account=='미분류':raise ValueError('unclassified ledger transaction')
        transactions.append(dict(month=int(m[2]),date='-'.join(m.groups()),name=people.mask(row[2]),pid=people.pid(row[2]),account=account,expense=number(row[3] or 0),income=number(row[4] or 0)))
    prior=collections.defaultdict(lambda:[0]*through)
    if previous:
        pw=openpyxl.load_workbook(previous,data_only=True,read_only=True)
        allowed=['정기후원','일시후원','한빛누리CMS','한빛누리 비CMS']
        for row in list(pw.active.values)[2:]:
            if row[1] in allowed:
                for i in range(through):prior[row[1]][i]+=number(row[i+2] or 0)
    donors, cms_change = extract_donors(w, sheets, through, previous, people) if '후원자현황' in sheets else ([], None)
    # Per-person sheets are not always filled for every month (e.g. CMS detail arrives with the 한빛누리 file):
    # record the months where a category's per-person sum differs from the closed account value.
    donor_account = {'정기후원금':'정기후원금','일시후원금':'일시후원금','한빛누리CMS후원금':'한빛누리CMS후원금','한빛누리비CMS후원금':'한빛누리비CMS후원금'}
    donor_check = {}
    for cat, acct in donor_account.items():
        av = next((a['values'] for a in accounts if a['name'] == acct), None)
        if av is not None:
            donor_check[cat] = [m+1 for m in range(through) if sum(d['values'][m] for d in donors if d['category'] == cat) != av[m]]
    proxy = extract_proxy(w, sheets, through, ledger, people, fixed, confirmed_notes(confirm_csv)) if '대표대납_정산' in sheets else None
    confirmed = [m for m in range(1, through+1) if states[m] == '확정']
    provisional = [m for m in range(1, through+1) if states[m] == '잠정']
    confirmed_through = 0
    for m in range(1, through+1):
        if states[m] != '확정':
            break
        confirmed_through = m
    if provisional:
        pending = '%s월은 잠정 마감입니다(원본 자료와 대조 전). 확정 합계와 따로 표시하며, 확정되면 이 보고서를 다시 만듭니다.' % '·'.join(map(str, provisional))
    elif through < 12:
        pending = '%d월 이후는 마감되지 않아 넣지 않았습니다.' % (through+1)
    else:
        pending = '12월까지 마감이 끝났습니다.'
    data=dict(version='somnium-finance-paper/1',year=2026,through=through,confirmed_through=confirmed_through,source_sha256=hashlib.sha256(Path(book).read_bytes()).hexdigest(),
              monthly=[dict(month=i+1,status=states[i+1],income=income[i],expense=expense[i],net=income[i]-expense[i],balance=number(summary.cell(4,columns[i]).value)) for i in range(through)],
              opening=number(summary.cell(5,3).value),accounts=accounts,transactions=transactions,donors=donors,donor_check=donor_check,cms_change=cms_change,proxy=proxy,previous=dict(prior),
              generated=datetime.date.today().isoformat(),pending=pending,
              notes=DEFAULT_NOTES if notes is None else notes,
              questions=DEFAULT_QUESTIONS if questions is None else questions,
              _raw=people.raw_person_names())
    # Transaction totals are NET bank cash; account totals are donation gross incl. settlement fees.
    for i,m in enumerate(data['monthly']):
        cash=sum(t['income']-t['expense'] for t in transactions if t['month']==m['month'])
        if cash!=m['net']:raise ValueError('ledger cash net differs from closed summary')
        start=data['opening'] if i==0 else data['monthly'][i-1]['balance']
        if start+m['net']!=m['balance']:raise ValueError('balance rollforward mismatch')
    return data


def build(data):
    raw=data.pop('_raw',set())
    template=Path(__file__).with_name('accounting_paper.html').read_text()
    encoded=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    result=template.replace('REPORT_CSP',html.escape(CSP,quote=True)).replace('REPORT_JSON',encoded)
    # the hex source fingerprint can contain 10 digits in a row by chance; every other string is scanned
    if re.search(r'(?:01[016789][- ]?\d{3,4}[- ]?\d{4}|\d{10,})', result.replace(data['source_sha256'],'')):
        raise ValueError('possible contact/account number in report')
    names = {a['name'] for a in data['accounts']} | {d['category'] for d in data.get('donors', [])}
    for name in raw - names:
        # An unmasked name is a failure; the masked form (김*환) never matches this pattern.
        if re.search(r'(?<![가-힣])' + re.escape(name) + r'(?![가-힣])', encoded):
            raise ValueError('unmasked personal name found in report')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workbook',required=True);p.add_argument('--previous');p.add_argument('--through',default='auto',help='auto = every month the workbook has closed (default), or an explicit month 1-12');p.add_argument('--out',required=True);p.add_argument('--notes');p.add_argument('--questions');p.add_argument('--anonymous',help='JSON list of names who asked to be anonymous');p.add_argument('--fixed-payments',help='JSON list of standing payees: names, label_name, label, note');p.add_argument('--confirm-csv',help='수기확인.csv (read only): 사유 memos');p.add_argument('--manifest')
    a=p.parse_args()
    if a.through!='auto':
        a.through=int(a.through)
        if not 1<=a.through<=12:raise ValueError('choose an explicitly closed month 1–12')
    out=Path(a.out)
    if out.exists():raise ValueError('choose a new output; preserve reviewed versions')
    load=lambda f:json.loads(Path(f).read_text()) if f else None
    data=extract(a.workbook,a.previous,a.through,load(a.notes),load(a.questions),load(a.anonymous) or (),load(a.fixed_payments),a.confirm_csv);body=build(data);out.write_text(body)
    if a.manifest:
        mp=Path(a.manifest)
        if mp.exists():raise ValueError('choose a new manifest path')
        c,t,pm=data['confirmed_through'],data['through'],data['through']-data['confirmed_through']
        period='%d년 1~%d월 확정'%(data['year'],c)+(' · %d월 잠정'%t if pm==1 else ' · %d~%d월 잠정'%(c+1,t) if pm else '')
        mp.write_text(json.dumps(dict(file=str(out.resolve()),title='솜니움 %s 재정보고서 · 검토 초안'%period,period=period[:80],sha256=hashlib.sha256(body.encode()).hexdigest(),member_safe=True,publish=False),ensure_ascii=False,indent=2))
    print(json.dumps({'months':data['through'],'confirmed_through':data['confirmed_through'],'transactions':len(data['transactions']),'accounts':len(data['accounts']),'sha256':hashlib.sha256(body.encode()).hexdigest(),'source_sha256':data['source_sha256'],'privacy':'names masked, memo/contact/account columns excluded'},ensure_ascii=False))

if __name__=='__main__':main()
