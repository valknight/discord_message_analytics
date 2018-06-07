import mysql.connector
import markovify
import json
import random
import string
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from config import config, strings

disabled_groups = config['discord']['disabled_groups']

add_message = ("INSERT INTO messages (id, channel, time) VALUES (%s, %s, %s)")
add_message_custom = "INSERT INTO `%s` (id, channel_id, time, contents) VALUES (%s, %s, %s, %s)"

cnx = mysql.connector.connect(**config['mysql'])
cursor = cnx.cursor()
app = Flask(__name__, static_url_path='/public', static_folder='./public')


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


def requires_api_access (f):
    """
    This check will check whether the user is logged in Flask's cryptographically secure tokens
    :param f:
    :return:
    """

    @wraps(f)
    def decorated (*args, **kwargs):
        try:
            api = request.args.get("api_key")
            get_keys = "SELECT `key` FROM `apikeys`"
            cnx.commit()
            cursor.execute(get_keys)
            results = cursor.fetchall()
            valid = False
            if len(results) == 0:
                return f(*args, **kwargs)
            for result in results:
                if str(api) == str(result[0]):
                    valid = True

            if not valid:
                raise InvalidUsage('API key incorrect', status_code=401)
            return f(*args, **kwargs)
        except KeyError:
            raise InvalidUsage('API key incorrect', status_code=401)

    return decorated


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route('/', methods=['GET'])
def index():
    return """
<body style="font-family:Arial;font-size:2em;padding:30px">
All of these requests require an API key unless otherwise specified. If no API keys exist, you don't have to pass one, but we HIGHLY recommend you make one.
Pass this using param <i>api_key</i>
<h6>GET methods</h6>
<b>/api/v1/generate_api_key</b> - this is used to create a new API key.
<hr>
<b>/api/v1/messages</b> - get's messages for ONE user
<br>
user = username <i>in DB</i> of user we want to get messages from
<br>
blacklist = JSON formatted list of words we want to filter out
<br>
limit = integer for max number of messages we want to get
<hr>
<b>/api/v1/count_messages</b> - count's messages for entire server
<br>
blacklist = JSON formatted list of words we want to filter out
<br>
requirelist = JSON formatted list of words required for the message to be counted - use this if you want to search for instances of a word.
<hr>
<b>/api/v1/markov</b> - get's messages for ONE user
<br>
user = username <i>in DB</i> of user we want to get messages from
<br>
blacklist = JSON formatted list of words we want to filter out
<br>
limit = integer for max number of messages we want to get
<br>
state_size = integer for state size of markov - 1 or 2 is recommended, 3 if you want it to be true to life - any higher WILL cause issues, such as nothing being returned
</body>
    """


def get_messages(table_name, blocklist, limit = None, requirelist=[]):
    """
    user_id : ID of user you want to get messages for

    Returns:

    messages: list of all messages from a user
    channels: list of all channels relevant to messages, in same order
    """
    if limit is None:
        get_messages = "SELECT `contents`, `channel_id` FROM `%s` ORDER BY TIME DESC"
    else:
        get_messages = "SELECT `contents`, `channel_id` FROM `%s` ORDER BY TIME DESC LIMIT " + str(int(limit))

    cursor.execute(get_messages, (table_name, ))
    results = cursor.fetchall()
    messages = []
    channels = []
    blocklist_full = blocklist + get_blocklist(get_id(table_name))

    for result in results:
        valid = True
        for word in result[0].split(" "):
            if word in blocklist_full:
                valid = False
        if valid:
            if requirelist==[]:
                messages.append(result[0])
                channels.append(result[1])
            else:
                for word in result[0].split(" "):
                    if word.lower() in requirelist:
                        messages.append(result[0])
                        channels.append(result[1])

    return messages, channels


def get_id(table_name):
    query = "SELECT user_id FROM users WHERE username = %s"
    cursor.execute(query, (table_name, ))
    results = cursor.fetchall()
    if len(results)==0:
        return None
    return (results[0])[0]

def get_blocklist(user_id):
    user_id = str(user_id)
    get = "SELECT blocklist FROM blocklists WHERE user_id = %s"
    cursor.execute(get, (user_id, ))
    resultset = cursor.fetchall()
    if not resultset:
        #add a blank blocklist
        create_user = "INSERT INTO blocklists (user_id, blocklist) VALUES (%s, '[]')"
        cursor.execute(create_user, (user_id, ))
        return []
    return json.loads(resultset[0][0])


def opted_in(user=None, user_id=None):
    """
    ID takes priority over user if provided

    User: Logged username in DB
    ID: ID of user

    Returns true if user is opted in, false if not
    """
    if user_id is None:
        get_user = "SELECT `opted_in`, `username` FROM `users` WHERE  `username`=%s;"
    else:
        get_user = "SELECT `opted_in`, `username` FROM `users` WHERE  `user_id`=%s;"
        user = user_id

    cursor.execute(get_user, (user, ))
    results = cursor.fetchall()
    try:
        if results[0][0] != 1:
            return False
    except IndexError:
        return False
    return results[0][1]

def get_opted_in():
    query = "SELECT username FROM users WHERE opted_in = 1"
    cursor.execute(query)
    results = cursor.fetchall()
    users = []
    for result in results:
        users.append(result[0])
    return users

#API v1


@app.route('/api/v1/generate_api_key', methods=['GET'])
@requires_api_access
def api_key():


    key = ""
    nums = ""
    for x in range(0, 10):
        nums += str(x)
    potentials = nums + string.ascii_lowercase + string.ascii_uppercase
    for x in range(0, 32):
        key += str(random.choice(potentials))

    get_keys = "INSERT INTO `gssp_logging`.`apikeys` (`key`) VALUES (%s);"
    cursor.execute(get_keys, (key, ))
    cnx.commit()
    return jsonify({"key":key})

@app.route('/api/v1/count_messages', methods=['GET'])
@requires_api_access
def count_messages():
    count = 0
    users = get_opted_in()
    blocklist = request.args.get("blocklist", "[]")
    requirelist = request.args.get("requirelist", "[]") # requirelist is a list of words we NEED for it to be counted
    blocklist = json.loads(blocklist)
    requirelist = json.loads(requirelist)
    for user in users:
        messages_temp, channels_temp = get_messages(user, blocklist=blocklist, requirelist=requirelist)
        if requirelist == []:
            count += len(messages_temp)
        else: # this means we've been given at least ONE thing in our requirelist
            for message in messages_temp:
                for word in message.split(" "):
                    if word.lower() in requirelist:
                        count += 1
                        break

    to_return = dict(count=count, users=users)
    return jsonify(to_return)

@app.route('/api/v1/messages', methods=['GET'])
@requires_api_access
def messages():
    blocklist = request.args.get("blocklist", "[]")
    blocklist = json.loads(blocklist)
    try:
        messages, channels = get_messages(request.args.get('user'), blocklist=blocklist, limit=request.args.get('limit',1000))
    except mysql.connector.errors.ProgrammingError:
        messages, channels = [],[]
    to_return = []
    for x in range(0,len(messages)):
        to_return.append(dict(message=messages[x], channel=channels[x]))
    return jsonify(to_return)

@app.route('/api/v1/markov', methods=['GET'])
@requires_api_access
def markov():

    blocklist = request.args.get("blocklist", "[]")
    blocklist = json.loads(blocklist)

    try:
        messages, channels = get_messages(request.args.get('user'), blocklist=blocklist, limit=request.args.get('limit',1000))
    except mysql.connector.errors.ProgrammingError:
        raise InvalidUsage('User data does not exist', status_code=400)
    
    text = ""
    for message in messages:
        text += message + "\n"

    text_model = markovify.NewlineText(text, state_size=int(request.args.get("state_size", 1)))
    text = text_model.make_short_sentence(140)
    return jsonify(dict(markov=text))
    
if __name__ == "__main__":
    app.run(**config['web'])
