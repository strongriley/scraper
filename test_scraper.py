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
        self.url = 'http://example.com/'
        self.node = UrlNode(self.url)

    # @responses.activate # TODO would be nice to not have to add this to every method
    def test_find_static_stylesheet_absolute(self):
        body = '<link rel="stylesheet" href="http://example.com/sheet.css">'
        self._mock_response(body)
        self.node.process()
        self.assertEqual(self.node.static_urls,
                         ['http://example.com/sheet.css'])

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
        self.assertEqual(node.static_urls,
                         ['http://example.com/sheet.css'])
        pass

    def test_find_static_stylesheet_bad_url(self):
        """
        Should still include it, but this is debatable
        """
        body = '<link rel="stylesheet" href="htp:/example.com/sheet.css">'
        self._mock_response(body)
        self.node.process()
        self.assertEqual(self.node.static_urls,
                         ['htp:/example.com/sheet.css'])

    def _mock_response(self, body, status=200):
        self.responses.add(
            responses.GET, self.url, body=body, status=status)


if __name__ == '__main__':
    unittest.main()
