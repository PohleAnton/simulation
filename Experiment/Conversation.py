import json

from Database.Person import Person
from Database.Database import Database  # Import the Database class
import openai
import yaml
import os

with open('config.yml', 'r') as ymlfile:
    cfg = yaml.safe_load(ymlfile)
openai.api_key = os.getenv('openai')
print(openai.api_key)
# Now you can use the Database class
database = Database()
print("Person:", Person)
person1 = database.get_person_by_pid(6)
person2 = database.get_person_by_pid(7)

persons_array = [person1, person2]

# weiß nicht so richtig, wohin ich das refactorieren soll...
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
                                            "description": "A few words (maximal 30 words)What the thinker thinks about this participant. Should be personal, what they like or dislike about them"
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

prompt = 'conversation between 2 people: ' + str(person1) + '\n' + str(person2)

# erzeugt erstmal die konversation
intro = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-1106",
    messages=[
        {"role": "user", "content": prompt}
    ]
)

conversation = intro.choices[0].message.content

# nimmt die konversation und führt die 1. methode darauf aus
function_one = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-1106",
    messages=[
        {"role": "user", "content": conversation}
    ]
    ,
    functions=functions,
    function_call={'name': 'rate_conversation'},

)
# schreibt diese in einen string und ein json
content_one = function_one["choices"][0]["message"]["function_call"]["arguments"]
content_json_one = json.loads(content_one)

# führt die 2. methode auf die gleiche konversation aus
function_two = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-1106",
    messages=[
        {"role": "user", "content": conversation}
    ]
    ,
    functions=functions,
    function_call={'name': 'thoughts_on_person'},

)
# schreibt diese in einen string und ein json
content_two = function_two["choices"][0]["message"]["function_call"]["arguments"]
content_json_two = json.loads(content_two)
print(content_two)


def process_persons_and_json(persons_array, content_json_str, database):
    # Convert the JSON string to a dictionary
    content_json = json.loads(content_json_str)

    # Create a dictionary to map names to pk for quick lookup
    name_to_pk = {person.name: person.pk for person in persons_array}
    print(name_to_pk)
    # Iterate through each entry in the participants array of the JSON
    for participant in content_json["participants"]:
        thinker_name = participant["thinker"]["name"]
        print(thinker_name)
        # Check if the thinker is in our persons_array
        if thinker_name in name_to_pk:
            thinker_pk = name_to_pk[thinker_name]

            # Process each thought
            for thought in participant["thoughts"]:
                thought_person_name = thought["name"]
                thought_content = thought["thought"]
                print(thought_content)
                # Check if the thought person is in our persons_array
                if thought_person_name in name_to_pk:
                    thought_person_pk = name_to_pk[thought_person_name]
                    thoughts = database.get_thoughts(thinker_pk, thought_person_pk)
                    print(len(thoughts))
                    print(thoughts)
                    if len(thoughts) == 0:
                        database.insert_thoughts(thinker_pk, thought_person_pk, thought_content)
                    elif len(thoughts) != 0:
                        database.update_thoughts(thinker_pk, thought_person_pk, thought_content)
                    print(len(thoughts))
                    # Print the combination of the thinker's pk and the thought person's pk
                    print((thinker_pk, thought_person_pk))


process_persons_and_json(persons_array, content_two, database)

