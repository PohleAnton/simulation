import scrapy
from twisted.internet import reactor
import scrapy
from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging


class SimulationHypoSpider(scrapy.Spider):
    name = 'simulation_hypo_knowledge'
    start_urls = [
        'https://www.fsgu-akademie.de/lexikon/simulationshypothese/',
        'https://de.wikipedia.org/wiki/Simulationshypothese',
        'https://erfankasraie.com/eine-philosophische-untersuchung-ueber-die-simulationshypothese/'
    ]

    def parse(self, response, **kwargs):
        paragraphs = response.css('p:not(.footer, .byline, .metadata, .reference, .caption)').extract()
        scored_paragraphs = [(self.score_paragraph(p), p) for p in paragraphs if self.is_relevant(p)]
        top_paragraphs = sorted(scored_paragraphs, key=lambda x: x[0], reverse=True)[:10]
        for score, paragraph in top_paragraphs:
            yield {'text': paragraph}

    def score_paragraph(self, paragraph):
        keywords = ['Simulation', 'Hypothese', 'Realität', 'philosophisch', 'Nick Bostrom', 'Matrix', 'virtuell', 'Bewusstsein', 'Technologie', 'Künstliche Intelligenz']
        words = re.findall(r'\w+', paragraph)
        word_count = Counter(words)
        score = sum(word_count.get(word, 0) for word in keywords)
        return score

    def is_relevant(self, text):
        irrelevant_keywords = ['Newsletter', 'Anmeldung', 'Werbung', 'Affiliate', 'Link', 'Bildquelle', 'Autor', 'Referenzen', 'Quellenangabe', 'Fußnote']
        return not any(keyword in text for keyword in irrelevant_keywords)

configure_logging({"LOG_FORMAT": "%(levelname)s: %(message)s"})
runner = CrawlerRunner()

d = runner.crawl(SimulationHypoSpider)
d.addBoth(lambda _: reactor.stop())
reactor.run()  # das Skript blockiert hier, bis das Crawling beendet ist