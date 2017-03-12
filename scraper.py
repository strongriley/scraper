#!/usr/bin/env python
from urlparse import urljoin
from urlparse import urlparse

import fire
import requests
from bs4 import BeautifulSoup


class UrlNode(object):
    def __init__(self, url):
        """
        URL: should be a string something like "http://www.example.com"
        Note URL fragments like #top or #chapter2 will be stripped because
        we'll still be scraping the same page.
        """
        # TODO should we see rileystrong.com/ and rileystrong.com as the same?
        self.url = url.split('#')[0]
        self.static_urls = set()
        self.linked_urls = set()

    def process(self):
        # TODO: How should we manage timeouts?
        response = requests.get(self.url) # Allow exceptions to bubble
        # TODO HTML parsing failures?
        html = BeautifulSoup(response.text, 'html.parser')
        self._find_static(html)
        self._find_urls(html)

    def _find_static(self, html):
        """
        Extends self.static_urls with all stylesheets, images, and scripts
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
        # TODO should we follow stylesheets to their images and fonts?
        imgs = html.find_all('img')
        for img in imgs:
            if img.get('src'):
                self.static_urls.add(urljoin(self.url, img['src']))

        # Scripts -----------
        scripts = html.find_all('script')
        for script in scripts:
            # filter out inline scripts
            if script.get('src'):
                self.static_urls.add(urljoin(self.url, script['src']))
        # Remove duplicates
        self.static_urls = set(self.static_urls)

    def _find_urls(self, html):
        urls = html.find_all('a')
        for url in urls:
            if not url.get('href'):
                continue
            abs_url = urljoin(self.url, url.get('href').split('#')[0])
            current_urlparse = urlparse(self.url)
            new_urlparse = urlparse(abs_url)
            if current_urlparse == new_urlparse:
                continue
            if current_urlparse.netloc != new_urlparse.netloc:
                continue
            self.linked_urls.add(abs_url)


class Scraper(object):
    """
    A website scraper
    """

    def __init__(self):
        self.url_queue = []
        self.visited = dict()

    def scrape(self, starting_url, max_depth=None, max_pages=None):
        # TODO max_depth, max_pages
        self.url_queue.append(starting_url)
        self._process_queue()

    def _process_queue(self):
        while self.url_queue:
            try:
                node = UrlNode(self.url_queue.pop(0))
                node.process()
            except requests.RequestException as e:
            # On the first request, errors will not be suppressed so the user
            # can correct their input. After that, URLs will all be scraped and
            # we don't want to bomb out because some website screwed up.
                if len(self.visited) == 0:
                    raise e




if __name__ == '__main__':
    fire.Fire(Scraper)
