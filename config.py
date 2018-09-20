import json

config_f = open("config.json")
config = json.load(config_f)

strings_f = open("strings.json")
strings = json.load(strings_f)[config['language']]
