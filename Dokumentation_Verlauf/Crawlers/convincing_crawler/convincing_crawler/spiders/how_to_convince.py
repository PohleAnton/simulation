import requests
import scrapy
import yaml
from langchain.adapters import openai
from pydantic import json
from scrapy.crawler import CrawlerRunner
from scrapy.settings import Settings
from twisted.internet import reactor
from collections import Counter
import re
import logging


# Dieser Code implementiert einen Web-Crawler, der speziell darauf ausgerichtet ist,
# Informationen über Überzeugungsstrategien von bestimmten Webseiten zu sammeln.
# Hierfür werden Paragraphen auf den Webseiten basierend auf relevanten Schlüsselwörtern
# und deren Häufigkeit bewertet und gefiltert.
# Der Crawler begrenzt die Textlänge der extrahierten Inhalte und speichert sie in einer JSON-Datei.
# Nach dem Crawling-Prozess wird diese Datei an eine GPT-basierte API gesendet, um die Inhalte zusammenzufassen.
# Die Zusammenfassung wird dann in derselben JSON-Datei gespeichert,
# wodurch der ursprüngliche Inhalt überschrieben wird.


# Funktion zum Bewerten eines Absatzes basierend auf der Häufigkeit bestimmter Schlüsselwörter
def score_paragraph(paragraph):
    # Definierte Schlüsselwörter, die auf Überzeugungsstrategien hinweisen
    keywords = ['überzeugen', 'Technik', 'Strategie', 'Argument', 'Kommunikation']
    # Findet alle Wörter im Absatz und zählt ihre Vorkommen
    words = re.findall(r'\w+', paragraph)
    word_count = Counter(words)
    # Berechnet den Gesamtscore basierend auf der Häufigkeit der Schlüsselwörter
    score = sum(word_count.get(word, 0) for word in keywords)
    return score


# Funktion zur Überprüfung, ob ein Text relevant ist
def is_relevant(text):
    # Liste irrelevanter Schlüsselwörter, die im Text nicht vorkommen sollten
    irrelevant_keywords = ['Newsletter', 'wikiHow', 'Referenzen', 'Autoren', 'anmelden', 'Registriere', 'Mitverfassern',
                           'aufgerufen']
    # Überprüft, ob der Text keines der irrelevanten Schlüsselwörter enthält
    return not any(keyword in text for keyword in irrelevant_keywords)


# Funktion zur Begrenzung der Textlänge auf eine maximale Anzahl von Zeilen
def limit_text_length(text, max_lines=10):
    # Teilt den Text in Zeilen und behält nur die ersten max_lines Zeilen bei
    return '\n'.join(text.split('\n')[:max_lines])


# Spider-Klasse für das Crawlen von Webseiten und Extrahieren von Informationen über Überzeugungsstrategien
class ConvincingSpider(scrapy.Spider):
    name = 'how_to_convince'
    # Definierte URLs, die gecrawlt werden sollen
    start_urls = [
        'https://de.wikihow.com/Menschen-%C3%BCberzeugen',
        'https://de.wikihow.com/Jemanden-mit-unterbewussten-Techniken-%C3%BCberzeugen',
        'https://karrierebibel.de/menschen-ueberzeugen/'
    ]

    # Verarbeitet die Antwort von jeder URL
    def parse(self, response, **kwargs):
        # Extrahiert Absätze von der Webseite
        paragraphs = response.css('p:not(.footer):not(.byline):not(.metadata)').extract()
        # Bewertet und filtert die Absätze basierend auf Relevanz
        scored_paragraphs = [(score_paragraph(p), p) for p in paragraphs if is_relevant(p)]
        # Sortiert die Absätze nach ihrem Score und begrenzt ihre Länge
        top_paragraphs = sorted(scored_paragraphs, key=lambda x: x[0], reverse=True)[:10]
        for score, paragraph in top_paragraphs:
            limited_paragraph = limit_text_length(paragraph)
            yield {'text': limited_paragraph}


# Klasse zur Steuerung des Crawling-Prozesses - genaue Implementierung nicht erfolgt, da bisher nicht sicher,
# ob Code wirklich verwendet wird
def summarize_with_gpt_api(data):
    # Implementierung des Aufrufs der GPT-API
    api_url = "URL_DER_GPT_API"
    response = requests.post(api_url, json={"text": data})
    return response.json()  # Erwartet, dass die API eine JSON-Antwort zurückgibt


class CrawlerControl:
    def __init__(self):
        # Einstellungen für das Speichern der Ergebnisse in einer JSON-Datei
        self.settings = Settings({
            'FEED_FORMAT': 'json',
            'FEED_URI': 'convincing_strategy.json'
        })
        # Initialisieren des CrawlerRunners mit diesen Einstellungen
        self.runner = CrawlerRunner(self.settings)
        self.crawling = False

    def run(self):
        # Startet den Crawling-Prozess
        if not self.crawling:
            self.crawling = True
            d = self.runner.crawl(ConvincingSpider)
            # Fügt die post_process-Methode als Callback hinzu
            d.addBoth(self.post_process)
            reactor.run()

    def post_process(self, _):
        # Wird aufgerufen, nachdem der Crawling-Prozess beendet ist
        if self.crawling:
            self.crawling = False
            reactor.stop()
        # Startet die Verarbeitung und das Überschreiben der JSON-Datei
        self.process_and_rewrite_json('convincing_strategy.json')

    @staticmethod
    def process_and_rewrite_json(file_path):
        # Liest die generierte JSON-Datei
        with open(file_path, 'r') as file:
            data = json.load(file)
        # Sendet die Daten an die GPT-API und erhält eine Zusammenfassung
        summary = summarize_with_gpt_api(data)
        # Überschreibt die JSON-Datei mit der erhaltenen Zusammenfassung
        with open(file_path, 'w') as file:
            json.dump({'convincingStrategy': summary}, file, ensure_ascii=False, indent=2)


logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
crawler_control = CrawlerControl()
crawler_control.run()
