# This script is designed to help in creating word lists for use with hangman
import json

with open("word_list.txt") as a:
	b = a.read().split("\n")

while b[len(b)-1] == "":
	del b[len(b)-1] # removes empty strings at end of file

to_write = dict(license="These words have been sourced from google-10000-english. License at https://github.com/first20hours/google-10000-english/blob/master/LICENSE.md", words=b)
with open("words.json", "w") as c:
	c.write(json.dumps(to_write))
