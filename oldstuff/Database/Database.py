import mariadb
import os
from oldstuff.Database.Person import Person
import yaml

print(os.getenv('db_db'))

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


class Database:
    def __init__(self):
        self.db_host = os.getenv('DB_HOST')
        self.db_user = os.getenv('DB_USER')
        self.db_password = os.getenv('DB_PASSWORD')
        self.db_db = os.getenv('DB_DB')
        try:
            self.connection = mariadb.connect(host=self.db_host, user=self.db_user, passwd=self.db_password,
                                              db=self.db_db)
            self.cursor = self.connection.cursor()
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB: {e}")
            # handle error or raise

    def __del__(self):
        self.connection.close()

    def get_persons(self):

        try:
            self.cursor.execute("SELECT * FROM person")
            rows = self.cursor.fetchall()
            result_str = ""
            for row in rows:
                result_str += " ".join(str(item) for item in row) + "\n"
            return result_str
        except mariadb.Error as e:
            print(f"Error fetching data: {e}")
            # handle error or return an appropriate response

    def get_person_by_pid(self, pid):
        try:
            query = "SELECT * FROM person WHERE pid = %s"
            self.cursor.execute(query, (pid,))
            row = self.cursor.fetchone()
            print(row[1])
            if row:
                print(row)
                return Person(name=row[1], myers_briggs_type=row[2], personality_traits=row[3], interests=row[4],
                              pk=row[0])
            else:
                return None
        except mariadb.Error as e:
            print(f"Error fetching data: {e}")
            # handle error or return an appropriate response

    def get_thoughts(self, from_pid, about_pid):

        try:
            self.cursor.execute("SELECT thoughts FROM thoughts_on_person where from_pid=%s and about_pid=%s", (from_pid, about_pid))
            rows = self.cursor.fetchall()
            result_str = ""
            for row in rows:
                result_str += " ".join(str(item) for item in row) + "\n"
            return result_str
        except mariadb.Error as e:
            print(f"Error fetching data: {e}")

    def insert_thoughts(self, from_pid, about_pid, thoughts):

        query = "INSERT INTO thoughts_on_person (thoughts, from_pid, about_pid) VALUES (%s, %s, %s)"
        data = (thoughts, from_pid, about_pid)

        try:
            self.cursor.execute(query, data)
            self.connection.commit()
            print(thoughts)
            print(f"Data inserted successfully: {from_pid}, {about_pid}, '{thoughts}'")
            print(thoughts)
        except mariadb.Error as err:
            print(f"Error: {err}")

    def update_thoughts(self, from_pid, about_pid, thoughts):
        # SQL query to update the data
        query = "UPDATE thoughts_on_person SET thoughts = %s WHERE from_pid = %s AND about_pid = %s"

        # Data tuple
        data = (thoughts, from_pid, about_pid)

        try:
            # Execute the query
            self.cursor.execute(query, data)

            # Commit the changes
            self.connection.commit()

            if self.cursor.rowcount > 0:
                print(f"Data updated successfully for from_pid: {from_pid}, about_pid: {about_pid}")
            else:
                print("No record found to update.")
        except mariadb.Error as err:
            print(f"Error: {err}")


if __name__ == "__main__":
    db1 = Database()

    # Example usage
    print(db1.get_persons())
    print(db1.get_person_by_pid(7))
    tel = db1.get_thoughts(6,7)
    print(len(tel))

#mysql - u root - p
#CREATE USER 'new_username'@'%' IDENTIFIED BY 'new_password';
#GRANT ALL PRIVILEGES ON * . * TO 'new_username'@'%';
