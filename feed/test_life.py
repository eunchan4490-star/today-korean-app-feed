import unittest
from life import review_row
class LifeTest(unittest.TestCase):
 def entry(self):return {'im:rating':{'label':'2'},'id':{'label':'999'},'title':{'label':'배송 주소 관리'},'content':{'label':'가족에게 보내는 배송 주소를 여러 개 관리하기 어렵고 주문 때마다 다시 확인해야 해서 불편합니다.'}}
 def test_real_life_excerpt_and_no_author(self):
  row=review_row(self.entry(),'123','생활 앱','now');self.assertEqual('123:999',row['source_id']);self.assertNotIn('author',row)
 def test_positive_and_short_reviews_are_excluded(self):
  e=self.entry();e['im:rating']['label']='5';self.assertIsNone(review_row(e,'123','앱','now'));e=self.entry();e['content']['label']='배송 불편';self.assertIsNone(review_row(e,'123','앱','now'))
if __name__=='__main__':unittest.main()
