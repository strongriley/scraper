# TODO
import fire

class Scraper(object):
    def scrape(self, domain, max_depth=None, max_pages=None):
        # TODO validate domain
        print domain


if __name__ == '__main__':
    fire.Fire(Scraper)
