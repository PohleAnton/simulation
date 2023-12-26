import json
import scrapy

class WestSpider(scrapy.Spider):
    name = 'west_profile'
    start_urls = [
        'https://de.wikipedia.org/wiki/Kanye_West',
        'https://popkultur.de/kanye-west-die-erfolgsgeschichte/',
        'https://www.br.de/nachrichten/kultur/us-rapper-kanye-west-ich-mag-hitler-und-liebe-nazis,TOo7gHV'
    ]

    def parse(self, response, **kwargs):
        for paragraph in response.css('p'):
            yield {'text': paragraph.extract()}


# Crawler ausführen mit: scrapy crawl west_profile
# Crawler ausführen und Daten im Ordner data in JSON sichern:
# scrapy crawl west_profile -o data/west_profile.json



