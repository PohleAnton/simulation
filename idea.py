import yaml
import openai
import time


class Agent:
    def __init__(self, name, personality_profile, zodiac_sign, occupation, sport, alcohol, languages, interests):
        self.name = name
        self.personality_profile = personality_profile
        self.zodiac_sign = zodiac_sign
        self.occupation = occupation
        self.sport = sport  # "häufig", "selten" oder "nie"
        self.alcohol = alcohol  # "in Gesellschaft", "nie", "gelegentlich"
        self.languages = languages  # Liste von Sprachen
        self.interests = interests  # Liste von Interessen
        self.conversation_history = []  # Liste zur Speicherung der Konversationen

        # Vorstellungsnachricht bei der Initialisierung
        self.introduce_yourself()

    def introduce_yourself(self):
        introduction = f"Hi, I'm {self.name}! I'm an {self.occupation}, and my zodiac sign is {self.zodiac_sign}. In my free time, I {self.sport} and {self.alcohol} drink. I speak {', '.join(self.languages)} and my interests include {', '.join(self.interests)}."
        self.add_message_to_history("assistant", introduction)

    def behave_based_on_personality(self, other_agent):
        personality = self.personality_profile
        common_interests = set(self.interests).intersection(other_agent.interests)

        if personality == "INTJ":
            if self.speaks_same_language(other_agent):
                return "I prefer logical and structured conversations."
            else:
                return "Let's communicate in English."
        elif personality == "ENFP":
            if common_interests:
                return "I'm enthusiastic and enjoy discussing creative ideas."
            else:
                return "Our interests don't seem to align, but I'm open to new topics."
        elif personality == "ISTP":
            if self.speaks_same_language(other_agent):
                return "I'm practical and enjoy hands-on activities."
            else:
                return "Let's communicate in English."
        elif personality == "ESFJ":
            if common_interests:
                return "I value social harmony and relationships."
            else:
                return "It's important to build connections with others."
        elif personality == "INTP":
            if self.speaks_same_language(other_agent):
                return "I'm analytical and enjoy intellectual challenges."
            else:
                return "Let's communicate in English."
        elif personality == "ESTJ":
            if common_interests:
                return "I'm organized and goal-oriented."
            else:
                return "We should set clear objectives for our conversation."
        elif personality == "ENTJ":
            if self.speaks_same_language(other_agent):
                return "I'm decisive and goal-driven."
            else:
                return "Let's communicate in English."
        elif personality == "ISTJ":
            if common_interests:
                return "I'm reliable and follow rules and standards."
            else:
                return "It's important to maintain a sense of order."
        elif personality == "INFJ":
            if self.speaks_same_language(other_agent):
                return "I'm empathetic and value meaningful connections."
            else:
                return "Let's communicate in English."
        elif personality == "ENFJ":
            if common_interests:
                return "I'm inspirational and passionate about collaboration."
            else:
                return "We can explore topics that inspire us both."
        elif personality == "ISFJ":
            if common_interests:
                return "I'm caring and considerate of others' needs."
            else:
                return "Let's focus on building a positive connection."
        elif personality == "ESFP":
            if common_interests:
                return "I'm lively and enjoy entertaining conversations."
            else:
                return "Let's keep the conversation fun and engaging."
        elif personality == "ENTP":
            if self.speaks_same_language(other_agent):
                return "I'm curious and love exploring new ideas."
            else:
                return "Let's communicate in English."
        elif personality == "ISFP":
            if common_interests:
                return "I'm artistic and appreciate beauty."
            else:
                return "Let's discuss topics that resonate with our creative sides."
        elif personality == "ESTP":
            if common_interests:
                return "I'm adventurous and open to exciting discussions."
            else:
                return "Let's dive into thrilling topics and experiences."

        # Fallback-Verhalten, falls der Persönlichkeitstyp nicht erkannt wird
        return "I have a unique personality, and our interaction depends on our common interests and communication."

    # Füge eine Nachricht zur Konversationshistorie hinzu
    def add_message_to_history(self, role, content):
        self.conversation_history.append({"role": role, "content": content})

    # Gib die gesamte Konversationshistorie des Agents zurück
    def get_conversation_history(self):
        return self.conversation_history

    # Generiere eine Antwort mit timeout und retry
    # Generiere eine Antwort mit timeout und retry
    def generate_response(self, conversation):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=conversation,
                timeout=5  # Set a timeout (in seconds)
            )
            if response.choices:
                return response.choices[0].message.content
            else:
                return None
        except Exception as e:
            print(f"Error generating response: {e}")
            return None

    # Überprüfe, ob der Agent dieselbe Sprache wie ein anderer Agent spricht
    def speaks_same_language(self, other_agent):
        common_languages = set(self.languages).intersection(other_agent.languages)
        return bool(common_languages)


    # Führe eine Konversation zwischen den Agents durch
    # Führe eine Konversation zwischen den Agents durch
    def simulate_conversation(self, agent2, max_duration=10):
        conversation = []
        start_time = time.time()

        # Starte die Konversation
        conversation.append({"role": "system", "content": "You are starting a conversation between two agents."})

        # Überprüfe, ob beide Agents Deutsch sprechen
        both_agents_speak_german = "Deutsch" in self.languages and "Deutsch" in agent2.languages

        while time.time() - start_time < max_duration:
            # Füge die Nachrichten des aktuellen Agents zur Konversation hinzu
            for message in self.get_conversation_history():
                conversation.append({"role": "user", "content": message["content"]})
                print(f"{self.name}: {message['content']}")

            # Füge die Nachrichten des zweiten Agents zur Konversation hinzu
            for message in agent2.get_conversation_history():
                conversation.append({"role": "assistant", "content": message["content"]})
                print(f"{agent2.name}: {message['content']}")

            # Prüfe, ob die Konversation beendet ist
            if time.time() - start_time >= max_duration:
                conversation.append({"role": "user", "content": "Goodbye!"})
                print(f"{self.name}: Goodbye!")
                break

            # Entscheide, in welcher Sprache die Kommunikation stattfinden soll
            if both_agents_speak_german:
                conversation.append({"role": "user", "content": "Lassen Sie uns auf Deutsch kommunizieren."})
                conversation.append({"role": "assistant", "content": "Natürlich, wir können auf Deutsch sprechen."})
            else:
                conversation.append({"role": "user", "content": "Let's communicate in English."})
                conversation.append({"role": "assistant", "content": "Sure, we can use English."})

            # Generiere eine Antwort mit timeout und retry
            response = self.generate_response(conversation)
            if response:
                # Füge die Antwort des Modells zur Konversationshistorie hinzu
                self.add_message_to_history("user", response)
                print(f"{self.name}: {response}")

# Namen für die Agenten
agent_names = ["Alice", "Bob", "Charlie", "David", "Eva", "Frank", "Grace", "Helen", "Isaac", "Julia"]

# Erstellen Sie zehn Agenten mit zufällig ausgewählten Attributen
import random

# Bestimmen Sie die gemeinsame Sprache für die Konversation (Deutsch oder Englisch)
common_language = random.choice(["Deutsch", "Englisch"])

agents = []
for name in agent_names:
    personality_profile = random.choice(["INTJ", "ENFP", "ISTP", "ESFJ", "INTP", "ESTJ", "ENTJ", "ISTJ", "INFJ", "ENFJ"])
    zodiac_sign = random.choice(["Stier", "Krebs", "Wassermann", "Löwe", "Zwillinge", "Schütze", "Waage", "Krebs", "Steinbock", "Fische"])
    occupation = random.choice(["Ingenieur", "Künstler", "Lehrer", "Arzt", "Forscher", "Manager", "Unternehmer", "Buchhalter", "Therapeut", "Lehrer"])
    sport = random.choice(["häufig", "selten", "nie"])
    alcohol = random.choice(["in Gesellschaft", "nie", "gelegentlich"])

    # Wenn die gemeinsame Sprache Englisch ist, übersetzen Sie die Attributwerte
    if common_language == "Englisch":
        languages = random.sample(["German", "English", "Spanish", "French", "Chinese", "Italian"], random.randint(1, 3))
        interests = random.sample(["Reading", "Traveling", "Cooking", "Hiking", "Movies", "Programming", "Dancing", "Crafts", "Swimming", "Theater", "Photography", "Business", "Meditation", "Yoga", "Art"], random.randint(1, 4))
    else:
        languages = random.sample(["Deutsch", "Englisch", "Spanisch", "Französisch", "Chinesisch", "Italienisch"], random.randint(1, 3))
        interests = random.sample(["Lesen", "Reisen", "Kochen", "Wandern", "Kino", "Programmieren", "Tanzen", "Basteln", "Schwimmen", "Theater", "Fotografie", "Geschäft", "Meditation", "Yoga", "Kunst"], random.randint(1, 4))

    agent = Agent(name, personality_profile, zodiac_sign, occupation, sport, alcohol, languages, interests)
    agents.append(agent)

# Führen Sie Konversationen zwischen den Agenten durch
for i, agent1 in enumerate(agents):
    for j, agent2 in enumerate(agents):
        if i != j:  # Verhindern, dass ein Agent mit sich selbst spricht
            print(f"Konversation zwischen {agent1.name} und {agent2.name} (maximale Dauer von 10 Sekunden)")
            agent1.simulate_conversation(agent2, max_duration=5)
            print("\n")