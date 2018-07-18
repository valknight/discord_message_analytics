import datetime
import json
import logging
import os
import subprocess
import sys

import discord
import mysql.connector
from discord.ext import commands

from gssp_experiments.client_tools import ClientTools
from gssp_experiments.cogs.admin import add_message
from gssp_experiments.database import cnx, cursor
from gssp_experiments.database.database_tools import DatabaseTools
from gssp_experiments.settings.config import config, strings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def restart():
    logger.info("Restarting. Please wait.")
    os.system(sys.executable + ' bot.py')


client = commands.Bot(command_prefix=config['discord']['prefix'], owner_id=config['discord']['owner_id'])

client_tools = ClientTools(client)
database_tools = DatabaseTools(client)
token = config['discord']['token']
__version__ = "0.7"

if config['version'] == "0.5" and __version__ == "0.5.1":
    config['version'] = "0.5.1"

if config['version'] != __version__:
    if config['version'] == "0.4":
        logger.warning("Found running 0.4. Running upgrades")
        config['state_size'] = 2
        logger.debug("Added state size to config")
        config['version'] = "0.5"
        logger.debug("Updated version")
        json_to_save = json.dumps(config)
        config_new = open("config.json", "w")
        config_new.write(json_to_save)
        config_new.close()
        logger.info("Saved new config file.")
        restart()
    if config['version_check']:
        logger.error(strings['config_invalid'].format(__version__, str(config['version'])))
        sys.exit(1)
    else:
        logger.warning(strings['config_invalid_ignored'].format(__version__, str(config['version'])))

disabled_groups = config['discord']['disabled_groups']


@client.event
async def on_ready():
    client.load_extension("gssp_experiments.cogs.admin")
    log_in_message = """

[Connected to Discord]
[Username]  -   [ {} ]
[User  ID]  -   [ {} ]

"""
    logger.info(log_in_message.format(client.user.name, client.user.id))

    subprocess.Popen([sys.executable, "automated_messages.py"])
    logger.info("Started automated messages sub-process")
    members = []
    total_members = 0
    for server in client.guilds:
        for member in server.members:
            name = database_tools.opted_in(user_id=member.id)
            total_members += 1
            if name is not False:
                members.append(member)
    messages_processed = "SELECT COUNT(*) FROM messages_detailed"
    cursor.execute(messages_processed)
    amount_full = (cursor.fetchall()[0])[0]
    logger.info("Bot running with " + str(
        amount_full) + " messages avaliable fully, and . If this is very low, we cannot guarantee accurate results.")
    logger.info("Initialising building data profiles on existing messages. This will take a while.")
    await client_tools.build_data_profile(members, limit=None)


@client.event
async def on_message(message):
    # this set of code in on_message is used to save incoming new messages
    channel = message.channel
    user_exp = database_tools.opted_in(user_id=message.author.id)

    if user_exp is not False:
        database_tools.add_message_to_db(message)
    # this records analytical data - don't adjust this without reading
    # Discord TOS first
    try:
        cursor.execute(add_message,
                       (int(message.id), str(message.channel.id), message.created_at.strftime('%Y-%m-%d %H:%M:%S')))
        cnx.commit()
    except mysql.connector.errors.IntegrityError:
        pass
    try:
        if message.content[len(config['discord']['prefix'])] == config['discord'][
            'prefix']:  # if its double(or more) prefixed then it cant be a command (?word is a command, ????? is not)
            return
    except IndexError:
        return
    return await client.process_commands(message)


@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        embed = discord.Embed(title='Command Error')
        embed.description = str(error)
        embed.add_field(name='Server', value=ctx.guild)
        embed.add_field(name='Channel', value=ctx.channel.mention)
        embed.add_field(name='User', value=ctx.author)
        embed.add_field(name='Message', value=ctx.message.content)
        embed.timestamp = datetime.datetime.utcnow()
        await ctx.send(embed=embed)
    else:
        if isinstance(error, commands.NoPrivateMessage):
            embed = discord.Embed(description="")
        elif isinstance(error, commands.DisabledCommand):
            embed = discord.Embed(description=strings['errors']['disabled'])
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(description=strings['errors']['argument_missing'].format(error.args[0]))
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(description=strings['errors']['bad_argument'].format(error.args[0]))
        elif isinstance(error, commands.TooManyArguments):
            embed = discord.Embed(description=strings['errors']['too_many_arguments'])
        elif isinstance(error, commands.CommandNotFound):
            if not config['discord']['prompt_command_exist']:
                return
            embed = discord.Embed(description=strings['errors']['command_not_found'])
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(description="{}".format(error.args[0].replace("Bot", strings['bot_name'])))
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(description="{}".format(error.args[0]))
        elif isinstance(error, commands.NotOwner):
            embed = discord.Embed(description=strings['errors']['not_owner'].format(strings['owner_firstname']))
        elif isinstance(error, commands.CheckFailure):
            embed = discord.Embed(description=strings['errors']['no_permission'])
        elif isinstance(error, commands.CommandError):
            embed = discord.Embed(description=strings['errors']['command_error'].format(error.args[0]))
        else:
            embed = discord.Embed(
                description=strings['errors']['placeholder'].format(strings['bot_name']))
        if embed:
            embed.colour = 0x4c0000
            await ctx.send(embed=embed, delete_after=config['discord']['delete_timeout'])


if __name__ == "__main__":
    client.run(token)
