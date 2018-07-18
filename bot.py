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
from gssp_experiments.database import cnx, cursor
from gssp_experiments.database.tools import DatabaseTools
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
__version__ = "0.6"

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

add_message = ("INSERT INTO messages (id, channel, time) VALUES (%s, %s, %s)")

startup_extensions = [
    "gssp_experiments.cogs.controls",
    "gssp_experiments.cogs.markov",
    "gssp_experiments.cogs.nyoom",
    "gssp_experiments.cogs.tagger",
    "gssp_experiments.cogs.fun"
]


@client.event
async def on_ready():
    for extension in startup_extensions:
        try:
            client.load_extension(extension)
        except Exception as e:
            exc = '{}: {}'.format(type(e).__name__, e)
            print('Failed to load extension {}\n{}'.format(extension, exc))
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


@commands.is_owner()
@client.command()
async def process_server(ctx):
    """
    Admin command used to record anonymous analytical data.
    """
    for channel in ctx.guild.text_channels:
        # we run through every channel as discord doesn't provide an
        # easy alternative
        logger.debug(str(channel.name) + " is being processed. Please wait.")
        async for message in channel.history(limit=None, reverse=True):
            try:
                cursor.execute(add_message,
                               (int(message.id), str(ctx.channel.id), message.created_at.strftime('%Y-%m-%d %H:%M:%S')))
            except mysql.connector.errors.DataError:
                logger.warning("Couldn't insert {} - likely a time issue".format(message.id))
            except mysql.connector.errors.IntegrityError:
                pass
        # commit is here, as putting it in for every message causes
        # mysql to nearly slow to a halt with the amount of queries
        cnx.commit()
        logger.info(str(channel.name) + " has been processed.")
    logger.info("Server {} processing completed".format(str(ctx.guild)))


@commands.is_owner()
@client.command()
async def is_processed(ctx, user=None):
    """
    Admin command used to check if a member has opted in
    """
    if user is None:
        user = ctx.author.name

    await ctx.send(strings['process_check']['status']['checking'])
    if not database_tools.opted_in(user=user):
        return await ctx.send(strings['process_check']['status']['not_opted_in'])
    await ctx.send(strings['process_check']['status']['opted_in'])
    return


@client.command()
async def combine_messages(ctx):
    """
    This is used for migrating to the new system of tracking.

    """
    cnx = mysql.connector.connect(**config['mysql'])
    cursor = cnx.cursor(dictionary=True)
    table_name = database_tools.opted_in(user_id=ctx.author.id)

    query_users = "SELECT user_id, username FROM `gssp_logging`.`users` WHERE opted_in = 1"
    cursor.execute(query_users)
    users = cursor.fetchall()
    insert_query = "INSERT INTO `gssp_logging`.`messages_detailed` (`id`, `user_id`, `channel_id`, `time`, `contents`) VALUES (%s, %s, %s, %s, %s);"
    query = "SELECT * FROM `%s`"
    drop = "DROP TABLE `gssp_logging`.`%s`;"
    for user in users:
        try:
            cursor.execute(query, (database_tools.opted_in(user_id=user['user_id']),))
            messages = cursor.fetchall()
            await ctx.send("Combining " + user['username'])
            for message in messages:
                try:
                    cursor.execute(insert_query, (
                        message['id'], user['user_id'], message['channel_id'], message['time'], message['contents']))
                except:
                    pass
            cnx.commit()
            await ctx.send("Inserted %s for %s" % (len(messages), user['username']))
            try:
                cursor.execute(drop, (database_tools.opted_in(user_id=user['user_id']),))
            except:
                pass
        except:
            pass
        cnx.commit()
    return await ctx.send("Done!")


if __name__ == "__main__":
    client.run(token)
