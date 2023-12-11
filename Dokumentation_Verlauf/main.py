"""
Auch zu Beginn entstanden. Anfänglicher Versuch, die ursprüngliche Idee mit den vertrauten, deterministischen
Mitteln umzusetzen- kaum Prompt-, eher Conversationenginiiering. Keine Vektordb
"""


import copy
import yaml
import openai
import random

config = yaml.safe_load(open("../config.yml"))
openai.api_key = config['KEYS']['openai']

# wird als map formatiert, damit den einzelnen objecten informationen hinzugefügt werden können --> so können die agenten
# sich an den inhalt vergangener konversationen erinnern
book_a = {'title': 'The Emperor\'s New Mind', 'Self': [], 'Used': []}
book_b = {'title': 'Are you living in a computer simulation?', 'Self': [], 'Used': []}


class Agent:
    def __init__(self, name, favorite_tv_show, favorite_video_game):
        self.name = name
        self.favorite_tv_shows = favorite_tv_show
        self.favorite_video_games = favorite_video_game
        # ich weiß noch nicht...ich bin irgendwie überfordert. ich nehme hier mal eine liste von büchern, die der
        # agent gelesen hat. meine idee ist, dass man so die verbreitung von ideen abbilden kann und ggf. ähnliche bullet-
        # point hat...
        self.books = self.generate_favorite_books()
        # dies wird stand jetzt zu testzwecken in zeile 62 überschrieben, kann aber langfristig so bleiben
        self.fav_book = random.choice([book_a, book_b])
        self.agents_met = []
        self.trust_agent1 = 0
        self.trust_agent2 = 0

        # Call the method to generate favorite books.

    @staticmethod
    def generate_favorite_books():
        book_options = [
            {'title': 'Elemente und Ursprünge totaler Herrschaft', 'Self': []},
            {'title': 'Understanding Media', 'Self': []},
            {'title': 'The Age of Surveillance Capitalism', 'Self': []},
            {'title': 'Das Kapital', 'Self': []},
            {'title': 'Computing machinery and intelligence', 'Self': []}
        ]
        non_specific_books = [book for book in book_options if
                              book not in [book_a, book_b]]
        selected_books = random.sample(non_specific_books, 2)  # Sample 2 books from non_specific_books.
        # sollte später zufällig sein.
        # selected_books.append(random.choice([book_a, book_b]))

        # ACHTUNG!!!
        # zum testen wird immer das selbe buch genutzt
        # SONST:
        # selected_books.append(random.choice([book_a, book_b]))
        return selected_books


agent1 = Agent("Anton", ["South Park", "The Expanse"], "Baldurs Gate 3")
agent2 = Agent("Anna", ["The Last of Us", "Mr Robot"], "The Witcher 3")

# zum testen wird das gleiche buch vergeben:
agent1.fav_book = book_a
agent2.fav_book = book_a

# schließlich das lieblingsbuch auch in die gelesenen bücher
agent1.books.append(agent1.fav_book)
agent2.books.append(agent2.fav_book)

print(agent2.fav_book)

if agent2.name not in agent1.agents_met:
    agent1.agents_met.append(agent2.name)
    agent2.agents_met.append(agent1.name)
    # python geht merkwürdig mit attributen um: wenn im folgenden code-block agent1.favorite_books geändert wird, wird
    # dabei auch agent2.favorite_books geändert - hat wohl irgendwas mit speicherreferenz zu tun...hier wird eine unabhän-
    # gige kopie erstellt, welche später das attribut überschreibt
    agent1_books = copy.deepcopy(agent1.books)
    agent2_books = copy.deepcopy(agent2.books)
    if agent1.fav_book['title'] == agent2.fav_book['title']:
        f = open('../oldstuff/prompt_Templates/first_meeting/sameBook/1st_conversation.txt')
        content = f.read()
        agent1_prompt = content.replace("<Name>", agent1.name).replace("<Random_Book>", agent1.fav_book['title'])
        f.seek(0)
        agent2_prompt = content.replace("<Name>", agent2.name).replace("<Random_Book>", agent2.fav_book['title'])
        f.close()
        f = open('../oldstuff/prompt_Templates/first_meeting/sameBook/1st_intro.txt')
        agent1_role = f.read()
        agent1_prompt = agent1_prompt.replace("<Dialog_Role>", agent1_role)
        f.close()
        f = open('../oldstuff/prompt_Templates/first_meeting/sameBook/1st_answer.txt')
        agent2_role = f.read()
        agent2_prompt = agent2_prompt.replace("<Dialog_Role>", agent2_role)

        intro = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": agent1_prompt}
            ]
        )

        print('intro:  ' + intro.choices[0].message.content)
        answer = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": intro.choices[0].message.content + agent2_prompt}
            ]
        )

        print('answer: ' + answer.choices[0].message.content)

        # falls das gleiche buch genannt wird, fasst der 2 agent zusammen, was er/sie an dem buch mag. die passiert in der
        # strutkur einer python list
        bulletlist = [point.lstrip('- ') for point in answer.choices[0].message.content.split('\n')[1:]]
        if '' in bulletlist:
            bulletlist.remove('')
        # kreiert eine map mit dem namen sowie den bulletpoints. so kann sich der agent daran erinnern, was der gesprächs-
        # partner an dem buch mag und ggf. darauf zurückkommen. ich halte es außerdem für denkbar, dass dies später irgendwie
        # für die überzeugungsarbeit genutzt werden kann
        to_add = {agent2.name: bulletlist}

        for book in agent1_books:
            # nun wird die just erstellte map der liste von agent1 hinzugefügt - so weiß agent1 a) dass er / sie mit agent2
            # über dieses buch gesprochen hat und b)
            # was agent 2 daran mag. dieses wissen kann für folgegespräche oder ggf. für die konversation mit anderen genutzt
            # werden
            if book['title'] == agent2.fav_book['title']:
                book.update(to_add)

        for book in agent2_books:
            if book['title'] == agent1.fav_book['title']:
                for string in bulletlist:
                    book['Self'].append(string)
        for string in bulletlist:
            agent2.fav_book['Self'].append(string)

        agent1.books = agent1_books
        agent2.books = agent2_books

        # print(agent1.books)
        # print(agent2.books)
        # print(agent2.fav_book)

    if agent1.fav_book['title'] != agent2.fav_book['title']:
        g = open('../oldstuff/prompt_Templates/first_meeting/sameBook/1st_conversation.txt')
        content = g.read()
        agent1_prompt = content.replace("<Name>", agent1.name).replace("<Random_Book>", agent1.fav_book['title'])
        g.seek(0)
        agent2_prompt = content.replace("<Name>", agent2.name).replace("<Random_Book>", agent2.fav_book['title'])

        g.close()
        g = open('../oldstuff/prompt_Templates/first_meeting/sameBook/1st_intro.txt')
        agent1_role = g.read()
        agent1_prompt = agent1_prompt.replace("<Dialog_Role>", agent1_role)
        g.close()
        g = open('../oldstuff/prompt_Templates/first_meeting/diffBook/1st_answer.txt')
        agent2_role = g.read()
        agent2_prompt = agent2_prompt.replace("<Dialog_Role>", agent2_role)
        g.close()
        g = open('../oldstuff/prompt_Templates/first_meeting/diffBook/give_bulletpoints.txt')
        agent1_reply = g.read().replace("<Random_Book>", agent1.fav_book['title'])

        intro = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": agent1_prompt}
            ]
        )

        print('intro:  ' + intro.choices[0].message.content)
        answer = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": intro.choices[0].message.content + agent2_prompt}
            ]
        )

        print('answer: ' + answer.choices[0].message.content)


        reply = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": agent1_reply}
            ]
        )

        print('reply:  ' + reply.choices[0].message.content)


        # falls das gleiche buch genannt wird, fasst der 2 agent zusammen, was er/sie an dem buch mag. die passiert in der
        # strutkur einer python list
        bulletlist = [point.lstrip('- ') for point in reply.choices[0].message.content.split('\n')[1:]]
        if '' in bulletlist:
            bulletlist.remove('')
        # kreiert eine map mit dem namen sowie den bulletpoints. so kann sich der agent daran erinnern, was der gesprächs-
        # partner an dem buch mag und ggf. darauf zurückkommen. ich halte es außerdem für denkbar, dass dies später irgendwie
        # für die überzeugungsarbeit genutzt werden kann
        to_add = {agent1.name: bulletlist}
        if agent1.fav_book in agent2_books:
            for book in agent2_books:
                # nun wird die just erstellte map der liste von agent1 hinzugefügt - so weiß agent1 a) dass er / sie mit agent2
                # über dieses buch gesprochen hat und b)
                # was agent 2 daran mag. dieses wissen kann für folgegespräche oder ggf. für die konversation mit anderen genutzt
                # werden
                if book['title'] == agent1.fav_book['title']:
                    book.update(to_add)
            else:
                agent2_books.append(agent1.fav_book)
                for book in agent2_books:
                    if book['title'] == agent1.fav_book['title']:
                        book.update(to_add)

        for book in agent1_books:
            if book['title'] == agent1.fav_book['title']:
                for string in bulletlist:
                    book['Self'].append(string)
        for string in bulletlist:
            agent1.fav_book['Self'].append(string)

        agent1.books = agent1_books
        agent2.books = agent2_books

        print(agent1.books)
        print(agent2.books)
        print(agent1.fav_book)

if agent1.name in agent2.agents_met:

    if agent1.fav_book == agent2.fav_book:
        f = open('../oldstuff/prompt_Templates/meeting/sameBook/greeting.txt')
        content = f.read()
        agent1_prompt = content.replace("<Their_Name>", agent2.name).replace("<Dialog_Role>", agent1_role)
        f.close()

        intro = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": agent1_prompt}
            ]
        )

        #wieder: erstelle eine liste aus den genannten bulletpoints
        bulletlist = [point.lstrip('- ') for point in intro.choices[0].message.content.split('\n')[1:]]
        if '' in bulletlist:
            bulletlist.remove('')
        #füge diese den bereits bekannten hinzu
        for string in bulletlist:
            agent1.fav_book['Self'].append(string)
        #falls es dadurch zu doppelungen kam, entferne duplikate
        agent1.fav_book['Self'] = list(set(agent1.fav_book['Self']))

        for item in agent1.fav_book['Self']:
            if item in agent2.fav_book['Self'] and item not in agent2.fav_book['Used']:
                #agent1.fav_book['Used'].append(item)
                agent2.fav_book['Used'].append(item)
                agent2.fav_book['Used'] = list(set(agent2.fav_book['Used']))
                f = open('../oldstuff/prompt_Templates/meeting/sameBook/good_answer.txt')
                contents = f.read()
                f.close()

                reply = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "user", "content": contents}
                    ]
                )

                agent2.trust_agent1 += 1
                break

    if agent1.fav_book != agent2.fav_book:
        if [agent2.name] in agent2.books[agent2.fav_book['title']]:
            f = open('../oldstuff/prompt_Templates/meeting/diffBook/greeting.txt')
            content = f.read()
            agent1_prompt = (content.replace("<TheirName>", agent2.name).replace("<TheirBook>", agent2.fav_book)
                             .replace("<YourBook>", agent1.fav_book))
            f.close()

        else:
            ##reverse agents roles in dialog
            intro = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": agent1_prompt}
                ]
            )

    print(agent2.trust_agent1)
    print(agent2.fav_book['Used'])



