from ags_experiments.client_tools import ClientTools
from ags_experiments.settings.config import config
from ags_experiments.database import cnx, cursor
from ags_experiments.database.database_tools import DatabaseTools, insert_users, insert_settings, insert_role, \
    update_role
from ags_experiments.logger import logger
from ags_experiments.role_c import DbRole
import emoji
import mysql
from discord.ext import commands

class MessageLogger(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.client_tools = ClientTools(client)
        self.database_tools = DatabaseTools(client)

        insert_channel = "INSERT INTO channels (channel_id, channel_name) VALUES (%s, %s)"
        update_channel = "UPDATE `gssp_logging`.`channels` SET `channel_name`=%s WHERE `channel_id`=%s;"
        if not bool(config['discord'].get("skip_scrape")):
            for guild in client.guilds:
                logger.info("{}: Updating channels".format(str(guild)))
                for channel in guild.text_channels:
                    try:
                        cursor.execute(insert_channel, (channel.id, emoji.demojize(channel.name)))
                        logger.debug("Inserted {} to DB".format(emoji.demojize(channel.name)))
                    except mysql.connector.errors.IntegrityError:
                        cursor.execute(update_channel, (emoji.demojize(channel.name), channel.id))
                        logger.debug("Updated {}".format(emoji.demojize(channel.name)))
                logger.info("{}: Updating users".format(str(guild)))
                for member in guild.members:
                    try:
                        cursor.execute(insert_users, (member.id,))
                    except mysql.connector.errors.IntegrityError:
                        pass  # we pass because we just want to make sure we add any new users, so we expect some already here
                    try:
                        cursor.execute(insert_settings, (member.id,))
                    except mysql.connector.errors.IntegrityError:
                        pass  # see above
                logger.info("{}: Finished {} users".format(
                    str(guild), len(guild.members)))
                logger.info("{}: Updating roles".format(str(guild)))
                for role in guild.roles:
                    if role.name != "@everyone":
                        try:
                            cursor.execute(
                                insert_role, (role.id, emoji.demojize(role.name), guild.id, int(role.mentionable)))
                        except mysql.connector.errors.IntegrityError:
                            cursor.execute(
                                update_role, (emoji.demojize(role.name), int(role.mentionable), role.id))

                        # this is designed to assist with migration, by moving old discord role members over to the new
                        # system seamlessly
                        member_ids = []
                        for member in role.members:
                            member_ids.append(member.id)
                        role_db = DbRole(role.id, role.name, 0, members=member_ids)
                        role_db.save_members()
                logger.info("{}: Finished {} roles".format(
                    guild, len(guild.roles)))
                cnx.commit()
        else:
            logger.warn("Skipping scraping data from existing servers - data may be out of date")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        return await self.client_tools.process_message(message)

def setup(client):
    client.add_cog(MessageLogger(client))
