import json
import scrapy

class NietzscheSpider(scrapy.Spider):
    name = 'nietzsche_profile'
    start_urls = [
        'https://www.philognosie.net/wissen-technik/friedrich-wilhelm-nietzsches-philosophie-im-ueberblick',
        'https://de.wikipedia.org/wiki/Friedrich_Nietzsche',
        'http://www.philosophenlexikon.de/friedrich-nietzsche-1844-1900/'
    ]

    def parse(self, response, **kwargs):
        for paragraph in response.css('p'):
            yield {'text': paragraph.extract()}


# Crawler ausführen mit: scrapy crawl nietzsche_profile
# Crawler ausführen und Daten im Ordner data in JSON sichern:
# scrapy crawl nietzsche_profile -o data/nietzsche_profile.json



