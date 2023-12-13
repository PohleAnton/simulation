import os
import random

import openai
import yaml

from NetworkApproach import Research2

# from NetworkApproach.copy import get_profile, fill_profile_schemes_for_participants

__author__ = "Sebastian Koch"
openai.api_key = yaml.safe_load(open("config.yml")).get('KEYS', {}).get('openai')


def get_gpt_response_with_function(content, functions):
    # print(Research.segregation_str, "GPT - prompt :", content)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "user", "content": content}
        ],
        functions=functions
    )
    return response


def get_gpt_response(content):  # ohne functions!
    print(segregation_str, f"GPT - prompt :\n{content}")
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


def get_file_name(name):
    modified_name = name.replace(" ", "_")
    file_name = f"{modified_name}.txt"
    return file_name


def get_name_from_filename(file_name):
    modified_name = file_name.replace("_", " ")
    extracted_name = modified_name.replace(".txt", "")
    return extracted_name


def does_file_exists(file_path):
    exists = os.path.isfile(file_path)
    return exists


def read_from_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    return content


def write_in_file(file_path, content, mode):
    with open(file_path, mode) as file:
        file.write(content)


def generate_belief(participant, topic):
    prompt = f"Generate a belief for topic {topic} that {participant} could have!"
    response = get_gpt_response(prompt)
    res_content = get_response_content(response)
    print(segregation_str, f"Belief of {participant}:\n{res_content}")
    return res_content


def formulate_argument(participant, belief):
    strategy_name, strategy_content = choose_strategy()
    knowledge = ""  # TODO Wissen müsste irgendwie aus Chroma kommen
    prompt = (f"Given this persuasion strategy {strategy_name} ({strategy_content}) and this knowledge {knowledge}. "
              f"Formulate an argument for this belief {belief}!")
    response = get_gpt_response(prompt)
    res_content = get_response_content(response)
    print(segregation_str, f"Argument of {participant}:\n{res_content}")
    return res_content


def choose_strategy():
    file_list = [f for f in os.listdir(strategy_directory) if f.endswith('.txt')]
    if not file_list:
        print("Keine TXT-Dateien im angegebenen Ordner gefunden.")
        return None
    else:
        # Zufällige Auswahl einer Datei aus der Liste
        random_file = random.choice(file_list)
        file_path = os.path.join(strategy_directory, random_file)
        file_name = os.path.basename(random_file)
        strategy_name = get_name_from_filename(file_name)
        file_content = read_from_file(file_path)
        return strategy_name, file_content


def convincing_conversation(given_participants, given_beliefs, given_arguments):
    part_bel_arg_list = []
    # part_profile_list = []
    for i in range(len(given_participants)):
        part_bel_arg_list.append(f"{given_participants[i]} beliefs {given_beliefs[i]} "
                                 f"and uses this argument to convince the others: {given_arguments[i]}")
        # part_profile_list.append(get_profile(given_participants[i]))
        # TODO Profile müssten generiert/ abgerufen werden
    # profile_str = " ".join(part_profile_list)
    profile_str = ", ".join(given_participants)  # zu ersetzen
    convincing_str = "\n6. Convincing Strategy: " + " ".join(part_bel_arg_list)
    success_str = "\n7. One of the individuals needs to be successful with his/her argument!"
    gpt_prompt = pre_prompt + profile_str + convincing_str + success_str
    gpt_response = get_gpt_response(gpt_prompt)
    response_content = get_response_content(gpt_response)
    print(segregation_str, f"Conversation:\n{response_content}")
    return response_content


# Konstanten
segregation_str = Research2.segregation_str
profile_directory = "NetworkApproach/txtFiles/Profiles"
strategy_directory = "NetworkApproach/txtFiles/ConvincingStrategies"
profile_scheme = read_from_file("FocusedConversationApproach/txtFiles/scheme.txt")
initial_participants = ["Elon Musk", "Karl Marx", "Peter Thiel"]
pre_prompt = (
    "Write a conversation with the following setup: "
    "1. Topics: At least two subjects in their interest. If the simulation hypothesis comes up, focus on that"
    "2. Informal, emotional conversation between people who’ve known each other for a long time and don’t like each other "
    "very much. They enjoy intense intellectual arguments and do not hold back.Deep Talk "
    "3. Long and detailed conversation. "
    "4. Setting: New Year‘s Eve Party. All might have had a few drinks already "
    "5. Involved Individuals: "
)
test_topic = "Simulation Hypothesis"

# Programmablauf

initial_beliefs = []
for one_participant in initial_participants:
    initial_beliefs.append(generate_belief(one_participant, test_topic))

initial_arguments = []
for i in range(len(initial_participants)):
    initial_arguments.append(formulate_argument(initial_participants[i], initial_beliefs[i]))

conversation = convincing_conversation(initial_participants, initial_beliefs, initial_arguments)
