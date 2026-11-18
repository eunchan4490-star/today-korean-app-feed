import unittest
from pain import github_row, hn_row, text
class PainTest(unittest.TestCase):
 def test_issue_excludes_pr_and_untrusted_urls(self):
  item={'id':1,'title':'Request','body':'A real request','html_url':'https://github.com/owner/repo/issues/1'}
  self.assertEqual('1',github_row(item,'now')['source_id'])
  self.assertIsNone(github_row(dict(item,pull_request={}), 'now'))
  self.assertIsNone(github_row(dict(item,html_url='https://evil.example/issues/1'), 'now'))
 def test_hn_excludes_hiring_and_deleted(self):
  item={'id':2,'type':'story','title':'Ask HN: What tool solves this problem?','text':'A repetitive workflow','time':1}
  self.assertEqual('ask_hn',hn_row(item,'now')['source_kind'])
  self.assertIsNone(hn_row(dict(item,deleted=True),'now'))
  self.assertIsNone(hn_row(dict(item,title='Ask HN: Who is hiring?'),'now'))
 def test_excerpts_strip_markup_code_and_email(self):
  self.assertEqual('Hello [email removed]',text('<p>Hello</p> ```secret``` me@example.com'))
if __name__=='__main__':unittest.main()
