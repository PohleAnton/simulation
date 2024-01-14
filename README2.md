# TeamSimulation Project_1
![image](https://github.com/HTW-WI-KI-WS24/project-teamsimulation/assets/97105009/18ba1c00-6ae9-4398-9445-77be580b0792)

### Teammitglieder:
    Anton Pohle
    Sebastian Koch
    Pauline Trunte

    
### Ausführung des Programms:
Um das Programm auszuführen, verwenden Sie die finale Datei namens "DetailBot.py".
Zur Ausführung wird eine "config.yml"-Datei mit folgendem Setup benötigt:
KEYS:
 openai:
Für die Ausführung des finalen Codes ist lediglich ein OpenAI-Schlüssel erforderlich.
Anschließend müssen Sie im Terminal den Befehl "chroma run" ausführen. In einem
separaten Terminal geben Sie den Befehl "streamlit run DetailBot.py" ein, um das Programm
zu starten.
Die App ist dann über den Browser unter "localhost:8501" verfügbar und kann genutzt
werden.
#### Hinweise zur Ausführung:
Es ist erforderlich, auf die vollständige Ausführung von Chroma zu warten, bevor Streamlit
gestartet wird.
Zusätzlich wird ein Ordner namens "chroma_data" erstellt, der sämtliche Daten aus den
Sitzungen speichert, einschließlich derer, die über Sitzungen hinweg erzeugt werden. 
Dies ist grundsätzlich unproblematisch, jedoch kann dies bei einer zunehmenden Anzahl von
Durchläufen zu einer hohen Token-Auslastung führen. 
Daher empfiehlt es sich möglicherweise, diesen Ordner nach jedem Durchlauf zu löschen.
Es gab auch ein Docker-Setup. Der Commit vom 03.01. unter
https://github.com/HTW-WI-KI-WS24/project-teamsimulation/commit/f9127b1a802522f69f8a
90f72dfadf8af19ec235 kann mithilfe des Befehls "docker-compose up --build" ausgeführt
werden. 
Aufgrund der schlechten Internetverbindung eines Teammitglieds dauerte der
Build-Prozess jedoch unverhältnismäßig lange und wurde daher abgebrochen.

### Hergang des Experiments:
Das Frontend ermöglicht die Auswahl von zwei frei wählbaren Personen und erstellt für
diese individuelle Persönlichkeitsprofile, um anschließend eine Konversation zwischen ihnen
zu simulieren. 
Dabei wurde darauf geachtet, den Tonfall neutral zu gestalten und nicht zu
freundlich wirken zu lassen.

Nach der Konversation werden die diskutierten Themen identifiziert und dem Nutzer zur
Auswahl gestellt. Theoretisch hätte auch ein zufälliges Thema für die Diskussion ausgewählt
werden können, aber dies hätte den Prozess unnötig verlängert und die Kosten erhöht, ohne
substantiellen Mehrwert zu bieten.

Anschließend wird GPT beauftragt, eine Ja-Nein-Frage zum ausgewählten Thema zu
formulieren, beispielsweise „Is reality a simulation“. Daraufhin generiert GPT für jeden
Teilnehmer eine individuelle Überzeugung und bewertet, ob diese Überzeugung die gestellte
Frage mit Ja oder Nein beantwortet. 
Zusätzlich wird jeder Überzeugung ein Score zugewiesen, der die Stärke der Überzeugung ausdrücken soll. Ursprünglich war geplant, die
Diskussion so lange fortzusetzen, bis ein bestimmter Wert erreicht wurde. Dieser Ansatz
wurde jedoch nicht weiter verfolgt.

Zu Demonstrationszwecken wird überprüft, ob beide Teilnehmer die gleiche Überzeugung
vertreten, und gegebenenfalls eine der Überzeugungen ins Gegenteil verkehrt. 
Der ursprüngliche Ansatz, einen Teilnehmer zu beauftragen, den anderen zu überzeugen, erwies
sich als erfolglos. Es stellte sich heraus, dass Personen und Überzeugungen getrennt
behandelt werden müssen, um GPT nicht auf seine Trainingsdaten zurückgreifen zu lassen
und die ursprüngliche Überzeugung beizubehalten. In diesem Zusammenhang wurde auch
die Funktion fix_third_person verwendet, um Aussagen wie „As Karl Marx, I firmly believe“
zu bereinigen.

Anschließend werden beide Teilnehmer beauftragt, ein überzeugendes Argument für ihre
Überzeugung zu generieren. Es war geplant, die Effektivität dieser Argumente zu überprüfen
und das Ergebnis mit der eigenen Überzeugung zu vergleichen, um daraus eine neue
Überzeugung zu generieren und diese erneut von GPT bewerten zu lassen. Dies führte
jedoch fast immer zu einem Meinungswechsel, daher wurde die Idee mit dem Scoring
verworfen.

Stattdessen wurde versucht, Argumente für beide Sichtweisen zu generieren, daraus ein
Meta-Argument zu erstellen und dieses den Überzeugungen gegenüberzustellen. Auch hier
führte dies mit wenigen Ausnahmen immer zu sofortigen Überzeugungswechseln.
Eine detaillierte Darstellung des Überzeugungsprozesses ist in der Präsentation
schematisch enthalten. Abschließend ist festzustellen, dass die Überzeugung fast immer
zugunsten des "Simulation Arguments" ausfällt. Dies legt nahe, dass entweder das
Argument selbst besonders überzeugend ist oder der zugrundeliegende Datensatz eine
Voreingenommenheit aufweist.


