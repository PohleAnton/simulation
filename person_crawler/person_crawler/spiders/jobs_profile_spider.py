import json
import scrapy

class JobsSpider(scrapy.Spider):
    name = 'jobs_profile'
    start_urls = [
        'https://de.wikipedia.org/wiki/Steve_Jobs',
        'https://www.sueddeutsche.de/digital/steve-jobs-biografie-erscheint-in-den-usa-zwischen-genialitaet-und-groessenwahn-1.1172183',
    ]

    def parse(self, response, **kwargs):
        for paragraph in response.css('p'):
            yield {'text': paragraph.extract()}


# Crawler ausführen mit: scrapy crawl jobs_profile
# Crawler ausführen und Daten im Ordner data in JSON sichern:
# scrapy crawl jobs_profile -o data/jobs_profile.json



