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
cursor = conn.cursor()

# Define SQL statements for creating tables


create_experiment_table = """
CREATE TABLE experiment (
    eid        INT AUTO_INCREMENT NOT NULL,
    simulation CHAR(1),
    PRIMARY KEY (eid)
);
"""

create_person_table = """
CREATE TABLE person (
    pid    INT AUTO_INCREMENT NOT NULL,
    name   VARCHAR(20),
    interests VARCHAR(50)
    myers_briggs_type CHAR(4),
    personality_traits VARCHAR(30),
    PRIMARY KEY (pid)
);
"""

create_thoughts_on_person_table = """
CREATE TABLE thoughts_on_person (
    thoughts  VARCHAR(50),
    from_pid  INT NOT NULL,
    about_pid INT NOT NULL,
    PRIMARY KEY (from_pid, about_pid),
    FOREIGN KEY (about_pid) REFERENCES person(pid),
    FOREIGN KEY (from_pid) REFERENCES person(pid)
);
"""

cursor.execute(create_experiment_table)
cursor.execute(create_person_table)
cursor.execute(create_thoughts_on_person_table)

# needs to be done after the other tables have been created...

create_conversation_table = """
CREATE TABLE conversation (
    cid            INT AUTO_INCREMENT NOT NULL,
    setting        VARCHAR(50),
    test           LONGTEXT,
    experiment_eid INT,
    PRIMARY KEY (cid),
    FOREIGN KEY (experiment_eid) REFERENCES experiment(eid)
);
"""

cursor.execute(create_conversation_table)

create_person_conversation_table = """
CREATE TABLE person_conversation (
    conversation_cid INT NOT NULL,
    person_pid       INT NOT NULL,
    PRIMARY KEY (conversation_cid, person_pid),
    FOREIGN KEY (conversation_cid) REFERENCES conversation(cid),
    FOREIGN KEY (person_pid) REFERENCES person(pid)
);
"""
cursor.execute(create_person_conversation_table)

# Commit the changes and close the connection
conn.commit()
conn.close()
