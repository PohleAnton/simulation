import mariadb
import os
import yaml

with open('config.yml') as ymlfile:
    cfg = yaml.safe_load(ymlfile)

# Set the environment variables from the loaded configuration
for key, value in cfg.items():
    os.environ[key] = str(value)

# Access the variables
db_host = os.getenv('DB_HOST')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_db = os.getenv('DB_DB')


#stellt die verbindung zur Datenbank her:
conn = mariadb.connect(host=db_host, user=db_user, passwd=db_password, db=db_db)
#GPT schlägt vor, hier einen cursor zu benutzen...ich habe nicht so richtig muße, dass ich python zu recherchieren.
#es funktioniert
cur = conn.cursor()

#diese beiden personen sind eingefügt. ich lasse das mal exemplarisch hier stehen.
new_person_data_1 = {
    'name': 'Anton',
    'briggs': 'INTJ',
    'traits': 'cerebral, artsy, well read',
    'interests': 'Gaming, Science Fiction, Philosophy'
}
new_person_data_2 = {
    'name': 'Anna',
    'briggs': 'ENTP',
    'traits': 'smart, shy, nerdy',
    'interests': 'Lord of the Rings, Coding, Linguistics'
}


insert_person_query = """
INSERT INTO person (name, briggs, traits, interests)
VALUES (%(name)s, %(briggs)s, %(traits)s,%(interests)s);
"""

try:

    cur.execute(insert_person_query, new_person_data_1)
    cur.execute(insert_person_query, new_person_data_2)
    # Commit the transaction
    conn.commit()

    print("Data inserted successfully.")
except mariadb.Error as e:
    print(f"Error: {e}")
finally:
    # Close the cursor and connection
    cur.close()
    conn.close()

#eine select * from person abfrage ergibt folgendes:

#(6, 'Anton', 'INTJ', 'cerebral, artsy, well read', 'Gaming, Science Fiction, Philosophy')
#(7, 'Anna', 'ENTP', 'smart, shy, nerdy', 'Lord of the Rings, Coding, Linguistics')

#die primärschlüssel zählen einfach hoch. 1-5 habe ich wieder gelöschht, weil mir sachen gefehlt haben
