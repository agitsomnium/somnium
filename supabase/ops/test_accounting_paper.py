import tempfile
import unittest
from pathlib import Path
import openpyxl
from build_accounting_paper import extract, mask_name, mask_person, number, build, People

class PaperTests(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        p=Path(temp.name)/'book.xlsx';w=openpyxl.Workbook();s=w.active;s.title='결산'
        s.cell(3,3,0);s.cell(4,3,120);s.cell(5,3,100)
        for r,label,value in [(8,'    (1) 정기후원금',30),(9,'수입합계',30),(10,'<지출>',0),(11,'    (1) 강사비',10),(12,'지출합계',10)]:s.cell(r,1,label);s.cell(r,3,value)
        l=w.create_sheet('원장');l.append(['월','날짜','이름','출금','입금','잔액','표시','메모','적요','계정'])
        l.append([None,'2026.01.01 10:00','홍길동',0,30,None,'01012345678','123456789012',None,'정기후원금'])
        l.append([None,'2026.01.02 10:00','가상교회',10,0,None,None,None,None,'강사비'])
        l.append([None,'2026.10.02 10:00','미확인',9999,0,None,None,None,None,'강사비'])
        d=w.create_sheet('대사')
        for _ in range(4):d.append(['header'])
        d.append(['26-01CMS',30,30,0,'OK']);d.append(['26-10CMS',9999,0,9999,'OK']);w.save(p)
        return p,w
    def test_confirmed_months_only_and_sensitive_fields_excluded(self):
        p,w=self.fixture();d=extract(p,None,1)
        self.assertEqual(d['monthly'][0]['status'],'확정');self.assertEqual(d['confirmed_through'],1)
        self.assertEqual(len(d['transactions']),2)
        self.assertEqual(d['transactions'][0]['name'],'홍*동')
        self.assertEqual(d['transactions'][1]['name'],'가상교회')
        self.assertNotIn('01012345678',str(d));self.assertNotIn('123456789012',str(d))
    def test_uncached_verification_is_not_zero(self):
        p,w=self.fixture();w['결산'].cell(3,3).value=None;w.save(p)
        with self.assertRaisesRegex(ValueError,'numeric zero'):extract(p,None,1)
    def test_account_summary_mismatch_refused(self):
        p,w=self.fixture();w['결산'].cell(8,3).value=31;w.save(p)
        with self.assertRaisesRegex(ValueError,'account totals'):extract(p,None,1)
    def test_nonzero_confirmed_donation_reconciliation_refused(self):
        p,w=self.fixture();w['대사'].cell(5,4).value=1;w.save(p)
        with self.assertRaisesRegex(ValueError,'donation reconciliation'):extract(p,None,1)
    def test_bank_cash_net_mismatch_refused(self):
        p,w=self.fixture();w['원장'].cell(2,5).value=31;w.save(p)
        with self.assertRaisesRegex(ValueError,'cash net'):extract(p,None,1)
    def test_auto_stops_at_first_unclosed_month(self):
        p,w=self.fixture();d=extract(p,None,'auto')
        self.assertEqual(d['through'],1);self.assertEqual(d['confirmed_through'],1)
    def test_provisional_verdict_marks_month_and_never_enters_confirmed(self):
        p,w=self.fixture();w['대사'].cell(5,5).value='잠정';w.save(p);d=extract(p,None,1)
        self.assertEqual(d['monthly'][0]['status'],'잠정');self.assertEqual(d['confirmed_through'],0);self.assertIn('잠정',d['pending'])
    def test_unknown_or_missing_verdict_refused(self):
        p,w=self.fixture();w['대사'].cell(5,5).value=None;w.save(p)
        with self.assertRaisesRegex(ValueError,'verdict'):extract(p,None,1)
    def test_masking_rules(self):
        self.assertEqual(mask_person('홍길동'),'홍*동');self.assertEqual(mask_person('홍길'),'홍*');self.assertEqual(mask_person('남궁민수'),'남궁*수')
        self.assertEqual(mask_name('홍길동',{'홍길동'}),'익명');self.assertEqual(mask_name('가상교회'),'가상교회')
    def test_anonymity_mark_in_ledger_turns_name_into_anonymous(self):
        p,w=self.fixture();w['원장'].cell(2,8).value='익명 요청';w.save(p);d=extract(p,None,1)
        self.assertEqual(d['transactions'][0]['name'],'익명')
    def test_person_ids_are_stable_and_raw_names_only_in_private_set(self):
        pe=People();self.assertEqual(pe.pid('홍길동'),pe.pid('홍길동'));self.assertIsNone(pe.pid('내역 비공개 메모 abc'));self.assertIn('홍길동',pe.raw_person_names())
    def test_unmasked_name_in_report_is_refused_but_masked_passes(self):
        p,w=self.fixture();d=extract(p,None,1);d['_raw']={'홍길동'}
        build(dict(d))  # masked 홍*동 passes
        d=extract(p,None,1);d['_raw']={'홍길동'};d['notes']=[dict(months=[1],text='홍길동 님')]
        with self.assertRaisesRegex(ValueError,'unmasked'):build(d)
    def test_proxy_payment_missing_from_ledger_refuses(self):
        p,w=self.fixture();s=w.create_sheet('대표대납_정산');s.append(['t']);s.append(['t']);s.append(['월','일시','받는분','금액','메모','분류','정정'])
        s.append([1,'2026.01.05 10:00','김가상',500,'식비','식음료비(사업)',None])
        w.save(p)
        with self.assertRaisesRegex(ValueError,'double count'):extract(p,None,1)
    def test_proxy_matched_once_and_delivery_rule_flag(self):
        p,w=self.fixture();s=w.create_sheet('대표대납_정산');s.append(['t']);s.append(['t']);s.append(['월','일시','받는분','금액','메모','분류','정정'])
        s.append([1,'2026.01.02 10:00','가상교회',10,'식비','강사비',None]);w.save(p)
        d=extract(p,None,1);self.assertEqual(d['proxy']['matched'],1);self.assertEqual(d['proxy']['rows'][0]['status'],'자동분류');self.assertIsNone(d['proxy']['rows'][0]['rule'])
    def test_person_and_free_text_masks(self):
        self.assertEqual(mask_name('홍길동'),'홍*동');self.assertEqual(mask_name('홍길동 010-1234-5678'),'내역 비공개')
        self.assertEqual(mask_name('가상연구소'),'가상연구소')
    def test_none_amount_never_zero_filled(self):
        with self.assertRaises(ValueError):number(None)

if __name__=='__main__':unittest.main()
