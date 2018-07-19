import subprocess
import sys

import discord
import mysql
from discord.ext import commands

from gssp_experiments.checks import is_owner_or_admin
from gssp_experiments.client_tools import ClientTools, add_message
from gssp_experiments.colours import red, green
from gssp_experiments.database import cnx, cursor
from gssp_experiments.database.database_tools import DatabaseTools
from gssp_experiments.settings.config import config, strings

startup_extensions = [
    "gssp_experiments.cogs.controls",
    "gssp_experiments.cogs.markov",
    "gssp_experiments.cogs.sentiment",
    "gssp_experiments.cogs.slurs",
    "gssp_experiments.cogs.nyoom",
    "gssp_experiments.cogs.tagger",
    "gssp_experiments.cogs.fun"
]


class Admin():

    def __init__(self, client):
        self.automated = subprocess.Popen([sys.executable, "automated_messages.py"])
        self.client = client
        self.database_tools = DatabaseTools(client)
        self.client_tools = ClientTools(client)
        for extension in startup_extensions:
            try:
                client.load_extension(extension)
            except Exception as e:
                exc = '{}: {}'.format(type(e).__name__, e)
                print('Failed to load extension {}\n{}'.format(extension, exc))

    @commands.is_owner()
    @commands.command()
    async def unload(self, ctx, extension_name: str):
        """Unloads an extension."""
        self.client.unload_extension(extension_name)
        await ctx.send("{} unloaded.".format(extension_name))

    @commands.is_owner()
    @commands.command()
    async def load(self, ctx, extension_name: str):
        """Loads an extension. """
        self.client.load_extension(extension_name)
        await ctx.send("{} loaded.".format(extension_name))

    @commands.is_owner()
    @commands.command()
    async def reload(self, ctx):
        """Reload all existing cogs"""

        em = discord.Embed(title="Killing automated bot", color=red)
        output = await ctx.channel.send(embed=em)
        self.automated.kill()

        reload_text = "Reloading {}"
        startup_extensions_temp = startup_extensions
        startup_extensions_temp.insert(0, "gssp_experiments.cogs.admin")

        em = discord.Embed(title="Reloading - please wait", color=red)
        await output.edit(embed=em)

        for cog in startup_extensions_temp:
            self.client.unload_extension(cog)
            self.client.load_extension(cog)

        em = discord.Embed(title="Finished!", colour=green)
        await output.edit(embed=em)

    @commands.is_owner()
    @commands.command()
    async def process_server(self, ctx):
        """
        Admin command used to record anonymous analytical data.
        """
        for channel in ctx.guild.text_channels:
            # we run through every channel as discord doesn't provide an
            # easy alternative
            print(str(channel.name) + " is being processed. Please wait.")
            async for message in channel.history(limit=None, reverse=True):
                try:
                    cursor.execute(add_message,
                                   (int(message.id), str(ctx.channel.id),
                                    message.created_at.strftime('%Y-%m-%d %H:%M:%S')))
                except mysql.connector.errors.DataError:
                    print("Couldn't insert {} - likely a time issue".format(message.id))
                except mysql.connector.errors.IntegrityError:
                    pass
            # commit is here, as putting it in for every message causes
            # mysql to nearly slow to a halt with the amount of queries
            cnx.commit()
            print(str(channel.name) + " has been processed.")
        print("Server {} processing completed".format(str(ctx.guild)))

    @is_owner_or_admin()
    @commands.command()
    async def is_processed(self, ctx, user=None):
        """
        Admin command used to check if a member has opted in
        """
        if user is None:
            user = ctx.author.name

        await ctx.send(strings['process_check']['status']['checking'])
        if not self.database_tools.opted_in(user=user):
            return await ctx.send(strings['process_check']['status']['not_opted_in'])
        await ctx.send(strings['process_check']['status']['opted_in'])
        return

    @commands.command()
    async def combine_messages(self, ctx):
        """
        This is used for migrating to the new system of tracking.

        """
        cnx = mysql.connector.connect(**config['mysql'])
        cursor = cnx.cursor(dictionary=True)
        table_name = self.database_tools.opted_in(user_id=ctx.author.id)

        query_users = "SELECT user_id, username FROM `gssp_logging`.`users` WHERE opted_in = 1"
        cursor.execute(query_users)
        users = cursor.fetchall()
        insert_query = "INSERT INTO `gssp_logging`.`messages_detailed` (`id`, `user_id`, `channel_id`, `time`, `contents`) VALUES (%s, %s, %s, %s, %s);"
        query = "SELECT * FROM `%s`"
        drop = "DROP TABLE `gssp_logging`.`%s`;"
        for user in users:
            try:
                cursor.execute(query, (self.database_tools.opted_in(user_id=user['user_id']),))
                messages = cursor.fetchall()
                await ctx.send("Combining " + user['username'])
                for message in messages:
                    try:
                        cursor.execute(insert_query, (
                            message['id'], user['user_id'], message['channel_id'], message['time'],
                            message['contents']))
                    except:
                        pass
                cnx.commit()
                await ctx.send("Inserted %s for %s" % (len(messages), user['username']))
                try:
                    cursor.execute(drop, (self.database_tools.opted_in(user_id=user['user_id']),))
                except:
                    pass
            except:
                pass
            cnx.commit()
        return await ctx.send("Done!")


def setup(client):
    client.add_cog(Admin(client))
