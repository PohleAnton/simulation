import openai
import time

class ConversationAnalyzer:
    def __init__(self, model_name="gpt-4-1106-preview"):
        self.model = model_name

    def analyze(self, conversation):
        try:
            response = openai.Completion.create(
                model=self.model,
                prompt=f"Analysiere die folgende Konversation: {conversation}",
                max_tokens=100
            )
            return response.choices[0].text
        except Exception as e:
            return f"Fehler bei der Analyse: {str(e)}"

class Agent:
    def __init__(self, name, age, occupation, interests, characteristics, mbti):
        self.name = name
        self.age = age
        self.occupation = occupation
        self.interests = interests
        self.characteristics = characteristics
        self.mbti = mbti
        self.conversation_history = []
        self.analyzer = ConversationAnalyzer()
        self.introduce_yourself()

    def introduce_yourself(self):
        intro_message = f"Hi, I'm {self.name}, a {self.age}-year-old {self.occupation}. I'm interested in {', '.join(self.interests)}."
        self.add_message_to_history("system", intro_message)

    def add_message_to_history(self, role, content):
        self.conversation_history.append({"role": role, "content": content})

    def get_conversation_history(self):
        return self.conversation_history

    def simulate_conversation(self, agent2, max_duration=10):
        self.add_message_to_history("system", f"You are starting a conversation between {self.name} and {agent2.name}.")
        start_time = time.time()

        while time.time() - start_time < max_duration:
            self_response = f"{self.name} says something based on their personality."
            agent2_response = f"{agent2.name} responds based on their personality."

            self.add_message_to_history("user", self_response)
            agent2.add_message_to_history("assistant", agent2_response)

            if time.time() - start_time >= max_duration:
                break

        self.analyze_conversation()

    def analyze_conversation(self):
        conversation_text = "\n".join([msg["content"] for msg in self.conversation_history])
        analysis_result = self.analyzer.analyze(conversation_text)
        print("Analysis: ", analysis_result)



agents = [
    Agent("Tina Schneider", 31, "Sozialunternehmerin", ["Nachhaltigkeit", "Yoga", "Dokumentarfilme"], ["Visionärin", "weltoffen", "geduldig"], "ENFJ"),
    Agent("Raj Patel", 28, "Grafikdesigner", ["Typografie", "Urban Art", "Elektronische Musik"], ["Kreativ", "detailorientiert", "kommunikativ"], "ISFP"),
    Agent("Elena Sorokina", 35, "Astronomin", ["Weltraumforschung", "klassische Literatur", "Geige spielen"], ["Nachdenklich", "analytisch", "musikalisch"], "INTJ"),
    Agent("Liam Byrne", 42, "Meeresbiologe", ["Tiefseeforschung", "Segeln", "Kochen"], ["Abenteuerlustig", "umweltbewusst", "geduldig"], "ESTP"),
    Agent("Sophia Chen", 26, "App-Entwicklerin", ["Technologischer Fortschritt", "Mode", "Reisen"],["Innovativ", "stilbewusst", "unternehmerisch"], "ENTJ"),
    Agent("Omar Al-Farsi", 39, "Politikwissenschaftler", ["Internationale Beziehungen", "Schreiben", "Jazzmusik"],["Intellektuell", "eloquent", "musikalisch"], "INFJ"),
    Agent("Ava Dupont", 33, "Klimawissenschaftlerin", ["Klimaaktivismus", "Bergsteigen", "Science-Fiction"],["Leidenschaftlich", "resolut", "abenteuerlustig"], "ENFP"),
    Agent("Diego Torres", 45, "Chefkoch", ["Kulinarische Innovationen", "Weinproben", "Tango tanzen"],["Kreativ", "gesellig", "lebensfroh"], "ESFP"),
    Agent("Isabelle Girard", 37, "Bildende Künstlerin", ["Kunstgeschichte", "Philosophie", "Freiwilligenarbeit"],["Reflektierend", "tiefgründig", "empathisch"], "INFP"),
    Agent("Kenji Takahashi", 30, "Archäologe", ["Antike Zivilisationen", "Bouldern", "Animation"],["Forschend", "geduldig", "detailverliebt"], "ISTJ")
]


# Führen Sie Konversationen zwischen den Agenten durch
for i, agent1 in enumerate(agents):
    for j, agent2 in enumerate(agents):
        if i != j:  # Verhindern, dass ein Agent mit sich selbst spricht
            print(f"Konversation zwischen {agent1.name} und {agent2.name} (maximale Dauer von 10 Sekunden)")
            agent1.simulate_conversation(agent2, max_duration=5)
            print("\n")
