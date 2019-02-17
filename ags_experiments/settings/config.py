import json

config_f = open("ags_experiments/settings/config.json")
config = json.load(config_f)

strings_f = open("ags_experiments/settings/strings.json")
strings = json.load(strings_f)[config['language']]
