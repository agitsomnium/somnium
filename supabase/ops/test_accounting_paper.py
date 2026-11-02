import tempfile
import unittest
from pathlib import Path
import openpyxl
from build_accounting_paper import extract, mask_name, number

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
        d.append(['26-01CMS',30,30,0]);d.append(['26-10CMS',9999,0,9999]);w.save(p)
        return p,w
    def test_confirmed_months_only_and_sensitive_fields_excluded(self):
        p,w=self.fixture();d=extract(p,None,1)
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
    def test_person_and_free_text_masks(self):
        self.assertEqual(mask_name('홍길동'),'홍*동');self.assertEqual(mask_name('홍길동 010-1234-5678'),'내역 비공개')
        self.assertEqual(mask_name('가상연구소'),'가상연구소')
    def test_none_amount_never_zero_filled(self):
        with self.assertRaises(ValueError):number(None)

if __name__=='__main__':unittest.main()
