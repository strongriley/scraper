#!/usr/bin/env python
import unittest
import sys
import os
import re
from contextlib import contextmanager
from StringIO import StringIO

import requests
import responses
import pep8

from scraper import UrlNode
from scraper import Scraper

FIXTURES = [
    'about.html',
    'index.html',
    'login.html']


# Thanks Stackoverflow: http://stackoverflow.com/a/17981937
@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


class BaseScraperTestCase(unittest.TestCase):
    """
    Provides automatic mocking of network requests & helper methods
    """
    def run(self, result=None):
        """
        Instead of decorating every test with @responses.activate just put
        all in a context manager here
        """
        # TODO(riley): this approach can make it hard to determine which test
        # failed to make the request. Consider refactoring.
        with responses.RequestsMock(assert_all_requests_are_fired=True) as r:
            self.responses = r
            super(BaseScraperTestCase, self).run(result)

    def mock_fixtures(self):
        # TODO(riley): Optimize later. Wasting I/O loading each time called.
        for filename in FIXTURES:
            with open(os.path.join('fixtures', filename)) as f:
                url = 'http://example.com/%s' % filename
                self.responses.add(
                    responses.GET, url, body=f.read(), status=200)


class AcceptanceTestScraper(BaseScraperTestCase):
    """
    Acceptance tests on the Scraper class checking stdout
    """
    def run(self, result=None):
        """
        Automatically capture stdout and stderr since that's how scraper
        outputs things and that's what we want to test.
        """
        with captured_output() as (out, err):
            self.stdout = out
            self.stderr = err
            super(AcceptanceTestScraper, self).run(result)

    def test_basic_traverse(self):
        self.mock_fixtures()
        scraper = Scraper()
        scraper.scrape('http://example.com/index.html')
        with open(os.path.join('fixtures', 'expected.json')) as f:
            self.assertEqual(self.stdout_value, f.read().strip())

    @property
    def stdout_value(self):
        return self.stdout.getvalue().strip()


class IntegrationTestScraper(BaseScraperTestCase):
    """
    Integration tests on the Scraper class checking scraper.nodes
    """
    def setUp(self):
        self.url = 'http://example.com/index.html'
        self.scraper = Scraper(should_print=False)

    def test_simple_traverse(self):
        self.mock_fixtures()
        self.scraper.scrape(self.url)
        expected_nodes = {
            'http://example.com/index.html',
            'http://example.com/about.html',
            'http://example.com/login.html',
            'http://example.com/404'}
        self.assertEqual(set(self.scraper.nodes.keys()), expected_nodes)
        expected_static = {
            'http://example.com/index.html': {
                'http://example.com/style.css',
                'http://example.com/home.jpg',
                'http://example.com/main.js'
            }, 'http://example.com/about.html': {
                'http://example.com/about.css',
                'http://example.com/images/about.jpg',
            }, 'http://example.com/login.html': set([]),
            'http://example.com/404': set([]),
        }

        for url, static_urls in expected_static.iteritems():
            self.assertEqual(self.scraper.nodes[url].static_urls, static_urls)

    def test_fail_bad_seed_url(self):
        self.assertRaises(
            requests.exceptions.InvalidSchema,
            self.scraper.scrape, 'htp://example.com')

    def test_ignore_bad_scraped_url(self):
        body = '<a href="htp://example.com/login">login</a>'
        self.responses.add(responses.GET, self.url, body=body, status=200)
        self.scraper.scrape(self.url)

    def test_stripped_nodes_list(self):
        self.url = 'http://example.com'
        body = '<a href="http://example.com/">login</a>'
        self.responses.add(responses.GET, self.url, body=body, status=200)
        self.scraper.scrape(self.url)
        self.assertTrue('http://example.com' in self.scraper.nodes)
        self.assertFalse('http://example.com/' in self.scraper.nodes)

    def test_default_max_pages(self):
        # Must use different responses context to allow multiple calls
        with responses.RequestsMock(
                assert_all_requests_are_fired=False) as res:
            self._add_wild_goose_chase(res)
            self.scraper.scrape(self.url)
            self.assertEqual(len(self.scraper.nodes), 20)

    def test_custom_max_pages(self):
        # Must use different responses context to allow multiple calls
        with responses.RequestsMock(
                assert_all_requests_are_fired=False) as res:
            self._add_wild_goose_chase(res)
            self.scraper.scrape(self.url, 50)
            self.assertEqual(len(self.scraper.nodes), 50)

    def _add_wild_goose_chase(self, res):
        def wild_goose_chase(request):
            # Keeps providing a new link forever
            try:
                idx = int(request.url.split('/')[-1])
            except:
                idx = 0
            idx += 1
            body = '<a href="http://example.com/%s">keep goin!</a>' % idx
            headers = {'idx': str(idx)}
            return (200, headers, body)

        res.add_callback(
            responses.GET, re.compile(r'.+'),
            callback=wild_goose_chase,
            content_type='text/html')


class UnitTestUrlNode(BaseScraperTestCase):
    """
    Unit tests all functionality for UrlNode class
    """
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
        self.assertEqual(self.node.linked_urls, ['http://example.com/login'])

    def test_find_urls_strip_trailing_slash(self):
        body = '<a href="http://example.com/login/">login</a>'
        self._mock_response(body)
        self.node.process()
        self.assertEqual(self.node.linked_urls, ['http://example.com/login'])

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
        self.assertEqual(self.node.linked_urls, ['https://example.com/login'])

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

    def test_find_urls_keep_duplicates(self):
        body = '''
        <a href="http://example.com/login">login</a>
        <a href="http://example.com/login">login</a>
        '''
        self._mock_response(body)
        self.node.process()
        self.assertEqual(self.node.linked_urls, ['http://example.com/login']*2)

    def test_get_print_dict(self):
        body = '<script src="http://example.com/s.js"></script>'
        self._mock_response(body)
        self.node.process()
        expected = {
            "url": "http://example.com",
            "assets": ["http://example.com/s.js"]
        }
        self.assertEqual(self.node.get_print_dict(), expected)

    def _mock_response(self, body, status=200):
        self.responses.add(
            responses.GET, self.url, body=body, status=status)


class Pep8TestCase(unittest.TestCase):
    """
    Keep styles in check with PEP8
    """
    def test_pep8(self):
        # TODO(riley): automatically provide all *.py files.
        pep8style = pep8.StyleGuide(paths=['scraper.py', 'test_scraper.py'])
        report = pep8style.check_files()  # Verbose by default, will print
        if report.total_errors:
            raise RuntimeError('PEP8 StyleCheck failed. See STDOUT above.')


if __name__ == '__main__':
    unittest.main()
