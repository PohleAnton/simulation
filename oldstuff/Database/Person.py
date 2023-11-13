import json
import mariadb
import os

import openai
import yaml


# ich definiere hier mal eine andere, sehr viel weniger komplexe person. diese hat alle eigenschaften, die aktuell in
# der tabelle person gespeichert werden
class Person:
    def __init__(self, name, myers_briggs_type, personality_traits, interests, pk):
        self.name = name
        self.myers_briggs_type = myers_briggs_type
        self.personality_traits = personality_traits
        self.interests = interests
        self.pk = pk

    # das könnte super nützlich sein: das verwandelt ein objekt in einen lesbaren String - also auch für das LLM lesbar
    # die personen bekommen zwar den pk - allerdings nur für die datenbankabfrage. der string lässt diesen bewusst aus,
    # um das llm nicht mit einer willkürlichen zahl zu verwirren
    def __str__(self):
        return f"Person(name={self.name}, myers_briggs_type={self.myers_briggs_type}, personality_traits={self.personality_traits}, interests={self.interests}, pk={self.pk})"
