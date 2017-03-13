#!/usr/bin/env python
from urlparse import urljoin
from urlparse import urlparse
import json

import fire
import requests
from bs4 import BeautifulSoup

DEFAULT_MAX_PAGES = 20


class UrlNode(object):
    def __init__(self, url):
        """
        URL: should be a string something like "http://www.example.com"

        Note URL fragments like #top or #chapter2 and trailing slashes will be
        stripped to promote consistency and avoid repeat visits to the same
        page
        """
        self.url = self._format_url(url)
        self.static_urls = set()
        self.linked_urls = []

    def process(self):
        response = requests.get(self.url)  # Allow exceptions to bubble
        # TODO(riley): what should we do if the content-type returned isn't
        # actually text/html? Assume HTML for now, allow parser to silently
        # fail.
        html = BeautifulSoup(response.text, 'html.parser')
        self._find_static(html)
        self._find_urls(html)

    def get_print_dict(self):
        return {
            'url': self.url,
            'assets': sorted(list(self.static_urls))
        }

    def _find_static(self, html):
        """
        Extends self.static_urls with all stylesheets, images and scripts
        """
        # Stylesheets -------
        links = html.find_all('link')
        # grab link rel='stylesheet' for CSS
        # Could be a single list comprehensions line but that'd get messy
        for link in links:
            if 'stylesheet' in link.get('rel') and link.get('href'):
                self.static_urls.add(urljoin(self.url, link['href']))

        # Images ------------
        # grab img tags' src attribute
        imgs = html.find_all('img')
        for img in imgs:
            if img.get('src'):
                self.static_urls.add(urljoin(self.url, img['src']))

        # Scripts -----------
        scripts = html.find_all('script')
        for script in scripts:
            if script.get('src'):
                self.static_urls.add(urljoin(self.url, script['src']))

        # Remove duplicates
        self.static_urls = set(self.static_urls)

    def _find_urls(self, html):
        urls = html.find_all('a')
        for url in urls:
            if not url.get('href'):
                continue
            relative_url = self._format_url(url.get('href'))
            abs_url = urljoin(self.url, relative_url)
            # Use urlparse to compare attrs instead of hand-rolling regex
            current_urlparse = urlparse(self.url)
            new_urlparse = urlparse(abs_url)
            if current_urlparse == new_urlparse:
                continue
            if current_urlparse.netloc != new_urlparse.netloc:
                continue
            # Always add the URL. Scraper class should decide if it should skip
            self.linked_urls.append(abs_url)

    def _format_url(self, url):
        return url.split('#')[0].rstrip('/')


class Scraper(object):
    """
    A website scraper
    """
    def __init__(self, should_print=True):
        self._url_queue = []
        self.nodes = dict()
        self._print_list = []
        self._should_print = should_print  # makes testing easier

    def scrape(self, starting_url, max_pages=DEFAULT_MAX_PAGES):
        self.max_pages = max_pages
        # TODO(riley): could also add max_depth but let's keep simple for now
        self._url_queue.append(starting_url)
        self._process_queue()
        if self._should_print:
            self._print_results()

    def _process_queue(self):
        while self._url_queue:
            node = UrlNode(self._url_queue.pop(0))
            if node.url in self.nodes:
                continue  # Skip dups
            self.nodes[node.url] = node  # Use consistent URL
            try:
                node.process()
            # On the first request, errors will not be suppressed so the user
            # can correct their input. After that, URLs will all be scraped and
            # we don't want to bomb out b/c some website screwed up their HTML.
            except requests.RequestException as e:
                if len(self.nodes) == 1:
                    raise e
            self._url_queue.extend(node.linked_urls)
            self._print_list.append(node.get_print_dict())
            # "How does one get off this thing?" -Marcus Brody
            if len(self.nodes) >= self.max_pages:
                break

    def _print_results(self):
        # TODO(riley): would be nice to stream out, but requires more manual
        # manipulation of JSON than I'd like right now
        # TODO(riley): debatable, but including pages that failed to load and
        # will display empty assets. Get clarity on this.
        print json.dumps(self._print_list, indent=2, separators=(',', ': '))


if __name__ == '__main__':
    fire.Fire(Scraper)
