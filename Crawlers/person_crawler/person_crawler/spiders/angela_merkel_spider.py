import json
import scrapy

class MerkelSpider(scrapy.Spider):
    name = 'merkel_profile'
    start_urls = [
        'https://de.wikipedia.org/wiki/Angela_Merkel',
        'https://www.imf.org/de/News/Articles/2019/08/31/sp083119-Angela-Merkel-Striking-the-Right-Note-on-Leadership',
    ]

    def parse(self, response, **kwargs):
        for paragraph in response.css('p'):
            yield {'text': paragraph.extract()}


# Crawler ausführen mit: scrapy crawl merkel_profile
# Crawler ausführen und Daten im Ordner data in JSON sichern:
# scrapy crawl merkel_profile -o data/merkel_profile.json



