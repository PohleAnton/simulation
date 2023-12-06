import copy
import json
import os

import yaml
import openai
import random

config = yaml.safe_load(open("../config.yml"))
openai.api_key = os.getenv('openai')

print(openai.api_key)

f = open('templates/test.txt')
prompt = f.read()
f.close()

prompt2 = {
    'role': 'user',
    'content': prompt
}

functions = [
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
    }
    #,
    #{
    #    "name": "thoughts_on_person",
    #    "description": "A function that rates aspects of a conversation from 1-5 for each participant. 1 is the worst, 5 is the best.",
    #    "parameters":
    #}
]

intro = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-1106",
    messages=[
        {"role": "user", "content": prompt}
    ],
    functions=functions,
    function_call={'name': 'rate_conversation'}

)

content = intro["choices"][0]["message"]["function_call"]["arguments"]
content_json = json.loads(content)
print(content)
