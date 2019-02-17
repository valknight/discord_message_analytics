import json

import mysql.connector.errors

from gssp_experiments.database import cursor, cnx, cursor_dict
from gssp_experiments.logger import logger

add_message_custom = "INSERT INTO `messages_detailed` (id, user_id, channel_id, time, contents) VALUES (%s, %s, %s, %s, %s)"
insert_users = "INSERT INTO `gssp`.`users` (`user_id`) VALUES (%s);"
insert_settings = "INSERT INTO `gssp`.`ping_settings` (`user_id`) VALUES (%s);"
insert_role = "INSERT INTO `gssp`.`roles` (`role_id`, `role_name`, `guild_id`, `is_pingable`) VALUES (%s, %s, %s, %s);"
update_role = "UPDATE `gssp`.`roles` SET `role_name`=%s, `is_pingable`=%s WHERE `role_id`=%s;" # we don't have guild_id here, as this doesn't change.


class DatabaseTools():
    def __init__(self, client):
        self.client = client

    def add_message_to_db(self, message):
        from gssp_experiments.client_tools import ClientTools
        self.client_tools = ClientTools(self.client)
        try:
            is_allowed = self.client_tools.channel_allowed(
                message.channel.id, message.channel, message.channel.is_nsfw())
        except AttributeError:
            is_allowed = False  # in PMs, and other channels, NSFW isn't an option
        if is_allowed:
            try:
                while True:
                    result = cursor.fetchone()
                    if result is not None:
                        logger.debug(result + " - < Unread result")
                    else:
                        break
                cursor.execute(add_message_custom, (
                    int(message.id), message.author.id, str(
                        message.channel.id),
                    message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    message.content,))
            except mysql.connector.errors.IntegrityError:
                pass
            except mysql.connector.errors.DataError:
                logger.warn(
                    "Couldn't insert {} - likely a time issue".format(message.id))
            cnx.commit()

    def opted_in(self, user=None, user_id=None):
        """
        ID takes priority over user if provided

        User: Logged username in DB
        ID: ID of user

        Returns true if user is opted in, false if not
        """
        try:
            cursor.fetchall()  # we do this just to make sure we don't get any erorrs from MySQL later
        except mysql.connector.errors.InterfaceError:
            pass
        if user_id is None:
            get_user = "SELECT `opted_in`, `username` FROM `users` WHERE  `username`=%s;"
        else:
            get_user = "SELECT `opted_in`, `username` FROM `users` WHERE  `user_id`=%s;"
            user = user_id
        cursor.execute(get_user, (user,))
        results = cursor.fetchall()
        try:
            if results[0][0] != 1:
                return False
        except IndexError:
            return False
        return results[0][1]

    async def save_markov(self, model, user_id):
        """
        Save a model to markov table

        user_id : user's ID we want to save for
        model: Markov model object
        """
        save = "INSERT INTO `markovs` (`user`, `markov_json`) VALUES (%s, %s);"
        save_update = "UPDATE `markovs` SET `markov_json`=%s WHERE `user`=%s;"

        try:
            cursor.execute(save, (user_id, model.to_json()))
        except mysql.connector.errors.IntegrityError:
            cursor.execute(save_update, (model.to_json(), user_id))
        cnx.commit()
        return

    async def get_blocklist(self, user_id):
        user_id = str(user_id)
        get = "SELECT blocklist FROM blocklists WHERE user_id = %s"
        cursor.execute(get, (user_id,))
        resultset = cursor.fetchall()
        if not resultset:
            # add a blank blocklist
            create_user = "INSERT INTO blocklists (user_id, blocklist) VALUES (%s, '[]')"
            cursor.execute(create_user, (user_id,))
            return []
        return json.loads(resultset[0][0])

    def is_automated(self, user):
        """
        Returns true if user is opted in to automation, false if not
        """
        cnx.commit()
        get_user = "SELECT `automate_opted_in` FROM `users` WHERE  `user_id`=%s;"
        cursor.execute(get_user, (user.id,))
        results = cursor.fetchall()
        cnx.commit()
        try:
            if results[0][0] != 1:
                return False
        except IndexError:
            return False
        return True

    async def get_messages(self, user_id, limit: int, server=False):
        """
        user_id : ID of user you want to get messages for

        Returns:

        messages: list of all messages from a user
        channels: list of all channels relevant to messages, in same order
        """
        if server:
            get_messages = "SELECT `contents`, `channel_id` FROM `messages_detailed` ORDER BY TIME DESC LIMIT " + str(
                int(limit))
            cursor.execute(get_messages)
        else:
            get_messages = "SELECT `contents`, `channel_id` FROM `messages_detailed` WHERE `user_id` = %s ORDER BY TIME DESC LIMIT " + str(
                int(limit))
            cursor.execute(get_messages, (user_id,))
        results = cursor.fetchall()
        messages = []
        channels = []
        if server is True:
            blocklist = []
        else:
            blocklist = await self.get_blocklist(user_id)
        for result in results:
            valid = True
            for word in result[0].split(" "):
                if word in blocklist:
                    valid = False
            if valid:
                messages.append(result[0])
                channels.append(result[1])

        return messages, channels

    async def get_message_count(self, user_id=None):
        """
        Get number of messages sent
        You can specify user_id to get messages from only one user
        """
        if user_id is None:
            query = "SELECT COUNT(*) as message_count FROM messages_detailed"
            cursor_dict.execute(query)
        else:
            query = "SELECT COUNT(*) as message_count FROM messages_detailed WHERE user_id = %s"
            cursor_dict.execute(query, (user_id, ))
        res = cursor_dict.fetchall()[0]
        return int(res['message_count'])
