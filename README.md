#Discord Experiments
*A bot which allows you to run ethical experiments using Discord data*

**Note: This bot requires *express* user consent. Modifying this bot to remove these checking features would result in you violating Discord TOS. Don't do it.**

##Setup

1. Create a schema inside MySQL. You can name it whatever you want, just remember what you call it.

2. Copy `config.json.example` to `config.json`, populating the fields with what you require. For database, insert the schema you created.

3. Run `python3 setup.py` - this will populate your chosen schema with our database setup, and install all of our requirements

4. Run `python3 bot.py` - you're all ready to go!

