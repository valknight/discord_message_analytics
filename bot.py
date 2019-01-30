import os

import discord
import emoji
import mysql
from discord.ext import commands

from gssp_experiments.settings import guild_settings
from gssp_experiments import set_activity
from gssp_experiments.client_tools import ClientTools
from gssp_experiments.database import cnx, cursor
from gssp_experiments.database.database_tools import DatabaseTools, insert_users, insert_settings, insert_role, \
    update_role
from gssp_experiments.role_c import DbRole
from gssp_experiments.settings.config import config, strings
from gssp_experiments.logger import logger

if config['discord']['debug'] or bool(os.environ.get('discord_experiments_debug')):
    logger.info("Running in debug mode.")
    debug = True
    prefix = config['discord']['prefix_debug']
else:
    logger.info("Running in production mode.")
    debug = False
    prefix = config['discord']['prefix']

client = commands.Bot(
    command_prefix=prefix, owner_id=config['discord']['owner_id'])

client_tools = ClientTools(client)
database_tools = DatabaseTools(client)
token = config['discord']['token']


@client.event
async def on_ready():
    game = discord.Game("Starting")
    await client.change_presence(activity=game)
    logger.info("Bot starting. Please wait for synchroization to complete.")

    insert_channel = "INSERT INTO channels (channel_id, channel_name) VALUES (%s, %s)"
    update_channel = "UPDATE `gssp_logging`.`channels` SET `channel_name`=%s WHERE `channel_id`=%s;"

    members = []
    # we run this for loop twice so we can seperate scraping of data from core components
    for guild in client.guilds:
            guild_settings.add_guild(guild)
    
    if not bool(config['discord'].get("skip_scrape")):
        for guild in client.guilds:
            logger.info("{}: Updating channels".format(str(guild)))
            for channel in guild.text_channels:
                try:
                    cursor.execute(insert_channel, (channel.id, channel.name))
                    logger.debug("Inserted {} to DB".format(channel.name))
                except mysql.connector.errors.IntegrityError:
                    cursor.execute(update_channel, (channel.name, channel.id))
                    logger.debug("Updated {}".format(channel.name))
            logger.info("{}: Updating users".format(str(guild)))
            for member in guild.members:
                name = database_tools.opted_in(user_id=member.id)
                if name is not False:
                    members.append(member)
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
        logger.warn(
            "Skipping scraping data from existing servers - data may be out of date")
    # This needs to be here, so that all the other cogs can be loaded
    client.load_extension("gssp_experiments.cogs.loader")
    await set_activity(client)
    logger.info("\n[Connected to Discord]\n[Username]  -   [ {} ]\n[User  ID]  -   [ {} ]".format(
        client.user.name, client.user.id))

    logger.info(
        "Initialising building data profiles on existing messages. This will take a while.")
    await client_tools.build_data_profile(members, limit=None)


@client.event
async def on_message(message):
    await set_activity(client)
    # this set of code in on_message is used to save incoming new messages
    await client.process_commands(message)
    return await client_tools.process_message(message)


@client.event
async def on_command_error(ctx, error):
    if not debug:
        if isinstance(error, commands.CommandInvokeError):
            await client_tools.error_embed(ctx, error)
        else:
            if isinstance(error, commands.NoPrivateMessage):
                embed = discord.Embed(description="")
            elif isinstance(error, commands.DisabledCommand):
                embed = discord.Embed(
                    description=strings['errors']['disabled'])
            elif isinstance(error, commands.MissingRequiredArgument):
                embed = discord.Embed(
                    description=strings['errors']['argument_missing'].format(error.args[0]))
            elif isinstance(error, commands.BadArgument):
                embed = discord.Embed(
                    description=strings['errors']['bad_argument'].format(error.args[0]))
            elif isinstance(error, commands.TooManyArguments):
                embed = discord.Embed(
                    description=strings['errors']['too_many_arguments'])
            elif isinstance(error, commands.BotMissingPermissions):
                embed = discord.Embed(description="{}".format(
                    error.args[0].replace("Bot", strings['bot_name'])))
            elif isinstance(error, commands.MissingPermissions):
                embed = discord.Embed(description="{}".format(error.args[0]))
            elif isinstance(error, commands.NotOwner):
                embed = discord.Embed(
                    description=strings['errors']['not_owner'].format(strings['owner_firstname']))
            elif isinstance(error, commands.CheckFailure):
                embed = discord.Embed(
                    description=strings['errors']['no_permission'])
            elif isinstance(error, commands.CommandError):
                if not config['discord']['prompt_command_exist']:
                    embed = discord.Embed(description="")
                    return
                embed = discord.Embed(
                    description=strings['errors']['command_not_found'])
            else:
                embed = discord.Embed(
                    description=strings['errors']['placeholder'].format(strings['bot_name']))
            if embed:
                embed.colour = 0x4c0000
                await ctx.send(embed=embed, delete_after=config['discord']['delete_timeout'])
    else:
        raise error


@client.event
async def on_member_join(member):
    try:
        cursor.execute(insert_users, (member.id,))
    except mysql.connector.errors.IntegrityError:
        pass  # we pass because we just want to make sure we add any new users, so we expect some already here
    try:
        cursor.execute(insert_settings, (member.id,))
    except mysql.connector.errors.IntegrityError:
        pass  # see above
    logger.info("Added {}".format(str(member)))


@client.event
async def on_guild_join(guild):
    guild_settings.add_guild(guild=guild)


if __name__ == "__main__":
    client.run(token)
