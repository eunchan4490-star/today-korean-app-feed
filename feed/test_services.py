import unittest
from services import row,canonical_url,Metadata,WINDOW,collect
from unittest.mock import patch
class ServicesTest(unittest.TestCase):
 def item(self,stamp=1000000):return {'id':123,'type':'story','title':'Show HN: A creative app','url':'https://example.com/app?utm_source=hn','text':'Build a personal sound board','time':stamp}
 def test_only_recent_public_product_posts(self):
  self.assertIsNotNone(row(self.item(),1000000));self.assertIsNone(row(self.item(1000000-WINDOW-1),1000000));self.assertIsNone(row(self.item(1000001),1000000))
  for extra in [{'deleted':True},{'dead':True},{'title':'Ask HN: app?'},{'url':'https://127.0.0.1/'}]:
   item=self.item();item.update(extra);self.assertIsNone(row(item,1000000))
 def test_introduction_is_not_release_date(self):
  r=row(self.item(),1000000);self.assertEqual('public_introduction',r['date_basis']);self.assertIsNone(r['release_date']);self.assertEqual('unverified',r['pricing_status']);self.assertNotIn('by',r)
 def test_campaigns_and_github_subpaths_do_not_create_new_products(self):
  self.assertEqual(canonical_url('https://EXAMPLE.com/app/?utm_source=x#demo'),canonical_url('https://example.com/app'))
  self.assertEqual('https://github.com/owner/repo',canonical_url('https://github.com/OWNER/Repo.git/tree/main?x=y'))
  for u in ['http://example.com','https://a:b@example.com','https://192.168.1.1','https://x.local','https://example.com:8080'] :self.assertIsNone(canonical_url(u))
 def test_metadata_only_not_whole_page(self):
  p=Metadata();p.feed('<p>Do not copy this whole page</p><meta property="og:description" content="A sound &amp; music app">');self.assertEqual('A sound & music app',p.description)
 def test_network_failure_is_not_a_successful_empty_window(self):
  def failed(url):
   if url.endswith('showstories.json'):return [1,2]
   raise OSError('temporary network error')
  with patch('services.fetch',side_effect=failed):
   with self.assertRaises(RuntimeError):collect()
 def test_old_posts_produce_an_honest_empty_window(self):
  def old(url):return [1] if url.endswith('showstories.json') else self.item(1)
  with patch('services.fetch',side_effect=old):
   self.assertEqual([],collect()['items'])
if __name__=='__main__':unittest.main()
