# Scraper: a URL scraper for static assets

## Usage
```
./scraper.py scrape https://example.com
./scraper.py scrape https://example.com --max-pages=5
```

Notes:

- Request failures are silently dropped unless it's the first request.
- Failed URls will still appear in the results with a blank assets array.
- The default max-pages is 20.
- Static assets include directly referenced stylesheets, images, and scripts.
- Some static assets may not be included, e.g. inline images, fonts & images
  referenced from stylesheets, etc.

Output is something like this:

```
[
  {
    "url": "http://example.com/index.html",
    "assets": [
      "http://example.com/home.jpg",
      "http://example.com/main.js",
      "http://example.com/style.css"
    ]
  },
  {
    "url": "http://example.com/about.html",
    "assets": [
      "http://example.com/about.css",
      "http://example.com/images/about.jpg"
    ]
  }
]
```

## Setup

### System Requirements
You'll need at least the following installed on your machine:

- python 2.7
- pip
- virtualenv

### Installing

```
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Contributing
PRs / forks welcome. This project is unmaintained.


### Testing

```
./test_scraper.py
```

### Dependencies
Developers modify the `user-requirements.txt`file to add or update new deps.
After modifying, run:

```
pip install -r user-requirements.txt --upgrade && pip freeze > requirements.txt
```

That will save everything into the `requirements.txt` file but won't be very
user-readable. Think of this as the difference between Gemfile and Gemfile.lock
for anyone with Ruby experience.
