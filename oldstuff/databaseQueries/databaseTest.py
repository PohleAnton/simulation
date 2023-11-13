import mariadb
import os
import yaml

with open('config.yml', 'r') as ymlfile:
    cfg = yaml.safe_load(ymlfile)

# Set the environment variables from the loaded configuration
for key, value in cfg.items():
    os.environ[key] = str(value)

# Access the variables
db_host = os.getenv('DB_HOST')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_db = os.getenv('DB_DB')



conn = mariadb.connect(host=db_host, user=db_user, passwd=db_password, db=db_db)
cur = conn.cursor()

#steht hier zum testen
cur.execute("ALTER TABLE person CHANGE briggs myers_briggs_type CHAR(4);")
cur.execute("ALTER TABLE person CHANGE traits personality_traits  VARCHAR(30);")
#cur.execute("DELETE FROM person WHERE pid = 5")
#WICHTIG!!!
conn.commit()
cur.execute("SELECT * FROM person")
for response in cur:
    print(response)
cur.close()
conn.close()




