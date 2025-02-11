import json
import random
import re

import openai
import requests
# import wikipedia
import wikipediaapi
import yaml

__author__ = "Sebastian Koch"

config = yaml.safe_load(open("config.yml"))
openai.api_key = config.get('KEYS', {}).get('openai')
google_api_key = config.get('KEYS', {}).get('google')
search_engine_id = config.get('KEYS', {}).get('search_engine_id')
segregation_str = ("\n\n<<<<< ----- >>>>>       <<<<< ----- >>>>>       <<<<< ----- >>>>>       <<<<< ----- >>>>>\n\n")


# https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list?hl=de
def build_payload(query, num, start=1):
    # kann mit date_restict erweitert werden, schränkt Zeit ein
    if num > 10:
        num = 10
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


def research_web(topic, num):
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
    query = topic + " site:en.wikipedia.org"
    payload = build_payload(query, num)  # request parameter vorbereiten
    response = make_request(payload)  # Auf 100 Anfragen pro Tag begrenzt
    result_list = response['items']
    # print(segregation_str, f"Web Search - {query} :\n")
    # for result in result_list:
    #     print_json_in_pretty(result)

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

    return result_list


def print_json_in_pretty(given_json):
    print(json.dumps(given_json, ensure_ascii=False, indent=4))


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
        print(segregation_str, "There is no Wikipedia article about:", topic)
    else:
        print(segregation_str, "There is a Wikipedia article about:", topic)
    return exists


def check_minimal_parameters(page_py):
    print(segregation_str, "Page - Title:", page_py.title)
    print(segregation_str, "Page - Summary:", page_py.summary)


def check_all_site_parameters(page_py):
    print(segregation_str, "Page - Text:", page_py.text)
    print(segregation_str, "Page - Categories:",
          page_py.categories)  # Sowas wie verwandte Themen, für weitere vertiefende Suchen
    print(segregation_str, "Page - Language:",
          page_py.language)  # Sprache in der der Wikipedia Artikel bereitgestellt wird
    print(segregation_str, "Page - Sections:", page_py.sections)  # gesamter Text, inklusive Auswertung der Gliederung
    print(segregation_str, "Page - Links:", page_py.links)  # Links zu anderen Themen in diesem Format:
    # name der Wikipedia Seite
    # 'Abstract Window Toolkit': Abstract Window Toolkit (id: ??, ns: 0)
    print(segregation_str, "Page - Namespace", page_py.namespace)


def get_wikipedia_summary(topic):
    # Option 1: wikipedia package
    """
    topic = 'google'
    summary = wikipedia.summary(topic)
    print(summary)
    """

    # Option 2: wikipediaapi package
    page_py = get_wikipedia_api_instance(topic)
    summary = page_py.summary
    # print(segregation_str, f"Wiki-API Response: {topic}\n\n{summary}")
    # Für Testzwecke
    # check_minimal_parameters(page_py)

    # Gibt die andern Parameter als Ausgabe auf die Konsole, falls man testet
    # check_all_site_parameters(page_py, segregation)

    return summary


def get_wikipedia_text(topic):
    page_py = get_wikipedia_api_instance(topic)

    # Schaut, ob die Seite existiert
    does_wikipedia_topic_exists(page_py, topic)

    text = page_py.text  # ACHTUNG! Ist sehr viel, vorsichtig mit umgehen

    # Für Testzwecke
    check_minimal_parameters(page_py)

    return json.dumps(text, ensure_ascii=False,)


# Sucht für das übergebene Thema den expliziten Titel des Wikipedia Eintrags
def get_wikipedia_title(topic):
    page_py = get_wikipedia_api_instance(topic)

    return page_py.title


def try_wiki_search(given_topic, num=10):  # hier sollte es bei 10 Webseiten bleiben,
    # um eine zufällige Auswahl und dadurch unterschiedliche Ergebnisse zu gewährleisten
    """
    research_result = None
    site_exists = does_wikipedia_topic_exists(get_wikipedia_api_instance(given_topic), given_topic)
    if site_exists:
        research_result = get_gpt_response_with_research(given_topic)

    return research_result
    """
    google_result_list = None
    try:
        google_result_list = research_web(given_topic, num)
    except Exception as e:  # TODO vllt passt hier ne andere Exception besser
        print(segregation_str, "ACHTUNG!!! Eine Exception beim Aufruf der Google API ist aufgetreten. "
                               f"Exception: {e}")

    if google_result_list is not None:
        extracted_titles_list = extract_titles_of_google_research(google_result_list)

        count_selector = 3  # Zahl der zufälligen Ergebnisse die ausgewählt werden sollen
        if len(extracted_titles_list) < count_selector:
            used_titles_list = extracted_titles_list  # wenn kleiner als gewählte Zahl, wird ganze Liste ausgewählt
        else:
            used_titles_list = random.sample(extracted_titles_list, count_selector)  # sonst diese Zahl aus der Liste

        summary_list = []
        try:
            for title in used_titles_list:
                summary_list.append(get_wikipedia_summary(title))  # nur für Testzwecke
        except Exception as e:
            print(segregation_str, "ACHTUNG!!! Eine Exception beim Aufruf der Wikipedia API ist aufgetreten. "
                                   f"Exception: {e}")

        str_for_gpt = "\n".join(summary_list)
        gpt_response = get_gpt_response(f"Provide a detailed overview of the topic {given_topic}, "
                                        f"focus on details and explanations "
                                        f"utilizing and combine the following information: {str_for_gpt}")
    else:
        message_content = (f"Provide a detailed overview of the topic {given_topic}, "
                           f"focus on details and explanations")
        try:
            if does_wikipedia_topic_exists(get_wikipedia_api_instance(given_topic), given_topic):
                summary = get_wikipedia_summary(given_topic)
                message_content += f" utilizing and combine the following information: {summary}"
        except Exception as e:
            print(segregation_str, "ACHTUNG!!! Eine Exception beim Aufruf der Wikipedia API ist aufgetreten. "
                                   f"Exception: {e}")
        gpt_response = get_gpt_response(message_content)
    content_str = get_response_content(gpt_response)
    cleaned_string = content_str.replace("\n\n", "\n")
    # print(segregation_str, f"Content of GPT Response:\n{cleaned_string}")

    return cleaned_string


def organize_research(given_topic, num=10):  # hier sollte es bei 10 Webseiten bleiben,
    # um eine zufällige Auswahl und dadurch unterschiedliche Ergebnisse zu gewährleisten
    google_result_list = None
    try:
        google_result_list = research_web(given_topic, num)
    except Exception as e:  # TODO vllt passt hier ne andere Exception besser
        print(segregation_str, "ACHTUNG!!! Eine Exception beim Aufruf der Google API ist aufgetreten. "
                               f"Exception: {e}")

    if google_result_list is not None:
        extracted_titles_list = extract_titles_of_google_research(google_result_list)

        count_selector = 3  # Zahl der zufälligen Ergebnisse die ausgewählt werden sollen
        if len(extracted_titles_list) < count_selector:
            used_titles_list = extracted_titles_list  # wenn kleiner als gewählte Zahl, wird ganze Liste ausgewählt
        else:
            used_titles_list = random.sample(extracted_titles_list, count_selector)  # sonst diese Zahl aus der Liste

        #print(used_titles_list)
        summary_list = []
        title_summary_list = []

        try:
            for title in used_titles_list:
                summary = get_wikipedia_summary(title)
                summary_list.append(summary)
                title_summary_list.append({"title": title, "summary": summary})
        except Exception as e:
            print(segregation_str, "ACHTUNG!!! Eine Exception beim Aufruf der Wikipedia API ist aufgetreten. "
                                   f"Exception: {e}")

        output_json = json.dumps(title_summary_list, ensure_ascii=False, indent=2)
        # print(output_json)
        str_for_gpt = "\n".join(summary_list)
        gpt_response = get_gpt_response(f"Provide a detailed overview of the topic {given_topic}, "
                                        f"concentrate your focus on details and explanations "
                                        f"utilizing and combine the following information: {str_for_gpt}")
    else:
        message_content = (f"Provide a detailed overview of the topic {given_topic}, "
                           f"focus on details and explanations")
        title_summary_list = []
        try:
            if does_wikipedia_topic_exists(get_wikipedia_api_instance(given_topic), given_topic):
                summary = get_wikipedia_summary(given_topic)
                message_content += f" utilizing and combine the following information: {summary}"
                title_summary_list.append({"title": given_topic, "summary": summary})
        except Exception as e:
            print(segregation_str, "ACHTUNG!!! Eine Exception beim Aufruf der Wikipedia API ist aufgetreten. "
                                   f"Exception: {e}")
        gpt_response = get_gpt_response(message_content)

    content_str = get_response_content(gpt_response)
    cleaned_string = content_str.replace("\n\n", "\n")
    # print(segregation_str, f"Content of GPT Response:\n{cleaned_string}")
    return cleaned_string, title_summary_list


def extract_titles_of_google_research(google_result_list):
    # Extrahiere den "title" jedes JSON-Objekts, der "- Wikipedia" enthält
    extracted_titles = [item["title"].replace(" - Wikipedia", "")
                        if "- Wikipedia" in item.get("title", "")
                        else item.get("title", "") for item in google_result_list]

    # Gib die extrahierten "title" aus
    #for title in extracted_titles:
        #print(title)

    return extracted_titles


def get_gpt_response(content):  # ohne functions!
    # print(segregation_str, f"GPT - message content:\n{content}")
    messages = [
        {"role": "user", "content": content}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=messages
    )
    return response


def get_response_content(given_response):
    return given_response.choices[0].message.content


# Führt API Anfragen aus und ruft, falls nötig die Research-Funktionen auf
def get_gpt_response_with_research(topic):
    messages = [
        {"role": "user", "content": f"Give me a short summary of the wikipedia article about: {topic}"},
        # {"role": "user", "content": f"Give me all information of the wikipeda article about: {input_topic}"}
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
        #print(segregation_str, "GPT - Response for: ", topic, "\n\n", research_result_content)
        return research_result_content


"""
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
"""

functions = [
    {
        "name": "get_wikipedia_summary",
        "description": "A function to get a summary of a Wikipedia article about a topic",
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
