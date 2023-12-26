import openai
import yaml
from http import client

# Laden der Konfigurationsdatei, die die API-Schlüssel enthält.
# Die Datei 'config.yml' sollte im gleichen Verzeichnis wie dieses Skript liegen
# und im YAML-Format den OpenAI-API-Schlüssel unter 'KEYS' > 'openai' speichern.
config = yaml.safe_load(open("./config.yml"))
openai.api_key = config['KEYS']['openai']

# Erstellen eines Assistenten für Konversationsanalyse mithilfe der OpenAI API.
# Der Assistent wird konfiguriert, um Gespräche zu analysieren und Schlüsselthemen,
# Stimmungen und Dynamiken zu identifizieren. Das Modell 'gpt-4-1106-preview' wird dabei verwendet.
assistant = client.beta.assistants.create(
    name="Conversation Analyzer",
    instructions="You are skilled in analyzing conversations. Identify key themes, sentiments, and dynamics in the provided conversation.",
    tools=[{"type": "text_analysis"}],  # Angenommen, dies ist ein verfügbares Textanalyse-Werkzeug.
    model="gpt-4-1106-preview"
)

# Erstellen eines Threads, der als Container für die Konversationsanalyse dient.
thread = client.beta.threads.create()

# Hinzufügen einer Nachricht zu diesem Thread, die eine Beispielkonversation enthält.
# Diese Nachricht fungiert als Eingabeaufforderung für den Assistenten zur Analyse.
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Here is a conversation I had: [Insert conversation here]. Can you analyze it?"
)

# Starten der Analyse durch Ausführung des zuvor erstellten Assistenten.
run = client.beta.threads.runs.create(
  thread_id=thread.id,
  assistant_id=assistant.id,
  instructions="Analyze the conversation for emotional tone, themes, and participant dynamics."
)

# Abrufen des Ergebnisses der Konversationsanalyse.
analysis_result = client.beta.threads.runs.retrieve(
  thread_id=thread.id,
  run_id=run.id
)

# Abrufen aller Nachrichten des Threads, um die Konversation und ihre Analyse zu betrachten.
messages = client.beta.threads.messages.list(
  thread_id=thread.id
)

# Hier ist ein alternativer Ansatz, der die OpenAI API direkt verwendet,
# ohne einen Assistenten oder einen Thread zu erstellen.
# Die Konversation wird als String vorbereitet und direkt zur Analyse an OpenAI gesendet.
# Dieser Ansatz verwendet das Modell 'gpt-4' oder 'gpt-3.5-turbo'.
konversationstext = "Hier ist der Text der Konversation, die analysiert werden soll."

# Senden einer Anfrage an die OpenAI API zur Analyse der Konversation.
# Die Anfrage enthält den Konversationstext und spezifische Anweisungen für die Analyse.
response = openai.Completion.create(
    model="gpt-4",  # oder gpt-3.5-turbo
    prompt=f"Bitte analysiere die folgende Konversation für emotionale Töne, Hauptthemen und die Dynamik zwischen den Teilnehmern:\n\n{konversationstext}",
    max_tokens=150
)

# Verarbeiten und Ausgeben der Analyseergebnisse der Konversation.
analyseergebnisse = response.choices[0].text
print(analyseergebnisse)
