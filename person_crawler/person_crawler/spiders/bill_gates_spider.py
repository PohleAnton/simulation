import json
import scrapy

class GatesSpider(scrapy.Spider):
    name = 'gates_profile'
    start_urls = [
        'https://en.wikipedia.org/wiki/Bill_Gates',
        'https://whoswho.de/bio/bill-gates.html',
        'https://www.greelane.com/de/geisteswissenschaften/geschichte--kultur/bill-gates-biography-and-history-1991861'
    ]

    def parse(self, response, **kwargs):
        for paragraph in response.css('p'):
            yield {'text': paragraph.extract()}


# Crawler ausführen mit: scrapy crawl gates_profile
# Crawler ausführen und Daten im Ordner data in JSON sichern: scrapy crawl gates_profile -o data/gates_profile.json



