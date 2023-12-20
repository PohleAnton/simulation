import openai
import yaml
from http import client

# Konfigurationsdatei laden
config = yaml.safe_load(open("./config.yml"))
openai.api_key = config['KEYS']['openai']

# Assistent für Konversationsanalyse erstellen
assistant = client.beta.assistants.create(
    name="Conversation Analyzer",
    instructions="You are skilled in analyzing conversations. Identify key themes, sentiments, and dynamics in the provided conversation.",
    tools=[{"type": "text_analysis"}],  # Angenommen, es gibt ein Textanalyse-Werkzeug
    model="gpt-4-1106-preview"
)

# Thread für die Konversationsanalyse erstellen
thread = client.beta.threads.create()

# Nachricht mit einer Beispielkonversation erstellen
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Here is a conversation I had: [Insert conversation here]. Can you analyze it?"
)

# Analyse der Konversation anfordern
run = client.beta.threads.runs.create(
  thread_id=thread.id,
  assistant_id=assistant.id,
  instructions="Analyze the conversation for emotional tone, themes, and participant dynamics."
)

# Ergebnisse der Analyse abrufen
analysis_result = client.beta.threads.runs.retrieve(
  thread_id=thread.id,
  run_id=run.id
)

# Gesamte Nachrichten des Threads abrufen
messages = client.beta.threads.messages.list(
  thread_id=thread.id
)

#oder anders aber noch ohne Abruf der Konversation aus der Vektordatenbank
# Konversation als Text vorbereiten
konversationstext = "Hier ist der Text der Konversation, die analysiert werden soll."

# Anfrage an die OpenAI API senden
response = openai.Completion.create(
    model="gpt-4",  # oder gpt-3.5-turbo
    prompt=f"Bitte analysiere die folgende Konversation für emotionale Töne, Hauptthemen und die Dynamik zwischen den Teilnehmern:\n\n{konversationstext}",
    max_tokens=150
)

# Analyseergebnisse verarbeiten
analyseergebnisse = response.choices[0].text
print(analyseergebnisse)
