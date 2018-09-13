import concurrent
import json

import discord
import mysql
import mysql.connector

from gssp_experiments import colours
from gssp_experiments.database import cnx, cursor
from gssp_experiments.database.database_tools import DatabaseTools
from gssp_experiments.settings.config import config, strings

enabled_groups = config['discord']['enabled_groups']

add_message = ("INSERT INTO messages (id, channel, time) VALUES (%s, %s, %s)")


class ClientTools():

    def __init__(self, client):
        self.database_tools = DatabaseTools(client)
        self.client = client

    def channel_allowed(self, channel_id, existing_channel, nsfw=False):
        """
        Check if a channel is allowed in current context

        channel_id: ID of channel
        existing_channel: channel object of existing channel
        nsfw: whether to only return NSFW channels
        """
        channel = self.client.get_channel(int(channel_id))
        if channel is None:
            return False

        enabled = False
        for group in enabled_groups:
            if str(channel.category).lower() == str(group).lower():
                enabled = True
                break

        if not enabled:
            return False

        if not existing_channel.is_nsfw() and bool(nsfw):
            return False

        if channel.is_nsfw():
            return bool(nsfw)  # checks if user wants / is allowed explicit markovs
            # this means that if the channel *is* NSFW, we return True, but if it isn't, we return False
        else:  # channel is SFW
            if bool(nsfw):
                return False  # this stops SFW chats from being included in NSFW markovs

        return True

    async def build_messages(self, ctx, nsfw, messages, channels, selected_channel=None):
        """
            Returns/appends to a list messages from a user
            Params:
            messages: list of messages
            channel: list of channels for messages
            selected_channel: Not required, but channel to filter to. If none, filtering is disabled.
            text = list of text that already exists. If not set, we just create one
        """
        text = []

        for counter, m in enumerate(messages):

            if self.channel_allowed(channels[counter], ctx.message.channel, nsfw):
                if selected_channel is not None:
                    if self.client.get_channel(int(channels[counter])).id == selected_channel.id:
                        text.append(m)
                else:
                    text.append(m)
        return text

    async def get_delete_emoji(self):
        delete_emoji = self.client.get_emoji(int(strings['emojis']['delete']))
        if delete_emoji is not None:
            emoji_name = delete_emoji.name
        else:
            emoji_name = "❌"
        return emoji_name, delete_emoji

    async def markov_embed(self, title, message):
        em = discord.Embed(title=title, description=message)
        name = await self.get_delete_emoji()
        name = name[0]
        em.set_footer(text=strings['markov']['output']['footer'].format(name))
        return em

    async def delete_option(self, client, message, ctx, delete_emoji, timeout=config['discord']['delete_timeout']):
        """Utility function that allows for you to add a delete option to the end of a command.
        This makes it easier for users to control the output of commands, esp handy for random output ones."""
        await message.add_reaction(delete_emoji)

        def check(r, u):
            return str(r) == str(delete_emoji) and u == ctx.author and r.message.id == message.id

        try:
            await client.wait_for("reaction_add", timeout=timeout, check=check)
            await message.remove_reaction(delete_emoji, client.user)
            await message.remove_reaction(delete_emoji, ctx.author)
            em = discord.Embed(title=str(ctx.message.author) +
                                     " deleted message", description="User deleted this message.")

            return await message.edit(embed=em)
        except concurrent.futures._base.TimeoutError:
            await message.remove_reaction(delete_emoji, client.user)

    async def build_data_profile(self, members, limit=50000):
        """
        Used for building a data profile based on a user

        Members: list of members we want to import for
        Guild: Guild object
        Limit: limit of messages to be imported
        """
        for guild in self.client.guilds:
            for cur_channel in guild.text_channels:
                adding = False
                for group in enabled_groups:
                    if str(cur_channel.category).lower() == str(group).lower():
                        adding = True
                        break

                if adding:
                    counter = 0
                    already_added = 0
                    async for message in cur_channel.history(limit=limit, reverse=True):
                        if message.author in members:
                            self.database_tools.add_message_to_db(message)
                    print(
                        "{} scraped for {} users - added {} messages, found {} already added".format(cur_channel.name,
                                                                                                     len(members),
                                                                                                     counter,
                                                                                                     already_added))

    async def process_message(self, message):
        await self.check_slurs(message)
        user_exp = self.database_tools.opted_in(user_id=message.author.id)

        if user_exp is not False:
            self.database_tools.add_message_to_db(message)
        # this records analytical data - don't adjust this without reading
        # Discord TOS first
        try:
            cursor.execute(add_message,
                           (int(message.id), str(message.channel.id), message.created_at.strftime('%Y-%m-%d %H:%M:%S')))
            cnx.commit()
        except mysql.connector.errors.IntegrityError:
            pass
        try:
            # if its double(or more) prefixed then it cant be a command (?word is a command, ????? is not)
            if message.content[len(config['discord']['prefix'])] == config['discord']['prefix']:
                return
        except IndexError:
            return

    async def check_slurs(self, message):
        if type(message.channel) == discord.DMChannel:
            return
        matches = []
        file = open("gssp_experiments/data/bad_words.json")
        slurs = json.loads(file.read())
        for slur in slurs:
            if slur.lower() != "" and slur in message.content.lower():
                matches.append(slur)
        if len(matches) > 0:
            embed = discord.Embed(title="Potential usage of slur detected", color=colours.dark_red)

            embed.add_field(name="Slur(s)", value=str(matches))
            embed.add_field(name="Message", value=str(message.content))
            embed.add_field(name="Author", value=str(message.author))
            embed.add_field(name="Author ID", value=str(message.author.id))
            embed.add_field(name="Channel", value=str(message.channel))
            embed.add_field(name="Time", value=str(message.created_at))
            embed.add_field(name="Message ID", value=str(message.id))
            embed.add_field(name="Guild ID", value=str(message.channel.guild.id))
            embed.add_field(name="Guild", value=str(message.channel.guild))

            channel = self.client.get_channel(config['discord']['warning_channel'])
            await channel.send(embed=embed)
