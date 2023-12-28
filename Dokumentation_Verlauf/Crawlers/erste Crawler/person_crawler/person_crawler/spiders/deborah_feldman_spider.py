import json
import scrapy

class FeldmanSpider(scrapy.Spider):
    name = ('feldman_profile')
    start_urls = [
        'https://de.wikipedia.org/wiki/Deborah_Feldman',
        'https://www.spiegel.de/politik/deutschland/antisemitismus-deborah-feldman-kritisiert-selektiven-schutz-juedischen-lebens-a-c4775412-1abb-447c-b691-2b1a20054f72',
        'https://taz.de/Buch-ueber-Juedischsein-und-Identitaet/!5960158/'
    ]

    def parse(self, response, **kwargs):
        for paragraph in response.css('p'):
            yield {'text': paragraph.extract()}


# Crawler ausführen mit: scrapy crawl feldman_profile
# Crawler ausführen und Daten im Ordner data in JSON sichern:
# scrapy crawl feldman_profile -o data/feldman_profile.json