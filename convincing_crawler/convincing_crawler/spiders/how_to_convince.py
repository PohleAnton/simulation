import scrapy
from collections import Counter
import re

class ConvincingSpider(scrapy.Spider):
    name = 'how_to_convince'
    start_urls = [
        'https://de.wikihow.com/Menschen-%C3%BCberzeugen',
        'https://de.wikihow.com/Jemanden-mit-unterbewussten-Techniken-%C3%BCberzeugen',
        'https://karrierebibel.de/menschen-ueberzeugen/'
    ]

    def parse(self, response, **kwargs):
        paragraphs = response.css('p:not(.footer, .byline, .metadata)').extract()
        scored_paragraphs = [(self.score_paragraph(p), p) for p in paragraphs if self.is_relevant(p)]
        top_paragraphs = sorted(scored_paragraphs, key=lambda x: x[0], reverse=True)[:10]
        for score, paragraph in top_paragraphs:
            yield {'text': paragraph}

    def score_paragraph(self, paragraph):
        keywords = ['überzeugen', 'Technik', 'Strategie', 'Argument', 'Kommunikation']
        words = re.findall(r'\w+', paragraph)
        word_count = Counter(words)
        score = sum(word_count.get(word, 0) for word in keywords)
        return score

    def is_relevant(self, text):
        irrelevant_keywords = ['Newsletter', 'wikiHow', 'Referenzen', 'Autoren', 'anmelden', 'Registriere', 'Mitverfassern', 'aufgerufen']
        return not any(keyword in text for keyword in irrelevant_keywords)

# Crawler ausführen mit: scrapy crawl how_to_convince
# Crawler ausführen und Daten im Ordner data in JSON sichern:
# scrapy crawl how_to_convince -o data/how_to_convince.json
