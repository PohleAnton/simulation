import html
import json
import os

import openai
import yaml
import re
import urllib.request
import urllib.parse
import requests
from bs4 import BeautifulSoup

# import wikipedia
import wikipediaapi

__author__ = "Sebastian Koch"

config = yaml.safe_load(open("config.yml"))
openai.api_key = config.get('KEYS', {}).get('openai')
google_api_key = config.get('KEYS', {}).get('google')
search_engine_id = config.get('KEYS', {}).get('search_engine_id')
segregation = ("\n\n<<<<< ----- >>>>>       <<<<< ----- >>>>>       <<<<< ----- >>>>>       <<<<< ----- >>>>>\n\n")


# https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list?hl=de
def build_payload(query, start=1, num=10):
    # kann mit date_restict erweitert werden, schränkt Zeit ein
    payload = {
        'key': google_api_key,
        'q': query,
        'cx': search_engine_id,
        'start': start,  # für offsets
        "num": num
    }
    return payload


def clean_filename(filename):
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)  # remove special chars
    return filename


def make_request(payload):
    response = requests.get('https://www.googleapis.com/customsearch/v1', params=payload)
    if response.status_code != 200:
        raise Exception('Request failed')
    return response.json()


def research_web(query):  # kann für die google APi dann erweiter werden, falls nötig
    # Hier die Logik für die Websuche implementieren und das Ergebnis zurückgeben
    result_list = []

    # Option 1: googlesearch
    """
    try:
        from googlesearch import search
    except ImportError:
        print("no module named 'google' found")
    
    for i in search(query, num_results=10, lang=["en", "de"], advanced=True):
        result_list.append(i)
    """

    # Option 2: Urllib
    """
    test_query = 'weather%20Berlin'
    googlesearch = 'https://www.bing.com/search?q=' + test_query
    source = urllib.urlopen(googlesearch)
    source = source.read()
    source = str(source)
    output = re.findall(r'''(?:http://|www.)[^"]+''', source)
    
    if len(output) <= 3:
        max_range = len(output)
    else:
        max_range = 3
    for i in range(max_range):
        result_list.append(output[i])
        print(output[i])
    """

    # Option 3: Urlib mit parser
    """
    query = "weather%20Berlin"
    url = "https://www.bing.com/search?q=" + query
    values = {'q': 'python course'}
    data = urllib.parse.urlencode(values)
    data = data.encode('UTF-8')
    req = urllib.request.Request(url, data)
    resp = urllib.request.urlopen(req)
    repData = resp.read()

    soup = BeautifulSoup(repData, 'html.parser')
    soup.findAll('div')
    soup.find('span').get_text()
    print(soup)
    #print(soup.title.string)
    #print(soup.p.string)
    """

    # Option 4: requests
    """
    #payload = {'q': f'{query}'}
    payload = {"q": "Wetter Berlin"}
    r = requests.get("http://bing.com/search", params=payload)
    print(r.url)
    """

    # Option 5: urllib nochmal anders
    """
    query = "programming"
    url = urllib.urlunparse(("https", "www.bing.com", "/search", "", urllib.urlencode({"q": query}), ""))
    custom_user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0"
    req = Request(url, headers={"User-Agent": custom_user_agent})
    page = urlopen(req)
    # Further code I've left unmodified
    soup = BeautifulSoup(page.read())
    links = soup.findAll("a")
    for link in links:
    print(link["href"])
    """

    # Option 6: Google custom search api
    # Wie auch bei den oberen erhält man keine Daten, mit denen man arbeiten kann.
    # Nur ein kryptisches JSON
    query = "Wetter in Berlin"  # Zu test zwecken
    payload = build_payload(query)  # request parameter vorbereiten
    response = make_request(payload)  # Auf 100 Anfragen pro Tag begrenzt
    result_list.append(response['items'])
    for result in result_list:
        print(result)

    """
    # Hier wird aus der Query der filename gebaut und etwaige Sonderzeichen entfernt
    base_title = query.replace(' ', '_')
    string_clean_filename = clean_filename(base_title)

    # Zum Speichern der query requests, die können ggf. auch in die DB um die Anfragen gering zu halten
    # Muss nicht sein
    directory = './SearchResults'
    os.makedirs(directory, exist_ok=True)
    for result, index in enumerate(result_list):
        final_filename = string_clean_filename + "_" + index
        file_path = os.path.join(directory, final_filename)
        with open(file_path, 'w') as file:
            file.write(result)
    """

    # return result_list[:3]


def get_wikipedia_api_instance(topic):
    # Setze deinen eindeutigen Benutzeragenten
    user_agent = 'Python_research_Wikipedia (paul.mcwater@gmail.com)'

    # Lege eine Sprache fest in welcher der Artikel sein soll
    language = "en"

    # Erstelle die Wikipedia-API-Instanz mit angegebenen Benutzeragenten und in gewünschter Sprache
    wiki_wiki = wikipediaapi.Wikipedia(user_agent, language)
    page_py = wiki_wiki.page(topic)

    return page_py


def does_wikipedia_topic_exists(page_py, topic):
    exists = page_py.exists()
    if not exists:
        print(segregation, "D I E S E   S E I T E   E X I S T I E R T   N I C H T :", topic)
    return exists


def check_minimal_parameters(page_py):
    print(segregation, "Page - Title:", page_py.title)
    print(segregation, "Page - Summary:", page_py.summary)


def check_all_site_parameters(page_py):
    print(segregation, "Page - Text:", page_py.text)
    print(segregation, "Page - Categories:",
          page_py.categories)  # Sowas wie verwandte Themen, für weitere vertiefende Suchen
    print(segregation, "Page - Language:", page_py.language)  # Sprache in der der Wikipedia Artikel bereitgestellt wird
    print(segregation, "Page - Sections:", page_py.sections)  # gesamter Text, inklusive Auswertung der Gliederung
    print(segregation, "Page - Links:", page_py.links)  # Links zu anderen Themen in diesem Format:
    # name der Wikipedia Seite
    # 'Abstract Window Toolkit': Abstract Window Toolkit (id: ??, ns: 0)
    print(segregation, "Page - Namespace", page_py.namespace)


def get_wikipedia_summary(topic):
    # Option 1: wikipedia package
    """
    topic = 'google'
    summary = wikipedia.summary(topic)
    print(summary)
    """

    # Option 2: wikipediaapi package

    page_py = get_wikipedia_api_instance(topic)

    # Schaut, ob die Seite existiert
    does_wikipedia_topic_exists(page_py, topic)

    summary = page_py.summary
    # Für Testzwecke
    # check_minimal_parameters(page_py)

    # Gibt die andern Parameter als Ausgabe auf die Konsole, falls man testet
    # check_all_site_parameters(page_py, segregation)

    return json.dumps(summary)


def get_wikipedia_text(topic):
    page_py = get_wikipedia_api_instance(topic)

    # Schaut, ob die Seite existiert
    does_wikipedia_topic_exists(page_py, topic)

    text = page_py.text  # ACHTUNG! Ist sehr viel, vorsichtig mit umgehen

    # Für Testzwecke
    check_minimal_parameters(page_py)

    return json.dumps(text)


# Sucht für das übergebene Thema den expliziten Titel des Wikipedia Eintrags
def get_wikipedia_title(topic):
    page_py = get_wikipedia_api_instance(topic)

    return page_py.title


def get_topics_for_wiki_search(given_topics):
    existing_topics = []  # Themen aus der Konversation für die ein Wiki Artikel existiert

    for topic in given_topics:
        if does_wikipedia_topic_exists(get_wikipedia_api_instance(topic), topic):
            existing_topics.append(topic)

    return existing_topics


# Führt API Anfragen aus und ruft, falls nötig die Research-Funktionen auf
def get_gpt_response_with_research(topic):
    messages = [
        {"role": "user", "content": f"Give me a short summary about: {topic}"},
        # {"role": "user", "content": f"Give me all information about: {input_topic}"}
        # ACHTUNG! Hier kommt der gesamte Wikitext zurück, also sehr viele Token
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=messages,
        functions=functions
    )
    response_message = response.choices[0].message

    if response_message.get("function_call"):
        # Funktionen aufrufen
        function_name = response_message["function_call"]["name"]
        function_args = json.loads(response_message["function_call"]["arguments"])
        function_lookup = {
            "get_wikipedia_summary": get_wikipedia_summary,
            "get_wikipedia_text": get_wikipedia_text
        }
        function_to_call = function_lookup[function_name]
        function_response = function_to_call(**function_args)

        # Infos aus function call und response an GPT geben
        messages.append(response_message)  # extend conversation with assistant's reply
        messages.append(
            {
                "role": "function",
                "name": function_name,
                "content": function_response[0:10000],
            }
        )  # mit der response erweitern und zweite Anfrage stellen
        second_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=messages,
        )
        research_result_content = second_response.choices[0].message.content
        print(segregation, "GPT - Response for: ", topic, "\n\n", research_result_content)
        return research_result_content


# Führt für jedes Thema eine API Anfrage aus und sammelt die Responses
def get_response_for_every_topic(given_topics, participants):
    # Für Testzwecke
    test_topics = ["Mark Zuckerberg", "Java (programming language)", "Python French", "Python programming language",
                   "Facebook", "Simulation hypothesis"]

    # Für Themen aus Konversationen müsste hier "wikipedia" stehen, dazu oben "from X import wikipedia"
    topics_to_search = get_topics_for_wiki_search(given_topics)

    # Liste für Dictionaries
    research_result_list = []
    for topic in topics_to_search:
        # neues Dictionary erstellen
        result_entry = {}

        # GPT Response
        gpt_result = get_gpt_response_with_research(topic)

        # Daten zum Dictionary hinzufügen
        result_entry["topic"] = topic
        result_entry["content"] = gpt_result
        result_entry["knowing"] = participants

        # Dictionary zur Liste hinzufügen
        research_result_list.append(result_entry)

    return research_result_list


functions = [
    {
        "name": "get_wikipedia_summary",
        "description": "A function to search Wikipedia for a specific topic and get its summary",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "the topic to search wikipedia for"
                }
            },
            "required": ["topic"]
        }
    },
    {
        "name": "get_wikipedia_text",
        "description": "A function to search Wikipedia for a specific topic and get all information of this topic",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "the topic to search wikipedia for"
                }
            },
            "required": ["topic"]
        }
    },
    {
        "name": "research_web",
        "description": "A function, that search the web with a specific query to get a JSON with many information "
                       "about the best 10 results of that search",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A given query to search the web for"
                }
            }
        }
    }
]