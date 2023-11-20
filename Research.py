import json
import openai
import yaml

config = yaml.safe_load(open("config.yml"))
openai.api_key = config.get('KEYS', {}).get('openai')


def research_web(topic):
    # Hier die Logik für die Websuche implementieren und das Ergebnis zurückgeben
    result = f"Ergebnisse für {topic} gefunden."
    return result


functions = [
    {
        "name": "results_of_matches",
        "description": "A function, to give the results of matches in various sports",
        "parameters": {
            "type": "object",
            "properties": {
                "matches": {
                    "type": "array",
                    "description": "A list of all matches in that sport",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sport": {
                                "type": "String",
                                "description": "What kind of sport is this match"
                            },
                            "participants": {
                                "type": "String",
                                "description": "Which teams played in that match"
                            },
                            "result": {
                                "type": "String",
                                "description": "The result of that match, e.g. 1:0 for Germany"
                            },
                            "place": {
                                "type": "String",
                                "description": "Where was that match played"
                            },
                            "time": {
                                "type": "String",
                                "description": "The date and the time of that match"
                            }
                        }
                    }
                }
            }
        }
    },
    {
        "name": "research_web",
        "description": "A function, that search the web for a specific topic",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "A given topic to search the web for"
                },
                "result": {
                    "type": "string",
                    "description": "result of the search"
                }
            }
        }
    }
]

topic = "aktuelles Wetter in Berlin"
user_input = f"Beschreibe {topic}"

test_input = ("Give me all matches, their results and other data, of the german nationalteam "
              "in soccer, basketball and volleyball")

vector_test = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-1106",
    messages=[
        {"role": "user", "content": test_input}
    ],
    functions=functions,
    function_call={'name': 'results_of_matches'},
)

content = vector_test["choices"][0]["message"]["function_call"]["arguments"]
data = json.loads(content)
print(data)
