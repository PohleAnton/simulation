import json
import openai
import sys

import Research

openai.api_key = Research.openai.api_key
research_result_list = Research.get_response_for_every_topic()


def get_gpt_response(messages, functions):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=messages,
        functions=functions
    )
    return response


def get_response_message(response):
    response_message = response.choices[0].message
    return response_message


print(Research.get_response_for_every_topic())

"""
TODO:
1. Themen aus der Chroma DB/ den txt-files holen
2. Ergebnisse zu den Themen als eine Collection speichern
3. Metadaten der einzelnen Dokumente: Wissende (alle die davon Ahnung haben, es recherchiert haben)
4. Inhalt der einzelnen Dokumente: Content aus der research_result_list
5. Sobald 2 Personen eine Konversation beendet haben, werden die Themen gesucht und entsprechend in die DB geschrieben
"""
