import scrapy
from scrapy.crawler import CrawlerRunner
from scrapy.settings import Settings
from twisted.internet import reactor
from collections import Counter
import re
import logging

# Dieses Skript verwendet das Scrapy-Framework, um Webseiten zu crawlen und Informationen zu extrahieren. Es sucht nach relevanten Absätzen
# auf verschiedenen URLs, bewertet sie anhand bestimmter Schlüsselwörter und filtert irrelevante Absätze aus. Die Top 10 bewerteten und relevanten
# Absätze werden in einer JSON-Datei gespeichert. Das Scrapy-Framework ermöglicht das effiziente Crawlen und Extrahieren von Informationen
# von Webseiten und ist besonders nützlich, um gezielte Informationen aus großen Textmengen zu gewinnen.


# Funktion zum Bewerten eines Absatzes basierend auf der Häufigkeit bestimmter Schlüsselwörter
def score_paragraph(paragraph):
    # Liste der Schlüsselwörter, die für die Bewertung verwendet werden
    keywords = ['Simulation', 'Hypothese', 'Realität', 'philosophisch', 'Nick Bostrom', 'Matrix', 'virtuell', 'Bewusstsein', 'Technologie', 'Künstliche Intelligenz']
    # Extrahieren aller Wörter im Absatz
    words = re.findall(r'\w+', paragraph)
    # Zählen, wie oft jedes Schlüsselwort vorkommt
    word_count = Counter(words)
    # Berechnen des Gesamtscores für den Absatz
    score = sum(word_count.get(word, 0) for word in keywords)
    return score

# Funktion zur Überprüfung, ob ein Text relevant ist
def is_relevant(text):
    # Liste irrelevanter Schlüsselwörter
    irrelevant_keywords = ['Newsletter', 'Anmeldung', 'Werbung', 'Affiliate', 'Link', 'Bildquelle', 'Autor', 'Referenzen', 'Quellenangabe', 'Fußnote']
    # Überprüfen, ob der Text keines der irrelevanten Schlüsselwörter enthält
    return not any(keyword in text for keyword in irrelevant_keywords)

# Spider-Klasse für das Crawlen von Webseiten und Extrahieren von Informationen
class SimulationHypoSpider(scrapy.Spider):
    name = 'simulation_hypo_knowledge'
    # Start-URLs für das Crawling
    start_urls = [
        'https://www.fsgu-akademie.de/lexikon/simulationshypothese/',
        'https://de.wikipedia.org/wiki/Simulationshypothese',
        'https://erfankasraie.com/eine-philosophische-untersuchung-ueber-die-simulationshypothese/'
    ]

    # Methode zur Verarbeitung der Antwort von jeder URL
    def parse(self, response, **kwargs):
        # Extrahieren der relevanten Absätze von der Seite
        paragraphs = response.css('p:not(.footer):not(.byline):not(.metadata):not(.reference):not(.caption)').extract()
        # Bewertung und Filterung der Absätze
        scored_paragraphs = [(score_paragraph(p), p) for p in paragraphs if is_relevant(p)]
        # Sortieren und Auswählen der Top 10 Absätze
        top_paragraphs = sorted(scored_paragraphs, key=lambda x: x[0], reverse=True)[:10]
        for score, paragraph in top_paragraphs:
            # Zurückgeben der Top 10 Absätze
            yield {'text': paragraph}

# Klasse zur Steuerung des Crawling-Prozesses
class CrawlerControl:
    def __init__(self):
        # Festlegen der Ausgabe-Einstellungen
        self.settings = Settings({
            'FEED_FORMAT': 'json',
            'FEED_URI': 'output.json'
        })
        # Initialisieren des CrawlerRunners mit diesen Einstellungen
        self.runner = CrawlerRunner(self.settings)
        self.crawling = False

    # Methode zum Starten des Crawlers
    def run(self):
        if not self.crawling:
            self.crawling = True
            d = self.runner.crawl(SimulationHypoSpider)
            # Registrieren der stop-Methode als Callback
            d.addBoth(self.stop)
            reactor.run()

    # Methode zum Stoppen des Crawlers
    def stop(self):
        if self.crawling:
            self.crawling = False
            reactor.stop()

# Konfiguration des Loggings
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

# Erstellen und Starten des CrawlerRunners mit der CrawlerControl-Klasse
crawler_control = CrawlerControl()
crawler_control.run()
