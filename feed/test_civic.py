import unittest
from civic import parse_list
class CivicTest(unittest.TestCase):
 def row(self,visibility='공개',ident='123'):
  return '<tr><td>1</td><td><a href="./bbs.asp?bmode=D&amp;code=10000662&amp;pcode='+ident+'">버스 &amp; 보행 불편</a></td><td>2026.11.01</td><td>개인 이름</td><td>완료</td><td>'+visibility+'</td></tr>'
 def test_only_explicitly_public_rows_and_no_author_or_body(self):
  rows=parse_list('<table class="boardList">'+self.row()+self.row('비공개','456')+'</table>','now')
  self.assertEqual(1,len(rows));self.assertEqual('dobong:123',rows[0]['source_id']);self.assertNotIn('개인 이름',str(rows));self.assertTrue(rows[0]['index_only']);self.assertEqual(rows[0]['title'],rows[0]['description'])
 def test_changed_layout_and_bad_identity(self):
  with self.assertRaises(ValueError):parse_list('<html>login</html>','now')
  self.assertEqual([],parse_list('<table class="boardList">'+self.row(ident='invalid')+'</table>','now'))
if __name__=='__main__':unittest.main()
