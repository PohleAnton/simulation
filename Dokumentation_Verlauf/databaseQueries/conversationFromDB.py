"""
Ähnlicher Ansatz wie in ./Database - die Idee war, einmal entdeckte, sinnvolle Personae wieder und wieder zu benutzen.
-->Python muss mit der Datenbank sprechen.
Außerdem sind hier erste Schritte mit Funktion Calls - Personen und Konversationen bewerten ist inzwischen allerdings obsolet.
"""


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
        return f"Person(name={self.name}, myers_briggs_type={self.myers_briggs_type}, personality_traits={self.personality_traits}, interests={self.interests})"


with open('config.yml', 'r') as ymlfile:
    cfg = yaml.safe_load(ymlfile)

# Set the environment variables from the loaded configuration
for key, value in cfg.items():
    os.environ[key] = str(value)

# Access the variables
db_host = os.getenv('DB_HOST')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_db = os.getenv('DB_DB')
openai.api_key = os.getenv('openai')

print(openai.api_key)

conn = mariadb.connect(host=db_host, user=db_user, passwd=db_password, db=db_db)
cur = conn.cursor()
try:
    cur.execute("SELECT * FROM person where pid=6")
    row = cur.fetchone()
    if row:
        person1 = Person(name=row[1], myers_briggs_type=row[2], personality_traits=row[3], interests=row[4], pk=row[0])

    cur.execute("SELECT * FROM person where pid=7")
    row2 = cur.fetchone()

    if row2:
        person2 = Person(name=row2[1], myers_briggs_type=row2[2], personality_traits=row2[3], interests=row2[4],
                         pk=row2[0])
except mariadb.Error as e:
    print(f"Error: {e}")

finally:
    cur.close()
    conn.close()

print(person1)
print(person2)

prompt = 'conversation between 2 people: ' + str(person1) + '\n' + str(person2)

intro = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-1106",
    messages=[
        {"role": "user", "content": prompt}
    ]
)

conversation = intro.choices[0].message.content

functions = [
    # dieser call kann benutzt werden, um eine konversation zu bewerten. die gewählten attribute und skalen sind
    # willkürlich
    {
        "name": "rate_conversation",
        "description": "A function that rates aspects of a conversation from 1-5 for each participant. 1 is the worst, 5 is the best.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "brief description of the conversation"
                },
                "participants": {
                    "type": "array",
                    "description": "A list of the names of all the participants of the conversation",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "name of the participant"
                            },
                            "ratings": {
                                "type": "object",
                                "properties": {
                                    "Warmth": {
                                        "type": "integer",
                                        "description": "how the participant rates the warmth of the conversation"
                                    },
                                    "Intelligence": {
                                        "type": "integer",
                                        "description": "how the participant rates the intelligence of the conversation"
                                    },
                                    "Likes chocolate": {
                                        "type": "boolean",
                                        "description": "does the participant like chocolate?"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    },
    # diese funktion erzeugt eine nested list. jeder teilnehmer macht sich gedanken über die anderen teilnehmer
    {
        "name": "thoughts_on_person",
        "description": "A function that summarizes what each participant thinks about every other participant in the conversation except themselves",
        "parameters": {
            "type": "object",
            "properties": {
                "participants": {
                    "type": "array",
                    "description": "A list of the names of all the participants in the conversation",
                    "items": {
                        "type": "object",
                        "properties": {
                            "thinker": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Name of the participant"
                                    }
                                }
                            },
                            "thoughts": {
                                "type": "array",
                                "description": "A list of thoughts about each other participant",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "Name of the other participant"
                                        },
                                        "thought": {
                                            "type": "string",
                                            "description": "A few words (maximal 30 words)What the thinker thinks about this participant. Maybe what they like or don't like about them"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

]

function_one = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-1106",
    messages=[
        {"role": "user", "content": conversation}
    ]
    ,
    functions=functions,
    function_call={'name': 'rate_conversation'},

)

content_one = function_one["choices"][0]["message"]["function_call"]["arguments"]
content_json_one = json.loads(content_one)
print(content_one)

function_two = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-1106",
    messages=[
        {"role": "user", "content": conversation}
    ]
    ,
    functions=functions,
    function_call={'name': 'thoughts_on_person'},

)

content_two = function_two["choices"][0]["message"]["function_call"]["arguments"]
content_json_two = json.loads(content_two)
print(content_two)

# diese methode
persons = [person1, person2]

def extract_thoughts(data, persons):
    # Parse the input string as JSON
    db_host = os.getenv('DB_HOST')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_db = os.getenv('DB_DB')

    connection = mariadb.connect(host=db_host, user=db_user, passwd=db_password, db=db_db)
    cursor = connection.cursor()

    # Initialize an empty dictionary to store name:thoughts pairs
    thoughts_map = {}
    pids = [person.pk for person in persons]
    print(pids)

    # Close the cursor and connection
    cursor.close()
    connection.close()
    return pids


result = extract_thoughts(content_json_two, persons)
print(result)

