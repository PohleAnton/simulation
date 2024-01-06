# Research2.py
Hier werden verschiedene APIs verwendet, um den Teilnehmern der Konversation mehr Wissen zuzuführen.

Alleinautor ist hier ``Sebastian Koch``.


### Google API
Durch die Google API erhalten wir in unserem Programm die Namen von Wikipedia-Artikel. 

Das Endergebnis dieser Arbeit ist die Methode ``research_web(topic, num)`` welcher ein Thema und die Anzahl zu suchender Links übergeben wird. Dafür wird hier mit der Custom-Search-API von Google gearbeitet. Seitens der API ist für jeden Suchvorgang die maximale Anzahl an Ergebnissen auf 10 und die Anzahl täglicher gratis-Anfragen auf 100 beschränkt. Die Methoden ``build_payload(query, num, start)`` und ``make_request(payload)`` unterstützen hierbei.


### Wikipedia API
Mithilfe der Wikipedia API kann man alles was eine Wikipedia Seite bietet extrahieren. Das beinhaltet in unserm Fall nur die Zusammenfassung aktiv. Zu Testzwecken habe ich auch andere Dinge wie der gesamte Artikel, Links, ähnliche Themen etc. die es aber nicht in das fertige Programm geschafft haben.

Das Endergebnis dieser Arbeit ist die Methode ``try_wiki_search(topic, num)``, der ein zu suchendes Thema und Anzahl an Ergebnissen übergeben wird. Diese ruft dann mittels Google-API eine entsprechende Anzahl an Wikipedia-Artikel auf und packt dessen Zusammenfassung in ein String. Die Methode ``organize_research(topic, num)`` agiert fast 1:1, mit dem Zusatz, dass es Zusammenfassung und Titel in einem JSON zusätzlich zum String zurückgibt.

Des Weiteren unterstützen Methoden wie ``check_minimal_parameters(page_py)`` (für Testzwecke Grundlegendes ausgeben), ``get_wikipedia_api_instance(topic)`` (falls für das Thema ein Artikel existiert, erhält man eine API-Instanz dieses Artikels, aus der man alles Mögliche extrahieren kann), ``does_wikipedia_topic_exists(page_py, topic)`` (prüft, ob so ein Artikel existiert), ``get_wikipedia_summary(topic)`` (gibt Zusammenfassung des Artikels zurück).

Zu Beginn habe ich die GPT API die Zusammenfassung extrahieren lassen. Aus Sparmaßnahmen habe ich den Ansatz mit den function_calls dann doch fallen lassen und nur das Suchergebnis von der GPT zusammenfassen lassen.


### Sonstiges 
Das fasst alle APIs, Bibliotheken oder Methoden zur Informationsgewinnung aus dem Internet zusammen, die sich nicht durchsetzen konnten, aber dennoch ausprobiert wurden.

Zu Beginn war die Idee Infos von irgendeiner Seite zu nehmen und auszuwerten. Das habe ich, nach vielen Stunden Einarbeitung in verschiedenste Varianten wie ``googlesearch`` oder ``Urllib``, verworfen, da ich auf die Wikipedia API gestoßen bin.


# Network.py
Dies ist eine erste Variante die verschiedenen Code-Teile des Teams zusammenzuführen.

Dafür habe ich mich auf die Arbeit mit txt-Files konzentriert. Anschließend hat der Herr Pohle den fertigen Code für die Vector-DB abgeändert, schließlich ist daraus die Datei ``MostRecent.py`` abgeleitet worden.

Im Grunde führt das Programm zunächst eine erste Conversation mittels der gestellten Profile (Schema von Fr. Trunte), extrahiert die Themen (Code von Hr. Pohle), erweitert das Wissen aller beteiligten, falls nötig, und führt weitere Konversationen.


# Strategy.py
Dies ist der Versuch mittels Prompts die Konversation so zu lenken, dass am Ende jemand überzeugt wird.

Das Ganze ist von semi-optimalem Erfolg gekrönt. Zwar kann in einigen Fällen ein Teilnehmer von einem anderen überzeugt werden, jedoch nur durch die explizite Anweisung im Prompt, dass eben das passieren soll. Zudem ist das Endergebnis nicht wirklich eine Meinungsänderung über eine tiefgründige Überzeugung, sondern eher eine Akzeptanz für andere Dinge mit dem Hinweis "Ja, du hast recht, so hab ich das nicht gesehen, aber ...".

# ChatBot.py + BiggerChatBot.py
In der Datei `ChatBot.py` wird versucht mittels Streamlit ein Frontend bereitzustellen, sodass der Nutzer hübsch übersichtlich mit dem Programm interagieren kann und ihm die wichtigsten Dinge im Ablauf als Chat-Nachrichten ausgibt. Zwischendurch sollte der User zufällige Themen einstreuen können, die dann für die nächste Konversastion aufgegriffen werden sollen. Nach kurzer Bearbeitungszeit wurde daraus die Datei `BiggerChatBot.py` abgeleitet und mit Herrn Pohles BE Code gefüllt. Ich habe dann weiter an der FE Umsetzung mit Streamlit gearbeitet

```
message_placeholder = st.empty()

for topic in extracted_topics:
    if st.button(topic):
    next_conversation(participants_list, topic)
```