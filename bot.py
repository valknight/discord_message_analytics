import datetime
import discord
import json
import markovify
import math
import mysql.connector
import re
import time
import sys


config_f = open("config.json")
config = json.load(config_f)

strings_f = open("strings.json")
strings = json.load(strings_f)[config['language']]

from discord.ext import commands

cnx = mysql.connector.connect(**config['mysql'])
cursor = cnx.cursor()

token = config['discord']['token']
client = commands.Bot(command_prefix=config['discord']['prefix'], owner_id=config['discord']['owner_id'])

disabled_groups = config['discord']['disabled_groups']

add_message = ("INSERT INTO messages (id, channel, time) VALUES (%s, %s, %s)")

add_message_custom = "INSERT INTO `%s` (id, channel_id, time, contents) VALUES (%s, %s, %s, %s)"

opt_in_message = """
We want to protect your information, and therefore you need to read the following in detail. We keep it brief as a lot of this is important for you to know incase you change your mind in the future.
            ```
By proceeding with using this command, you agree for us to permanently store your data outside of Discord on a server located within Europe. This data will be used for data analysis and research purposes. Due to the worldwide nature of our team it may be transferred back out of the EU.

As per the GDPR, if you are under 18, please do not run this command, as data collection from minors is a big legal issue we don't want to get into. Sorry!

You also have the legal right to request your data is deleted at any point, which can be done by messaging Val. Upon deletion, it will be removed from all datasets, however communication regarding the datasets before your data removal may remain in this server, including in moderators private chats. You also have the legal right to request a full copy of all data stored on you at any point - this can also be done by messaging Val (and she'll be super happy to as it means she gets to show off her nerdy knowhow).

Your data may also be stored on data centres around the world, due to our usage of Google Team Drive to share files. All exports of the data will also be deleted by all moderators, including exports stored on data centres used for backups as discussed.```
"""


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print("Has nitro: " + str(client.user.premium))
    print('------')

    print()

    print("Ensuring no data was lost during downtime. This may take a while if a lot of users are part of your experiments")

    for server in client.guilds:
        for member in server.members:
            name = opted_in(id=member.id)
            if name is not False:
                await build_data_profile(name, member, server)


@client.event
async def on_message(message):
    # this set of code in on_message is used to save incoming new messages
    channel = message.channel
    user_exp = opted_in(id=message.author.id)

    if user_exp is not False:
        is_allowed = channel_allowed(
            channel.id, message.channel, message.channel.is_nsfw())
        if is_allowed:
            try:
                cursor.execute(add_message_custom, (user_exp, int(message.id), str(message.channel.id), message.created_at.strftime('%Y-%m-%d %H:%M:%S'), message.content,))
            except mysql.connector.errors.IntegrityError:
                pass
    # this records analytical data - don't adjust this without reading
    # Discord TOS first
    try:
        cursor.execute(add_message, (int(message.id), str(message.channel.id), message.created_at.strftime('%Y-%m-%d %H:%M:%S')))
        cnx.commit()
    except mysql.connector.errors.IntegrityError:
        pass

    return await client.process_commands(message)


@commands.is_owner()
@client.command()
async def process_server(ctx):
    """
    Admin command used to record anonymous analytical data.
    """
    print("Logging")
    for channel in ctx.guild.text_channels:
        # we run through every channel as discord doesn't provide an
        # easy alternative
        print(str(channel.name) + " is being processed. Please wait.")
        async for message in channel.history(limit=None, reverse=True):
            try:
                cursor.execute(add_message, (int(message.id), str(ctx.channel.id), message.created_at.strftime('%Y-%m-%d %H:%M:%S')))
            except mysql.connector.errors.DataError:
                print("Couldn't insert, probs a time issue")
            except mysql.connector.errors.IntegrityError:
                pass
        # commit is here, as putting it in for every message causes
        # mysql to nearly slow to a halt with the amount of queries
        cnx.commit()
        print(str(channel.name) + " has been processed.")
    print("Done!")


@client.command()
async def experiments(ctx):
    """
    Run this to opt into experiments
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
        cursor.execute(get_user, (author.id, ))
        username = (cursor.fetchall()[0])[0]

        opt_in_user = "UPDATE `users` SET `opted_in`=b'1' WHERE  `user_id`=%s;"

        cursor.execute(opt_in_user, (author.id, ))
        create_table = """
CREATE TABLE `%s` (
  `id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `channel_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `time` timestamp NULL DEFAULT NULL,
  `contents` longtext COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """

        try:
            cursor.execute(create_table, (username, ))
            await channel.send(strings['data_collection']['created_record'].format(username))
        except mysql.connector.errors.ProgrammingError:
            await channel.send(strings['data_collection']['update_record'].format(username))

    name = opted_in(id=message.author.id)

    await channel.send(strings['data_collection']['data_track_start'])
    await build_data_profile(name, author, message.guild)
    await channel.send(strings['data_collection']['complete'].format(author.name))


@commands.is_owner()
@client.command()
async def is_processed(ctx, user=None):
    """
    Admin command used to check if a member has opted in
    """
    if user is None:
        user = ctx.author.name

    await ctx.send(strings['process_check']['status']['checking'])
    if not opted_in(user=user):
        return await ctx.send(strings['process_check']['status']['not_opted_in'])
    await ctx.send(strings['process_check']['status']['opted_in'])
    return


def opted_in(user=None, id=None):
    """
    ID takes priority over user if provided

    User: Logged username in DB
    ID: ID of user

    Returns true if user is opted in, false if not
    """
    if id is None:
        get_user = "SELECT `opted_in`, `username` FROM `users` WHERE  `username`=%s;"
    else:
        get_user = "SELECT `opted_in`, `username` FROM `users` WHERE  `user_id`=%s;"
        user = id

    cursor.execute(get_user, (user, ))
    results = cursor.fetchall()
    try:
        if results[0][0] != 1:
            return False
    except IndexError:
        return False
    return results[0][1]


def get_messages(table_name):
    """
    table_name : Username of user you want to get messages for

    Returns:

    messages: list of all messages from a user
    channels: list of all channels relevant to messages, in same order
    """
    get_messages = "SELECT `contents`, `channel_id` FROM `%s` ORDER BY TIME DESC"
    cursor.execute(get_messages, (table_name, ))
    results = cursor.fetchall()
    messages = []
    channels = []

    for x in range(0, len(results)):
        messages.append(results[x][0])
        channels.append(results[x][1])

    return messages, channels


def channel_allowed(id, existing_channel, nsfw=False):
    """
    Check if a channel is allowed in current context

    id: ID of channel
    existing_channel: channel object of existing channel
    nsfw: whether to only return NSFW channels
    """
    channel = client.get_channel(int(id))

    for x in range(0, len(disabled_groups)):
        if str(channel.category).lower() == str(disabled_groups[x]).lower():
            return False

    if nsfw:
        if not existing_channel.is_nsfw():
            return False
        if channel.is_nsfw():
            return True
        else:
            return False  # this is because if NSFW is true, we only want stuff from NSFW chats
    else:
        if channel.is_nsfw():
            return False  # this is to prevent NSFW messages being included in SFW chats

    return True


async def save_markov(model, user_id):
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


async def build_messages(ctx, nsfw, messages, channels, selected_channel=None, text = []):
    """
        Returns/appends to a list messages from a user
        Params:
        messages: list of messages
        channel: list of channels for messages
        selected_channel: Not required, but channel to filter to. If none, filtering is disabled.
        text = list of text that already exists. If not set, we just create one
    """
    for x in range(0, len(messages)):

        if channel_allowed(channels[x], ctx.message.channel, nsfw):
            if selected_channel is not None:
                if client.get_channel(int(channels[x])).id == selected_channel.id:
                    text.append(messages[x])
            else:
                text.append(messages[x])
    return text


@client.command()
async def markov_server(ctx, nsfw: bool=False, selected_channel: discord.TextChannel=None):
    """
    Generates markov output based on entire server's messages.
    """

    output = await ctx.send(strings['markov']['title'] + strings['emojis']['markov'])

    await output.edit(content=output.content + "\n" + strings['markov']['status']['messages'])
    async with ctx.channel.typing():
        text = []

        print(selected_channel)
        for server in client.guilds:
            for member in server.members:
                username = opted_in(id=member.id)
                if username is not False:
                    messages, channels = get_messages(username)
                    text = await build_messages(ctx, nsfw, messages, channels, selected_channel=selected_channel, text=text)

        length = len(text)

        text1 = ""
        for x in range(0, len(text)):
            text1 += str(text[x]) + "\n"

        try:
            await output.edit(content=output.content + strings['emojis']['success'] + "\n" + strings['markov']['status']['building_markov'])
            # text_model = POSifiedText(text)
            text_model = markovify.NewlineText(text, state_size=3)
        except KeyError:
            return ctx.send('Not enough data yet, sorry!')
        await output.edit(content=output.content + strings['emojis']['success'] + "\n" + strings['markov']['status']['making'])
        text = text_model.make_short_sentence(140)
        attempt = 0
        while(True):
            attempt += 1
            if attempt >= 10:
                return await ctx.send(strings['markov']['errors']['failed_to_generate'])
            message_formatted = str(text)
            if message_formatted != "None":
                break

        em = discord.Embed(
            title=strings['markov']['output']['title_server'], description=message_formatted)

        em.set_footer(text=strings['markov']['output']['footer'])
        await output.delete()
        output = await ctx.send(embed=em)
    return await delete_option(client, ctx, output, client.get_emoji(strings['emoji']['delete']) or "❌")


@client.command()
async def markov(ctx, nsfw: bool=0, selected_channel: discord.TextChannel=None):
    """
    Generates markov output for user who ran this command
    """
    output = await ctx.send(strings['markov']['title'] + strings['emojis']['markov'])

    await output.edit(content=output.content + "\n" + strings['markov']['status']['messages'])
    async with ctx.channel.typing():
        username = opted_in(id=ctx.author.id)
        if not username:
            return await output.edit(content=output.content + strings['markov']['errors']['not_opted_in'])
            return await ctx.send()
        messages, channels = get_messages(username)

        text = await build_messages(ctx, nsfw, messages, channels, selected_channel=selected_channel)

        text1 = ""
        for x in range(0, len(text)):
            text1 += str(text[x]) + "\n"

        try:
            await output.edit(content=output.content + strings['emojis']['success'] + "\n" + strings['markov']['status']['building_markov'])
            # text_model = POSifiedText(text)
            text_model = markovify.NewlineText(text, state_size=3)
        except KeyError:
            return ctx.send('Not enough data yet, sorry!')

        await output.edit(content=output.content + strings['emojis']['success'])

        attempt = 0
        await output.edit(content=output.content + strings['emojis']['success'] + "\n" + strings['markov']['status']['analytical_data'])

        while(True):
            attempt += 1
            if attempt >= 10:
                await output.delete()
                return await ctx.send(strings['markov']['errors']['failed_to_generate'])
            new_sentance = text_model.make_short_sentence(140)
            message_formatted = str(new_sentance)
            if message_formatted != "None":
                break

        em = discord.Embed(title=str(ctx.message.author) + strings['emojis']['markov'], description=message_formatted)
        em.set_footer(text=strings['markov']['output']['footer'])
        await output.delete()
    output = await ctx.send(embed=em)
    return await delete_option(client, ctx, output, client.get_emoji(strings['emojis']['delete']) or "❌")


async def get_blacklist(user_id):
    get = "SELECT blacklist FROM blacklists WHERE user_id = %s"
    cursor.execute(get, (user_id, ))
    resultset = cursor.fetchall()
	if len(resultset) == 0:
		#add a blank blacklist
		set = "INSET INTO blacklists (user_id, blacklist) VALUES (%s, '[]')"
		cursor.execute(set, (user_id, ))
		return []
    return json.loads(resultset[0])


@client.command()
async def blacklist(ctx, command=None, word=None):
    """
    Prevents words from being shown publicly through methods such as markov and markov_server.
    Note: they will still be logged, and this just prevents them being shown in chat.

    Command: option to use
    Word: Word to add or remove from blacklist
    """
    await ctx.message.delete()
    if command is None:
        return await ctx.send("""
No subcommand selected - please enter a subcommand for your blacklist.

?blacklist add [word] : Add word to blacklist
?blacklist remove [word] : Remove word from blacklist
?blacklist get : Get PM of current blacklist
            """)

    if command == "add":
        if word is None:
            return await ctx.send(strings['blacklist']['status']['no_word'])
        msg = await ctx.send(strings['blacklist']['status']['adding'])
		id = ctx.message.author.id
		# fetch the current blacklist
		blackL = get_blacklist(id)
		exists = True
		if blackL == []:
			exists = False
		#check if the word is already on the list. throw error if it is
		if word != blackL:
			# if its not then add it
			blackL.append(word)
			# update DB with new list
			new_json = json.dumps(blackL)
			set = "UPDATE blacklists SET blacklist = %s WHERE user_id = %s"
			cursor.execute(set, (new_json, user_id, ))
			await ctx.send(strings['blacklist']['status']['complete'])
		else:
			await ctx.send(strings['blacklist']['status']['exist'])
    elif command == "remove":
        if word is none:
            return await ctx.send(strings['blacklist']['status']['no_word'])
        msg = await ctx.send(strings['blacklist']['status']['removing'])
        # TODO: Insert logic here
		# fetch the current blacklist
		# split the words if there are more than one(or maybe only allow one at a time)
		# for each word
			#try and remove it from list (use a try statement, catching ValueError)
		# update DB with new list
    elif command == "get":
		# fetch the current blacklist
		# make it nice to look at
		# send a private message with the nice to look at blacklist
        await ctx.send("#TODO")
    else:
        return await ctx.send("""
No subcommand selected - please enter a subcommand for your blacklist.

?blacklist add [word] : Add word to blacklist
?blacklist remove [word] : Remove word from blacklist
?blacklist get : Get PM of current blacklist
            """)

    await msg.edit(content=strings['blacklist']['status']['complete'])


async def build_data_profile(name, member, guild):
    """
    Used for building a data profile based on a user

    Name: name of user
    Member: member object
    Guild: Guild object
    """
    print("Initialising data tracking for " + name)
    for summer_channel in guild.text_channels:
        adding = True
        for x in range(0, len(disabled_groups)):
            if summer_channel.category.name.lower() == disabled_groups[x].lower():
                adding = False
                break

        if adding:
            print(name + " > in > " + summer_channel.name)
            messages_tocheck = await summer_channel.history(limit=50000).flatten()
            print(name + " > processing > " + summer_channel.name)
            for message in messages_tocheck:
                if message.author == member:
                    try:
                        cursor.execute(add_message_custom, (name, int(message.id), str(
                            message.channel.id), message.created_at.strftime('%Y-%m-%d %H:%M:%S'), message.content,))
                    except mysql.connector.errors.DataError:
                        print("Couldn't insert, probs a time issue")
                    except mysql.connector.errors.IntegrityError:
                        pass
            cnx.commit()


async def delete_option(bot, ctx, message, delete_emoji, timeout=60):
    """Utility function that allows for you to add a delete option to the end of a command.
    This makes it easier for users to control the output of commands, esp handy for random output ones."""
    await message.add_reaction(delete_emoji)

    def check(r, u):
        return str(r) == str(delete_emoji) and u == ctx.author and r.message.id == message.id

    try:
        await bot.wait_for("reaction_add", timeout=timeout, check=check)
        await message.remove_reaction(delete_emoji, bot.user)
        await message.remove_reaction(delete_emoji, ctx.author)
        em = discord.Embed(title=str(ctx.message.author) +
                           " deleted message", description="User deleted this message.")

        return await message.edit(embed=em)
    except:
        await message.remove_reaction(delete_emoji, bot.user)
client.run(token)
