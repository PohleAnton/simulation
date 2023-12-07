import json
import scrapy

class MuskSpider(scrapy.Spider):
    name = 'musk_profile'
    start_urls = [
        'https://de.wikipedia.org/wiki/Elon_Musk',
        'https://www.zdf.de/nachrichten/panorama/prominente/elon-musk-biografie-buch-100.html',
        'https://www.businessinsider.de/wirtschaft/elon-musk-8-wichtige-erkenntnisse-aus-der-neuen-biografie/'
    ]

    def parse(self, response, **kwargs):
        for paragraph in response.css('p'):
            yield {'text': paragraph.extract()}


# Crawler ausführen mit: scrapy crawl musk_profile
# Crawler ausführen und Daten im Ordner data in JSON sichern: scrapy crawl musk_profile -o data/musk_profile.json



