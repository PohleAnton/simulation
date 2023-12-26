import json
import scrapy

class MarxSpider(scrapy.Spider):
    name = 'marx_profile'
    start_urls = [
        'https://de.wikipedia.org/wiki/Karl_Marx',
        'https://www.geschichte-abitur.de/biographien/karl-marx-biografie',
        'https://www.vorwaerts.ch/theorie-debatte/karl-marx-grundlagen-seines-denkens/'
    ]

    def parse(self, response, **kwargs):
        for paragraph in response.css('p'):
            yield {'text': paragraph.extract()}


# Crawler ausführen mit: scrapy crawl marx_profile
# Crawler ausführen und Daten im Ordner data in JSON sichern:
# scrapy crawl marx_profile -o data/marx_profile.json



