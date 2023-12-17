import scrapy
from scrapy.crawler import CrawlerRunner
from scrapy.settings import Settings
from twisted.internet import reactor
from collections import Counter
import re
import logging
import requests


# Funktion zum Bewerten eines Absatzes anhand der Häufigkeit bestimmter Schlüsselwörter
def score_paragraph(paragraph, keywords):
    # Findet alle Wörter im Absatz und zählt ihre Vorkommen
    words = re.findall(r'\w+', paragraph)
    word_count = Counter(words)
    # Berechnet den Gesamtscore, indem die Anzahl jedes Schlüsselwortes summiert wird
    score = sum(word_count.get(word, 0) for word in keywords)
    return score


# Funktion zur Überprüfung, ob ein Text relevant ist
def is_relevant(text):
    # Liste der irrelevanten Schlüsselwörter
    irrelevant_keywords = ['Newsletter', 'wikiHow', 'Referenzen', 'Autoren', 'anmelden', 'Registriere', 'Mitverfassern',
                           'aufgerufen']
    # Überprüft, ob der Text keines der irrelevanten Schlüsselwörter enthält
    return not any(keyword in text for keyword in irrelevant_keywords)


# Spider-Klasse für das Crawlen von Webseiten und das Extrahieren von Informationen
class TopicsSpider(scrapy.Spider):
    name = 'topics'

    # Startet die Anfragen an die URLs, die aus den Google-Suchergebnissen stammen
    def start_requests(self):
        # API-Schlüssel, Suchmaschinen-ID und Suchanfrage
        API_KEY = 'IHR_API_SCHLÜSSEL'
        SEARCH_ENGINE_ID = 'IHRE_SUCHMASCHINEN_ID'
        SEARCH_QUERY = 'IHR_SUCHBEGRIFF'
        # Ableiten der Schlüsselwörter aus der Suchanfrage
        self.keywords = SEARCH_QUERY.split()
        # Aufbau der Suchanfrage-URL und Abrufen der Daten
        search_url = f"https://www.googleapis.com/customsearch/v1?key={API_KEY}&cx={SEARCH_ENGINE_ID}&q={SEARCH_QUERY}"
        data = requests.get(search_url).json()
        # Extrahieren der ersten drei URLs aus den Suchergebnissen
        urls = [item['link'] for item in data.get('items', [])][:3]
        for url in urls:
            yield scrapy.Request(url, self.parse)

    # Verarbeitet die Antwort von jeder URL
    def parse(self, response, **kwargs):
        # Extrahiert Absätze und bewertet sie anhand der Schlüsselwörter
        paragraphs = response.css('p:not(.footer, .byline, .metadata)').extract()
        scored_paragraphs = [(score_paragraph(p, self.keywords), p) for p in paragraphs if is_relevant(p)]
        # Sortiert die Absätze nach ihrem Score und gibt die Top 10 zurück
        top_paragraphs = sorted(scored_paragraphs, key=lambda x: x[0], reverse=True)[:10]
        for score, paragraph in top_paragraphs:
            yield {'text': paragraph}


# Klasse zur Steuerung des Crawling-Prozesses
class CrawlerControl:
    def __init__(self):
        # Einstellungen für das Speichern der Ergebnisse als JSON
        self.settings = Settings({
            'FEED_FORMAT': 'json',
            'FEED_URI': 'output.json'
        })
        # Initialisieren des CrawlerRunners mit diesen Einstellungen
        self.runner = CrawlerRunner(self.settings)
        self.crawling = False

    # Startet den Crawler
    def run(self):
        if not self.crawling:
            self.crawling = True
            # Startet den TopicsSpider und fügt die stop-Methode als Callback hinzu
            d = self.runner.crawl(TopicsSpider)
            d.addBoth(self.stop)
            reactor.run()

    # Stoppt den Crawler und den Twisted-Reactor
    def stop(self):
        if self.crawling:
            self.crawling = False
            reactor.stop()


# Konfiguration des Loggings
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

# Erstellen und Starten des CrawlerRunners mit der CrawlerControl-Klasse
crawler_control = CrawlerControl()
crawler_control.run()
