import json

import discord
import mysql
from discord.ext import commands

from gssp_experiments.client_tools import ClientTools
from gssp_experiments.database import cursor, cnx
from gssp_experiments.logger import logger
from gssp_experiments.database.database_tools import DatabaseTools
from gssp_experiments.settings.config import strings, config
from gssp_experiments import colours
opt_in_message = """
We want to protect your information, and therefore you need to read the following in detail. We keep it brief as a lot of this is important for you to know incase you change your mind in the future.
            ```
By proceeding with using this command, you agree for us to permanently store your data outside of Discord on a server located within Europe. This data will be used for data analysis and research purposes. Due to the worldwide nature of our team it may be transferred back out of the EU.

As per the GDPR, if you are under 18, please do not run this command, as data collection from minors is a big legal issue we don't want to get into. Sorry!

You also have the legal right to request your data is deleted at any point, which can be done by messaging Val. Upon deletion, it will be removed from all datasets, however communication regarding the datasets before your data removal may remain in this server, including in moderators private chats. You also have the legal right to request a full copy of all data stored on you at any point - this can also be done by messaging Val (and she'll be super happy to as it means she gets to show off her nerdy knowhow).

Your data may also be stored on data centres around the world, due to our usage of Google Team Drive to share files. All exports of the data will also be deleted by all moderators, including exports stored on data centres used for backups as discussed.```
"""


class Controls():
    def __init__(self, client):
        self.client = client
        self.database_tools = DatabaseTools(client)
        self.client_tools = ClientTools(client)

    @commands.command()
    async def experiments(self, ctx):
        """
        Opt into experiments
        """
        message = ctx.message
        channel = message.channel

        author = message.author
        create_user = "INSERT INTO `users` (`user_id`, `username`) VALUES (%s, %s);"
        try:
            cursor.execute(create_user, (author.id, author.name))
            cnx.commit()

            em = discord.Embed(
                title=strings['data_collection']['opt_in_title'], description=opt_in_message)

            em.set_footer(text=strings['data_collection']['opt_in_footer'])
            return await channel.send(embed=em)
        except mysql.connector.errors.IntegrityError:
            get_user = "SELECT `username` FROM `users` WHERE  `user_id`=%s;"
            cursor.execute(get_user, (author.id,))

            opt_in_user = "UPDATE `users` SET `opted_in`=b'1' WHERE  `user_id`=%s;"

            cursor.execute(opt_in_user, (author.id,))
        await channel.send(strings['data_collection']['data_track_start'] + " for " + str(ctx.message.author))

        await self.client_tools.build_data_profile([author])
        await channel.send(strings['data_collection']['complete'].format(author.name))

    @commands.command()
    async def automated(self, ctx):
        """
        Opt in to automated messages. Run this again to opt out.
        """
        if not self.database_tools.opted_in(user_id=ctx.author.id):
            return await ctx.channel.send(strings['tagger']['errors']['not_opted_in'])

        if self.database_tools.is_automated(ctx.author):
            output = await ctx.channel.send("Opting you out of automation.")
            query = "UPDATE `users` SET `automate_opted_in`=b'0' WHERE `user_id`=%s;"
            cursor.execute(query, (ctx.author.id,))
            cnx.commit()
            return await output.edit(
                content='Opted out - you will be removed from the pool on the next refresh (IE: when the bot goes back around in a loop again)')

        else:
            output = await ctx.channel.send("Opting you into automation")
            query = "UPDATE`users` SET `automate_opted_in`=b'1' WHERE `user_id`=%s;"
            cursor.execute(query, (ctx.author.id,))
            cnx.commit()
            return await output.edit(content='Opted in!')

    @commands.command()
    async def blocklist(self, ctx, command=None, word=None):
        """
        Prevents words from being shown publicly through methods such as markov and markov_server.
        Note: they will still be logged, and this just prevents them being shown in chat.

        Command: option to use
        Word: Word to add or remove from blocklist
        """
        pm_channel = (discord.channel.DMChannel == type(ctx.channel))
        if not pm_channel:
            try:
        await ctx.message.delete()
            except discord.errors.Forbidden:
                logger.warn(
                    "Could not delete blacklist command, lacking permissions")
        if command is None:
            return await ctx.send("""
        No subcommand selected - please enter a subcommand for your blocklist.

        ?blocklist add [word] : Add word to blocklist
        ?blocklist remove [word] : Remove word from blocklist
        ?blocklist get : Get PM of current blocklist
                """)
        # fetch current blocklist
        blockL = await self.database_tools.get_blocklist(ctx.author.id)
        update_blocklist = "UPDATE blocklists SET blocklist = %s WHERE user_id = %s"

        if command == "add":
            if word is None:
                return await ctx.send(strings['blocklist']['status']['no_word'],
                                      delete_after=config['discord']['delete_timeout'])
            msg = await ctx.send(strings['blocklist']['status']['adding'])

            # check if the word is already on the list. throw error if it is
            if word.lower() not in blockL:
                # if its not then add it
                blockL.append(word.lower())
                # update DB with new list
                new_json = json.dumps(blockL)
                cursor.execute(update_blocklist, (new_json, ctx.author.id,))

            else:
                await msg.delete?()
                return await ctx.send(strings['blocklist']['status']['exist'])

        elif command == "remove":
            if word is None:
                return await ctx.send(strings['blocklist']['status']['no_word'],
                                      delete_after=config['discord']['delete_timeout'])
            msg = await ctx.send(strings['blocklist']['status']['removing'])

            # try and remove it from list (use a try statement, catching ValueError)
            try:
                blockL.remove(word.lower())
            except ValueError:
                return await msg.edit(content=strings['blocklist']['status']['not_exist'])

            # update DB with new list
            new_json = json.dumps(blockL)
            cursor.execute(update_blocklist, (new_json, ctx.author.id,))

        elif command == "get":
            # make it nice to look at
            if blockL == []:
                msg = strings['blocklist']['status']['empty']
            else:
                msg = strings['blocklist']['status']['list']
                for item in blockL:
                    # done so that the merge with the long string is only done once per word
                    part = ' ' + item + ','
                    msg += part
                msg = msg[:-1]  # trim off the trailing ,
            # send a private message with the nice to look at blocklist
            # this prevents the next commands from running
            return await ctx.author.send(msg)
        else:
            return await ctx.send("""
    No subcommand selected - please enter a subcommand for your blocklist.

    ?blocklist add [word] : Add word to blocklist
    ?blocklist remove [word] : Remove word from blocklist
    ?blocklist get : Get PM of current blocklist
                """)
        await msg.edit(content=strings['blocklist']['status']['complete'])

    @commands.command()
    async def optout(self, ctx):
        """
        Run this to optout of experiments, and delete your data
        """
        em = discord.Embed(
            title=strings['data_collection']['opt_out_starting_title'], description=strings['data_collection']['opt_out_starting_message'], color=colours.red)
        current_embed = await ctx.send(embed=em)
        await self.client_tools.optout_user(ctx.author)
        em = discord.Embed(title=strings['data_collection']['opt_out_finish_title'],
                           description=strings['data_collection']['opt_out_finish_message'], color=colours.green)
        await current_embed.edit(embed=em)


def setup(client):
    client.add_cog(Controls(client))
