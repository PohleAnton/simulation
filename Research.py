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

config = yaml.safe_load(open("config.yml"))
openai.api_key = config.get('KEYS', {}).get('openai')
google_api_key = config.get('KEYS', {}).get('google')
search_engine_id = config.get('KEYS', {}).get('search_engine_id')


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


def research_web(query):  # kann für die google APi dann erweiter werden falls nötig
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
    query = "Wetter in Berlin" # Zu test zwecken
    payload = build_payload(query)  #request parameter vorbereiten
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


functions = [
    {
        "name": "research_web",
        "description": "A function, that search the web for a specific topic",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A given query to search the web for"
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

api_request = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-1106",
    messages=[
        {"role": "user", "content": user_input}
    ],
    functions=functions,
    function_call={'name': 'research_web', 'arguments': {'query': topic}},
)

content = api_request["choices"][0]["message"]["function_call"]["arguments"]["result"]
data = json.loads(content)
print(data)
