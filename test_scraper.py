#!/usr/bin/env python
import unittest

import responses

from scraper import UrlNode
from scraper import Scraper


class IntegrationTestScraper(unittest.TestCase):
    pass


class UnitTestUrlNode(unittest.TestCase):
    """
    Unit tests all functionality inside UrlNode class
    """
    def run(self, result=None):
        """
        Instead of decorating every test with @responses.activate just put
        all in a context manager here
        """
        with responses.RequestsMock(assert_all_requests_are_fired=True) as r:
            self.responses = r
            super(UnitTestUrlNode, self).run(result)

    def setUp(self):
        self.url = 'http://example.com'
        self.node = UrlNode(self.url)

    def test_strip_trailing_slash(self):
        self.node = UrlNode('https://example.com/')
        self.assertEqual(self.node.url, 'https://example.com')

    def test_strip_fragments(self):
        self.node = UrlNode('https://example.com#top')
        self.assertEqual(self.node.url, 'https://example.com')

    def test_find_static_stylesheet_absolute(self):
        body = '<link rel="stylesheet" href="http://example.com/s.css">'
        self._mock_response(body)
        self.node.process()
        self.assertEqual(self.node.static_urls, {'http://example.com/s.css'})

    def test_find_static_stylesheet_ignore_other_link(self):
        body = '''
        <link href="/global/en" hreflang="en" rel="alternate">
        <link href="/apple-120x120.png" rel="apple-touch-icon" sizes="120x120">
        '''
        self._mock_response(body)
        self.node.process()
        self.assertEqual(len(self.node.static_urls), 0)

    def test_find_static_stylesheet_relative_url(self):
        self.url = 'http://example.com/folder/index.html'
        node = UrlNode(self.url)
        body = '<link rel="stylesheet" href="../sheet.css">'
        self._mock_response(body)
        node.process()
        self.assertEqual(node.static_urls, {'http://example.com/sheet.css'})

    def test_find_static_stylesheet_bad_url(self):
        """
        Should still include it, but this is debatable
        """
        body = '<link rel="stylesheet" href="htp:/example.com/s.css">'
        self._mock_response(body)
        self.node.process()
        self.assertEqual(self.node.static_urls, {'htp:/example.com/s.css'})

    def test_find_static_img_absolute(self):
        body = '<img height="50" width="50" src="http://example.com/img.jpg">'
        self._mock_response(body)
        self.node.process()
        self.assertEqual(self.node.static_urls, {'http://example.com/img.jpg'})

    def test_find_static_img_src_missing(self):
        body = '<img height="50" width="50">'
        self._mock_response(body)
        self.node.process()
        self.assertFalse(self.node.static_urls)

    def test_find_static_img_relative(self):
        self.url = 'http://example.com/folder/index.html'
        node = UrlNode(self.url)
        body = '<link rel="stylesheet" href="/img.jpg">'
        self._mock_response(body)
        node.process()
        self.assertEqual(node.static_urls, {'http://example.com/img.jpg'})

    def test_find_static_script_absolute(self):
        body = '<script src="http://example.com/s.js"></script>'
        self._mock_response(body)
        self.node.process()
        self.assertEqual(self.node.static_urls, {'http://example.com/s.js'})

    def test_find_static_script_inline(self):
        body = '''
        <script type="text/javascript">
            alert('pwned');
        </script>'
        '''
        self._mock_response(body)
        self.node.process()
        self.assertFalse(self.node.static_urls)

    def test_find_static_script_relative(self):
        self.url = 'http://example.com/folder/index.html'
        node = UrlNode(self.url)
        body = '<script src="../s.js"></script>'
        self._mock_response(body)
        node.process()
        self.assertEqual(node.static_urls, {'http://example.com/s.js'})

    def test_find_static_remove_duplicates(self):
        body = '''
        <link rel="stylesheet" href="http://example.com/s.css">
        <link rel="stylesheet" href="http://example.com/s.css">
        '''
        self._mock_response(body)
        self.node.process()
        self.assertEqual(self.node.static_urls, {'http://example.com/s.css'})

    def test_find_urls_absolute(self):
        body = '<a href="http://example.com/login">login</a>'
        self._mock_response(body)
        self.node.process()
        self.assertEqual(self.node.linked_urls, {'http://example.com/login'})

    def test_find_urls_strip_trailing_slash(self):
        body = '<a href="http://example.com/login/">login</a>'
        self._mock_response(body)
        self.node.process()
        self.assertEqual(self.node.linked_urls, {'http://example.com/login'})

    def test_find_urls_add_subdomain(self):
        body = '<a href="http://mail.example.com">e-mail</a>'
        self._mock_response(body)
        self.node.process()
        self.assertFalse(self.node.linked_urls)

    def test_find_urls_remove_subdomain(self):
        self.url = 'http://www.example.com'
        node = UrlNode(self.url)
        body = '<a href="http://example.com/login/">login</a>'
        self._mock_response(body)
        node.process()
        self.assertFalse(node.linked_urls)

    def test_find_urls_different_subdomain(self):
        self.url = 'http://www.example.com'
        node = UrlNode(self.url)
        body = '<a href="http://mail.example.com">e-mail</a>'
        self._mock_response(body)
        node.process()
        self.assertFalse(node.linked_urls)

    def test_find_urls_different_domain(self):
        body = '<a href="http://rileystrong.com">Riley Strong</a>'
        self._mock_response(body)
        self.node.process()
        self.assertFalse(self.node.linked_urls)

    def test_find_urls_different_scheme(self):
        body = '<a href="https://example.com/login">secure login</a>'
        self._mock_response(body)
        self.node.process()
        self.assertEqual(self.node.linked_urls, {'https://example.com/login'})

    def test_find_urls_fragment(self):
        body = '<a name="top"></a><a href="#top">jump to top</a>'
        self._mock_response(body)
        self.node.process()
        self.assertFalse(self.node.linked_urls)

    def test_find_urls_root_fragment(self):
        self.url = 'http://www.example.com/#top'
        node = UrlNode(self.url)
        body = '<a name="bottom"></a><a href="#bottom">jump to top</a>'
        # Manually add otherwise responses won't think we visited the page
        # since the fragment is removed
        self.responses.add(
            responses.GET, 'http://www.example.com/', body=body, status=200)
        node.process()
        self.assertFalse(node.linked_urls)

    def test_find_urls_remove_duplicates(self):
        body = '''
        <a href="http://example.com/login">login</a>
        <a href="http://example.com/login">login</a>
        '''
        self._mock_response(body)
        self.node.process()
        self.assertEqual(self.node.linked_urls, {'http://example.com/login'})

    def _mock_response(self, body, status=200):
        self.responses.add(
            responses.GET, self.url, body=body, status=status)


if __name__ == '__main__':
    unittest.main()
