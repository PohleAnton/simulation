import scrapy
from collections import Counter
import re
#Vorgehensweise wie man die Topics aus unserer copy.py in der Google API nutzen würde
#In diesem Fall sollte die Google API die URLs der ersten drei Suchergebnisse zu den Topics
#dem Crawler übergeben, welcher wiederrum die relevanten Parts der Seiten extrahiert und in einer
#JSON speichert.
#Das JSON soll dann wiederrum in der copy.py genutzt werden, um die Informationen an die Agents bzw.
#Personen zu geben, die diese Informationen in der Konversation nutzen

#Ob es sinnvoll ist, das Scraping der Seiten in unsere Konversationen zu geben, ist nicht sicher.
class TopicsSpider(scrapy.Spider):
    name = 'topics'
    start_urls = [
        'https://example.com/page1',  # URL von Google-Suchergebnis 1
        'https://example.com/page2',  # URL von Google-Suchergebnis 2
        'https://example.com/page3',  # URL von Google-Suchergebnis 3
    ]

    def parse(self, response, **kwargs):
        paragraphs = response.css('p:not(.footer, .byline, .metadata)').extract()
        scored_paragraphs = [(self.score_paragraph(p), p) for p in paragraphs if self.is_relevant(p)]
        top_paragraphs = sorted(scored_paragraphs, key=lambda x: x[0], reverse=True)[:10]
        for score, paragraph in top_paragraphs:
            yield {'text': paragraph}

    def score_paragraph(self, paragraph):
        keywords = [#keywords zu den Topics]
        words = re.findall(r'\w+', paragraph)
        word_count = Counter(words)
        score = sum(word_count.get(word, 0) for word in keywords)
        return score

    def is_relevant(self, text):
        irrelevant_keywords = ['Newsletter', 'wikiHow', 'Referenzen', 'Autoren', 'anmelden', 'Registriere', 'Mitverfassern', 'aufgerufen']
        return not any(keyword in text for keyword in irrelevant_keywords)

# Crawler ausführen mit: scrapy crawl topics
# Crawler ausführen und Daten im Ordner data in JSON sichern:
# scrapy crawl topics -o data/topics.json
