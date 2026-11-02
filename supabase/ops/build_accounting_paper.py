"""Read an independently recalculated COPY of the closed workbook; never modify accounting sources.
Output is private member-report HTML, not a static-public asset.
"""
import argparse
import collections
import hashlib
import html
import json
import re
from pathlib import Path

COLS = [3,4,5,7,8,9,11,12,13,15,16,17]
CATEGORIES = {'급여':'경상비','복리후생비':'경상비','사무비':'경상비','식음료비(경상)':'경상비','사무실임차료':'경상비','CMS비용':'경상비','대여금':'경상비','강사비':'사업비','연구지원비':'사업비','식음료비(사업)':'사업비','장소사용료':'사업비','홍보비':'사업비','행사비':'사업비','참가비환불':'사업비','퇴직금':'퇴직금','차입금변제':'기타지출','잡지출':'기타지출'}
CSP="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'"


def mask_name(value):
    s = str(value or '').strip()
    # Whitelist the shape of a name, never copy arbitrary bank memos or phone/account numbers.
    if re.fullmatch(r'[가-힣]{2,4}', s):
        if s.endswith(('교회','재단','은행')):
            return s
        return s[0] + '*' * (len(s)-2 if len(s)>2 else 1) + (s[-1] if len(s)>2 else '')
    if s in ('한빛누리','아지트솜니움','한예연') or re.fullmatch(r'[가-힣A-Za-z·㈜]{1,40}(교회|연구소|주식회사|재단|통신|은행|공사)', s):
        return s
    return '내역 비공개' if s else '미기록'


def number(value):
    if type(value) not in (int,float):
        raise ValueError('missing or invalid recalculated amount')
    return round(value)


def extract(book, previous, through):
    import openpyxl
    w = openpyxl.load_workbook(book, data_only=True, read_only=True)
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
            accounts.append(dict(name=name,side=side,group=CATEGORIES.get(name,'수입' if side=='income' else '기타지출'),values=[number(row[c-1]) for c in columns]))
    if income is None or expense is None:raise ValueError('summary totals missing')
    for kind, totals in [('income',income),('expense',expense)]:
        if [sum(a['values'][i] for a in accounts if a['side']==kind) for i in range(through)]!=totals:
            raise ValueError('account totals differ from workbook summary')
    transactions=[]
    for row in list(w['원장'].values)[1:]:
        date=str(row[1] or '')
        m=re.match(r'(\d{4})[.-](\d{2})[.-](\d{2})',date)
        if not m or int(m[2])>through:continue
        account=str(row[9] or '')
        if account=='상계(제외)':continue
        if not account or account=='미분류':raise ValueError('unclassified ledger transaction')
        transactions.append(dict(month=int(m[2]),date='-'.join(m.groups()),name=mask_name(row[2]),account=account,expense=number(row[3] or 0),income=number(row[4] or 0)))
    prior=collections.defaultdict(lambda:[0]*through)
    if previous:
        pw=openpyxl.load_workbook(previous,data_only=True,read_only=True)
        allowed=['정기후원','일시후원','한빛누리CMS','한빛누리 비CMS']
        for row in list(pw.active.values)[2:]:
            if row[1] in allowed:
                for i in range(through):prior[row[1]][i]+=number(row[i+2] or 0)
    data=dict(version='somnium-finance-paper/1',year=2026,through=through,source_sha256=hashlib.sha256(Path(book).read_bytes()).hexdigest(),
              monthly=[dict(month=i+1,income=income[i],expense=expense[i],net=income[i]-expense[i],balance=number(summary.cell(4,columns[i]).value)) for i in range(through)],
              opening=number(summary.cell(5,3).value),accounts=accounts,transactions=transactions,previous=dict(prior),
              pending=('10월은 한빛누리 자료 대기 · 11월 중순 반영 예정' if through==9 else '추가 월은 마감·대조 완료 후 반영합니다.'),
              questions=['8/5 동일 금액 지급 건의 강의 역할 확인 대기','강사료 단가 차이의 지급 기준 확인 대기','7/28 강의분 지급 여부·다른 지급 경로 확인 대기'])
    # Transaction totals are NET bank cash; account totals are donation gross incl. settlement fees.
    for i,m in enumerate(data['monthly']):
        cash=sum(t['income']-t['expense'] for t in transactions if t['month']==m['month'])
        if cash!=m['net']:raise ValueError('ledger cash net differs from closed summary')
        start=data['opening'] if i==0 else data['monthly'][i-1]['balance']
        if start+m['net']!=m['balance']:raise ValueError('balance rollforward mismatch')
    return data


def build(data):
    template=Path(__file__).with_name('accounting_paper.html').read_text()
    encoded=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    result=template.replace('REPORT_CSP',html.escape(CSP,quote=True)).replace('REPORT_JSON',encoded)
    if re.search(r'(?:01[016789][- ]?\d{3,4}[- ]?\d{4}|\d{10,})', result):
        raise ValueError('possible contact/account number in report')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workbook',required=True);p.add_argument('--previous');p.add_argument('--through',type=int,default=9);p.add_argument('--out',required=True)
    a=p.parse_args()
    if not 1<=a.through<=12:raise ValueError('choose an explicitly closed month 1–12')
    out=Path(a.out)
    if out.exists():raise ValueError('choose a new output; preserve reviewed versions')
    data=extract(a.workbook,a.previous,a.through);body=build(data);out.write_text(body)
    print(json.dumps({'months':a.through,'transactions':len(data['transactions']),'accounts':len(data['accounts']),'sha256':hashlib.sha256(body.encode()).hexdigest(),'source_sha256':data['source_sha256'],'privacy':'names masked, memo/contact/account columns excluded'},ensure_ascii=False))

if __name__=='__main__':main()
