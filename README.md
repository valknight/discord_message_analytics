# Discord Experiments
*A bot which allows you to run ethical experiments using Discord data*

**Note: This bot requires *express* user consent. Modifying this bot to remove these checking features would result in you violating Discord TOS.**

## Requirements
 - Python 3.5 or higher
 - MySQL/MariaDB server

## Setup

1. Create a schema inside MySQL/MariaDB. You can name it whatever you want, just remember what you call it.

2. Go to discord developers, create an application, then add a bot user, and make note of the token. Also add this bot user to whatever servers you want to - this isn't documented, as you can find guides to do this everywhere

3. Copy `config.json.example` to `config.json`, populating the fields with what you require. For database, insert the schema you created.

4. Run `python3 setup.py` - this will populate your chosen schema with our database setup, and install all of our requirements

5. Run `python3 bot.py` - you're all ready to go!

