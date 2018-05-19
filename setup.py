import mysql.connector
import json
import os

discordpy_command = "python3 -m pip install -U https://github.com/Rapptz/discord.py/archive/rewrite.zip#egg=discord.py"
requirements = "python3 -m pip install -r requirements.txt"
# Load config files
config_f = open("config.json")
config = json.load(config_f)

# Setup discord.py + requirements
print("Installing discord.py...")
os.system(discordpy_command)
print("\nInstalling other requirements...")
os.system(requirements)

# Database
print("\nSetting up database")

print("Connecting to DB...")
cnx = mysql.connector.connect(**config['mysql'])
print("Connected.")
cursor = cnx.cursor()

users = """
CREATE TABLE `users` (
  `user_id` varchar(64) CHARACTER SET utf8 NOT NULL,
  `username` varchar(64) CHARACTER SET utf8 NOT NULL,
  `opted_in` bit(1) NOT NULL DEFAULT b'0',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci
"""

messages = """
CREATE TABLE `messages` (
  `id` varchar(64) NOT NULL,
  `channel` varchar(64) NOT NULL,
  `time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8
"""

markovs = """
CREATE TABLE `markovs` (
  `user` varchar(64) NOT NULL,
  `markov_json` longtext,
  PRIMARY KEY (`user`),
  CONSTRAINT `FK_markovs_users` FOREIGN KEY (`user`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8
"""

blocklist = """
CREATE TABLE `blocklists` (
  `user_id` varchar(64) NOT NULL,
  `blocklist` longtext NOT NULL,
  PRIMARY KEY (`user_id`),
  CONSTRAINT `user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8
"""

def make_table(query):
  try:
    cursor.execute(query)
  except mysql.connector.errors.ProgrammingError:
    print("Already exists")

print("\nCreating users table")
make_table(users)
print("\nCreating messages table")
make_table(messages)
print("\nCreating markovs table")
make_table(markovs)
print("\nCreating blocklist table")
make_table(blocklist)
print("\nDone!")
