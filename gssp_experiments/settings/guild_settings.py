import os
import json
from gssp_experiments.logger import logger

base_directory = "gssp_experiments/data"  # change this to another location if you wish per-server configs to be elsewhere

def add_guild(guild=None, guild_id=None):
    """
    Create config directory for a new guild
    :param guild: Guild object provided by discord
    :param guild_id: Raw number ID of the guild you wish to add
    """
    if guild is not None and guild_id is None:
        guild_id = guild.id

    made_change = False
    guild_path = "{}/{}".format(base_directory, guild_id)

    if not os.path.exists(base_directory):
        os.makedirs(base_directory)
        made_change = True

    if not os.path.exists(guild_path):
        os.makedirs("{}/{}".format(base_directory, guild_id))
        made_change = True
    if not os.path.exists("{}/bad_words.json".format(guild_path)):
        with open("{}/bad_words.json".format(guild_path), "w") as bad_words_f:
            bad_words_f.write(json.dumps({"words" : [], "alert_channel": None}))
        made_change = True

    if made_change:
        logger.info("Created data for {}".format(guild_id))


def write_bad_words(flags):
    """
    Updates bad words  dict spat out by get_bad_words on disk
    :param: flags: flags dict with list as key "json" and guild id as key "guild_id"
    """
    with open("{}/{}/bad_words.json".format(base_directory, flags['guild_id']), "w") as flag_f:
        flag_f.write(json.dumps(flags))


def get_bad_words(guild=None, guild_id=None):
    """
    :param guild: Guild object of the server you wish to retrieve flags for
    :param guild_id: ID of the server you wish to retrieve flags for
    :return:
    """
    if guild is not None and guild_id is None:
        guild_id = guild.id
    to_return = dict()
    try:
        json_f = open("gssp_experiments/data/{}/bad_words.json".format(guild_id))
    except FileNotFoundError:
        add_guild(guild=guild, guild_id=guild_id)
        json_f = open("gssp_experiments/data/{}/bad_words.json".format(guild_id))
    loaded_json = json.loads(json_f.read())
    json_f.close()
    loaded_json['guild_id'] = guild_id # we include this, so we can just pass this around, without the guild object
    return loaded_json