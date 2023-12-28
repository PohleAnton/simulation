import json
import scrapy

class ArendtSpider(scrapy.Spider):
    name = 'arendt_profile'
    start_urls = [
        'https://www.dhm.de/lemo/biografie/hannah-arendt',
        'https://www.swr.de/swr2/wissen/hannah-arendt-widerstand-revolution-freiheit-swr2-wissen-2020-11-28-100.html',
        'https://www.zukunft-braucht-erinnerung.de/hannah-arendt/'
    ]

    def parse(self, response, **kwargs):
        for paragraph in response.css('p'):
            yield {'text': paragraph.extract()}


# Crawler ausführen mit: scrapy crawl arendt_profile
# Crawler ausführen und Daten im Ordner data in JSON sichern: scrapy crawl arendt_profile -o data/arendt_profile.json



