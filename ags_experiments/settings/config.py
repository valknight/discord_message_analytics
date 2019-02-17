import json

config_f = open("gssp_experiments/settings/config.json")
config = json.load(config_f)

strings_f = open("gssp_experiments/settings/strings.json")
strings = json.load(strings_f)[config['language']]
