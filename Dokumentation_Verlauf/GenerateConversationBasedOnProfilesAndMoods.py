from random import random

import openai
import yaml
import os
import json

from Dokumentation_Verlauf.FocusedConversationApproach.GeneratePersonsMethods import both

# Dieses Skript liest Personenprofile und Stimmungsdaten aus Textdateien ein, erstellt dann ein Konversations-Prompt
# basierend auf diesen Daten und verwendet die OpenAI-ChatCompletion-API, um eine Konversation zu generieren und zu analysieren.
# Die analysierte Konversation wird in thematische Abschnitte unterteilt, und die Informationen zu jedem Thema werden in
# Dateien gespeichert. Schließlich werden Wikipedia-ähnliche Aufzählungspunkte aus den analysierten Themen extrahiert und
# in einer Liste zurückgegeben.


with open('config.yml', 'r') as ymlfile:
    cfg = yaml.safe_load(ymlfile)
openai.api_key = cfg.get('openai')
os.environ['OPENAI_API_KEY'] = cfg.get('openai')

# Pfade zu den Ordnern aus welchen die Personenprofile und die Moods stammen
person_profile_path = "PersonProfiles"
mood_and_conversation_dynamic_path = "MoodAndConversationDynamics"


def get_random_file_content(directory):
    # Stellt sicher, dass das Verzeichnis existiert und Textdateien enthält
    if not os.path.exists(directory) or not os.listdir(directory):
        return None
    # Wählt eine zufällige Textdatei aus dem Verzeichnis aus und gibt ihren Inhalt zurück
    text_files = [file for file in os.listdir(directory) if file.endswith('.txt')]
    if text_files:
        random_file = random.choice(text_files)
        with open(os.path.join(directory, random_file), 'r') as file:
            return file.read().strip()
    else:
        return None


def create_conversation_prompt(person_profile_path, mood_and_conversation_dynamic_path):
    # Ruft Inhalte aus zwei Gruppen von Dateien ab und erstellt einen Gesprächsprompt
    profile_contents = []
    while len(profile_contents) < 2:
        content = get_random_file_content(person_profile_path)
        if content and content not in profile_contents:
            profile_contents.append(content)

    mood_contents = []
    while len(mood_contents) < 2:
        content = get_random_file_content(mood_and_conversation_dynamic_path)
        if content and content not in mood_contents:
            mood_contents.append(content)

    if not profile_contents or not mood_contents:
        return "Not enough files in the directories to create a prompt."

    prompt = ("Generiere eine Konversation basierend auf den Daten der folgenden Teilnehmer: "
              f"\n({profile_contents[0]} + {mood_contents[0]}) "
              f"\n({profile_contents[1]} + {mood_contents[1]})")
    return prompt


# Erstelle den Prompt
generated_prompt = create_conversation_prompt(person_profile_path, mood_and_conversation_dynamic_path)
print(generated_prompt)

functions = [
    {
        "name": "structure_conversation",
        "description": "A function divides a conversation by its themes, finds subtitles for each theme, and summarizes what each participant had to say about that subject",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Brief description of the conversation and who took part"
                },
                "themes": {
                    "type": "array",
                    "description": "A list of all the themes that came up",
                    "items": {
                        "type": "object",
                        "properties": {
                            "theme": {
                                "type": "string",
                                "description": "Each theme that has been brought up - what the most fitting Wikipedia-article might be called"
                            },
                            "content": {
                                "type": "array",
                                "description": "What each participant said about that subject",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "Name of the participant. Write like this: {name} thinks:"
                                        },
                                        "summary": {
                                            "type": "string",
                                            "description": "Summary of what they said about that topic. Start like this: \"I think...\""
                                        },
                                        "liking": {
                                            "type": "string",
                                            "description": "How much the participant liked that part of the conversation on a scale from 1 - 5, 1 being the lowest, 5 the highest score. Always write like this:  {name} gives it a {rating}"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    },
]

"""diese Methode """


def analyze_conversation_with_functions(function_name, functions, conversation):
    """
    Processes a conversation string with a specified function and a set of additional functions
    using OpenAI's ChatCompletion API.

    :param function_name: A string representing the name of the primary function to be used in the analysis.
    :param functions: An array of additional functions to be used in the analysis.
    :param conversation: A string representing the conversation to be analyzed.
    :return: The JSON the function call produces.
    """

    # Call OpenAI's ChatCompletion API
    vector_test = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "user", "content": function_name + conversation}
        ],
        functions=functions,
    )

    # Return the arguments from the function call in the API response
    return vector_test["choices"][0]["message"]["function_call"]["arguments"]


"""example use:"""
result = analyze_conversation_with_functions('structure_conversation', functions, both[1])
print(result)

"""diese methode returned eine Liste von Strings - diese sind Wikipedia-Überschriften wenigstens ähnlich. """


def wikiresult_from_function_call(result):
    """
    Processes a JSON string containing themed data and saves each theme's content to a file.
    Each file is named using a base title and the theme's title. Returns a list of Wikipedia-style
    bullet points derived from the themes.

    :param result: A JSON-formatted string containing the data to be processed.
    :return: A list of strings, each a Wikipedia-style bullet point derived from the themes.
    """

    # Parse the JSON data
    data = json.loads(result)

    # Create a base title for file naming
    base_title = data["title"].replace(' ', '_')

    # Create directories for storing files
    directory = './FocusedConversationApproach/txtFiles/ConversationChunks'
    if not os.path.exists(directory):
        os.makedirs(directory)
    target_dir = 'FocusedConversationApproach/txtFiles/ConversationChunks/used/'
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    wikipedia = []

    # Process each theme and save to files
    for theme in data["themes"]:
        theme_title = theme["theme"].replace(' ', '_').replace('\'', '').replace('\"', '').replace('?', '')
        filename = f"{base_title}_{theme_title}.txt"
        file_path = os.path.join(directory, filename)
        wikipedia.append(theme['theme'])

        if 'liking' in theme['content'][0]:
            content = '\n\n'.join(
                [f'{entry["name"]}:\n{entry["summary"]} {entry["liking"]}' for entry in theme["content"]])
        else:
            content = '\n\n'.join([f'{entry["name"]}:\n{entry["summary"]}' for entry in theme["content"]])

        with open(file_path, 'w') as file:
            file.write(content)

    return wikipedia


"""example use"""
wiki = wikiresult_from_function_call(result)
print(wiki[0])
