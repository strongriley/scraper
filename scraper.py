# TODO
from urlparse import urljoin

import fire
import requests
from bs4 import BeautifulSoup


class UrlNode(object):
    def __init__(self, url):
        """
        URL: should be a string something like "http://www.example.com"
        """
        self.url = url
        self.static_urls = []
        self.linked_urls = []

    def process(self):
        # TODO: How should we manage timeouts?
        response = requests.get(self.url) # Allow exceptions to bubble
        print response
        # TODO HTML parsing failures?
        html = BeautifulSoup(response.text, 'html.parser')
        print html
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
                self.static_urls.append(urljoin(self.url, link['href']))

        # Images ------------
        # grab img tags' src attribute
        # TODO should we follow stylesheets to their images and fonts?
        imgs = html.find_all('img')
        for img in imgs:
            if img.get('src'):
                self.static_urls.append(urljoin(self.url, img['src']))

        # Scripts -----------
        scripts = html.find_all('script')
        for script in scripts:
            # filter out inline scripts
            if script.get('src'):
                self.static_urls.append(urljoin(self.url, script['src']))

    def _find_urls(self, html):
        pass
        # TODO ignore other subdomains
        # TODO ignore inner page # anchors?


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
