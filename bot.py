import datetime
import discord
from discord.ext import commands
import json
import markovify
import math
import mysql.connector
import re
import time
import sys
import concurrent
from config import config, strings

client = commands.Bot(command_prefix=config['discord']['prefix'], owner_id=config['discord']['owner_id'])

token = config['discord']['token']
__version__ = "0.3"

if config['version']!=__version__:
    if config['version_check']:
        print(strings['config_invalid'].format(__version__, str(config['version'])))
        sys.exit(1)
    else:
        print(strings['config_invalid_ignored'].format(__version__, str(config['version'])))

disabled_groups = config['discord']['disabled_groups']

add_message = ("INSERT INTO messages (id, channel, time) VALUES (%s, %s, %s)")
add_message_custom = "INSERT INTO `%s` (id, channel_id, time, contents) VALUES (%s, %s, %s, %s)"

cnx = mysql.connector.connect(**config['mysql'])
cursor = cnx.cursor()

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
    members = []
    for server in client.guilds:
        for member in server.members:
            name = opted_in(user_id=member.id)
            if name is not False:
                members.append(member)
    
    await build_data_profile(members, limit=None)


@client.event
async def on_message(message):
    # this set of code in on_message is used to save incoming new messages
    channel = message.channel
    user_exp = opted_in(user_id=message.author.id)

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
    try:
        if message.content[len(config['discord']['prefix'])] == config['discord']['prefix']:#if its double(or more) prefixed then it cant be a command (?word is a command, ????? is not)
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
async def thonkang(cnx):
    await cnx.message.delete()
    await   cnx.send(strings['emojis']['loading'])

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

    await channel.send(strings['data_collection']['data_track_start'])

    await build_data_profile([author])
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


def opted_in(user=None, user_id=None):
    """
    ID takes priority over user if provided

    User: Logged username in DB
    ID: ID of user

    Returns true if user is opted in, false if not
    """
    if user_id is None:
        get_user = "SELECT `opted_in`, `username` FROM `users` WHERE  `username`=%s;"
    else:
        get_user = "SELECT `opted_in`, `username` FROM `users` WHERE  `user_id`=%s;"
        user = user_id

    cursor.execute(get_user, (user, ))
    results = cursor.fetchall()
    try:
        if results[0][0] != 1:
            return False
    except IndexError:
        return False
    return results[0][1]


async def get_messages(user_id, limit: int):
    """
    user_id : ID of user you want to get messages for

    Returns:

    messages: list of all messages from a user
    channels: list of all channels relevant to messages, in same order
    """
    username = opted_in(user_id=user_id)
    get_messages = "SELECT `contents`, `channel_id` FROM `%s` ORDER BY TIME DESC LIMIT " + str(int(limit))
    cursor.execute(get_messages, (username, ))
    results = cursor.fetchall()
    messages = []
    channels = []
    blocklist = await get_blocklist(user_id)
    for result in results:
        valid = True
        for word in result[0].split(" "):
            if word in blocklist:
                valid = False
        if valid:
            messages.append(result[0])
            channels.append(result[1])

    return messages, channels


def channel_allowed(channel_id, existing_channel, nsfw=False):
    """
    Check if a channel is allowed in current context

    channel_id: ID of channel
    existing_channel: channel object of existing channel
    nsfw: whether to only return NSFW channels
    """
    channel = client.get_channel(int(channel_id))

    for group in disabled_groups:
        if str(channel.category).lower() == str(group).lower():
            return False

    if not existing_channel.is_nsfw() and bool(nsfw):
        return False

    if channel.is_nsfw():
        return bool(nsfw) # checks if user wants / is allowed explicit markovs
        # this means that if the channel *is* NSFW, we return True, but if it isn't, we return False
    else: # channel is SFW
        if bool(nsfw):
            return False # this stops SFW chats from being included in NSFW markovs

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


async def build_messages(ctx, nsfw, messages, channels, selected_channel=None):
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

        if channel_allowed(channels[counter], ctx.message.channel, nsfw):
            if selected_channel is not None:
                if client.get_channel(int(channels[counter])).id == selected_channel.id:
                    text.append(m)
            else:
                text.append(m)
    return text


async def get_delete_emoji():
    delete_emoji = client.get_emoji(int(strings['emojis']['delete']))
    if delete_emoji is not None:
        emoji_name = delete_emoji.name
    else:
        emoji_name = "❌"
    return emoji_name


async def markov_embed(title, message):
    em = discord.Embed(title=title, description=message)
    name = await get_delete_emoji()
    em.set_footer(text=strings['markov']['output']['footer'].format(name))
    return em


@client.command(aliases=["m_s"])
async def markov_server(ctx, nsfw: bool=False, selected_channel: discord.TextChannel=None):
    """
    Generates markov output based on entire server's messages.
    """
    output = await ctx.send(strings['markov']['title'] + strings['emojis']['loading'])

    await output.edit(content=output.content + "\n" + strings['markov']['status']['messages'])
    async with ctx.channel.typing():
        text = []

        print(selected_channel)
        for server in client.guilds:
            for member in server.members:
                if opted_in(user_id=member.id) is not False:
                    messages, channels = await get_messages(member.id, config['limit_server'])
                    text_temp = await build_messages(ctx, nsfw, messages, channels, selected_channel=selected_channel)
                    for m in text_temp:
                        text.append(m)

        text1 = ""
        for m in text:
            text1 += str(m) + "\n"

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

        await output.delete()
        em = await markov_embed(strings['markov']['output']['title_server'], message_formatted)
        output = await ctx.send(embed=em)
    return await delete_option(client, ctx, output, client.get_emoji(int(strings['emojis']['delete'])) or "❌")


@client.command(aliases=["m"])
async def markov(ctx, nsfw: bool=False, selected_channel: discord.TextChannel=None):
    """
    Generates markov output for user who ran this command
    """
    if (not ctx.message.channel.is_nsfw()) and nsfw:
        return await ctx.send(strings['markov']['errors']['nsfw'].format(str(ctx.author)))

    output = await ctx.send(strings['markov']['title'] + strings['emojis']['loading'])

    await output.edit(content=output.content + "\n" + strings['markov']['status']['messages'])
    async with ctx.channel.typing():
        username = opted_in(user_id=ctx.author.id)
        if not username:
            return await output.edit(content=output.content + strings['markov']['errors']['not_opted_in'])
        messages, channels = await get_messages(ctx.author.id, config['limit'])

        text = []

        text = await build_messages(ctx, nsfw, messages, channels, selected_channel=selected_channel)

        text1 = ""
        for m in text:
            text1 += str(m) + "\n"

        try:
            await output.edit(content=output.content + strings['emojis']['success'] + "\n" + strings['markov']['status']['building_markov'])
            # text_model = POSifiedText(text)
            text_model = markovify.NewlineText(text, state_size=3)
        except KeyError:
            return ctx.send('Not enough data yet, sorry!')

        attempt = 0
        while(True):
            attempt += 1
            if attempt >= 10:
                await output.delete()
                return await ctx.send(strings['markov']['errors']['failed_to_generate'])
            new_sentance = text_model.make_short_sentence(140)
            message_formatted = str(new_sentance)
            if message_formatted != "None":
                break

        await output.edit(content=output.content + strings['emojis']['success'] + "\n" + strings['markov']['status']['analytical_data'])
        await save_markov(text_model, ctx.author.id)

        await output.edit(content=output.content + strings['emojis']['success'] + "\n" + strings['markov']['status']['making'])
        await output.delete()

        em = await markov_embed(str(ctx.author), message_formatted)
        output = await ctx.send(embed=em)
    return await delete_option(client, ctx, output, client.get_emoji(int(strings['emojis']['delete'])) or "❌")

@commands.is_owner()
@client.command()
async def send_emoji(ctx, name, id):
    await ctx.message.delete()
    await ctx.send(strings['emojis']['animated_emoji_template'].format(name, int(id)))


async def get_blocklist(user_id):
    user_id = str(user_id)
    get = "SELECT blocklist FROM blocklists WHERE user_id = %s"
    cursor.execute(get, (user_id, ))
    resultset = cursor.fetchall()
    if not resultset:
        #add a blank blocklist
        create_user = "INSERT INTO blocklists (user_id, blocklist) VALUES (%s, '[]')"
        cursor.execute(create_user, (user_id, ))
        return []
    return json.loads(resultset[0][0])


@client.command()
async def blocklist(ctx, command=None, word=None):
    """
    Prevents words from being shown publicly through methods such as markov and markov_server.
    Note: they will still be logged, and this just prevents them being shown in chat.

    Command: option to use
    Word: Word to add or remove from blocklist
    """
    await ctx.message.delete()
    if command is None:
        return await ctx.send("""
    No subcommand selected - please enter a subcommand for your blocklist.

    ?blocklist add [word] : Add word to blocklist
    ?blocklist remove [word] : Remove word from blocklist
    ?blocklist get : Get PM of current blocklist
            """)
    #fetch current blocklist
    blockL = await get_blocklist(ctx.author.id)
    update_blocklist = "UPDATE blocklists SET blocklist = %s WHERE user_id = %s"

    if command == "add":
        if word is None:
            return await ctx.send(strings['blocklist']['status']['no_word'], delete_after=config['discord']['delete_timeout'])
        msg = await ctx.send(strings['blocklist']['status']['adding'])

        #check if the word is already on the list. throw error if it is
        if word != blockL:
            # if its not then add it
            blockL.append(word)
            # update DB with new list
            new_json = json.dumps(blockL)
            cursor.execute(update_blocklist, (new_json, ctx.author.id, ))
        else:
            await ctx.send(strings['blocklist']['status']['exist'])

    elif command == "remove":
        if word is None:
            return await ctx.send(strings['blocklist']['status']['no_word'], delete_after=config['discord']['delete_timeout'])
        msg = await ctx.send(strings['blocklist']['status']['removing'])

        #try and remove it from list (use a try statement, catching ValueError)
        try:
            blockL.remove(word)
        except ValueError:
            return await ctx.send(strings['blocklist']['status']['not_exist'], delete_after=config['discord']['delete_timeout'])

        # update DB with new list
        new_json = json.dumps(blockL)
        cursor.execute(update_blocklist, (new_json, ctx.author.id, ))

    elif command == "get":
        # make it nice to look at
        if blockL == []:
            msg = strings['blocklist']['status']['empty']
        else:
            msg = strings['blocklist']['status']['list']
            for item in blockL:
                part = ' ' + item + ','#done so that the merge with the long string is only done once per word
                msg += part
            msg = msg[:-1]#trim off the trailing ,
        # send a private message with the nice to look at blocklist
        await ctx.author.send(msg)
        msg = await ctx.send(strings['blocklist']['status']['complete'], delete_after=config['discord']['delete_timeout'])
    else:
        return await ctx.send("""
No subcommand selected - please enter a subcommand for your blocklist.

?blocklist add [word] : Add word to blocklist
?blocklist remove [word] : Remove word from blocklist
?blocklist get : Get PM of current blocklist
            """)

    await msg.edit(content=strings['blocklist']['status']['complete'])


async def build_data_profile(members, limit=50000):
    """
    Used for building a data profile based on a user

    Members: list of members we want to import for
    Guild: Guild object
    Limit: limit of messages to be imported
    """
    for guild in client.guilds:
        print("Starting guild {}".format(guild.name))
        for summer_channel in guild.text_channels:
            adding = True
            for group in disabled_groups:
                try:
                    if summer_channel.category.name.lower() == group.lower():
                        adding = False
                        break
                except AttributeError:
                    adding = False
            if adding:
                counter = 0
                already_added = 0
                print("{} scraping for {} users".format(summer_channel.name, len(members)))
                async for message in summer_channel.history(limit=limit, reverse=True):
                    if message.author in members:
                        name = opted_in(user_id=message.author.id)
                        try:
                            cursor.execute(add_message_custom, (name, int(message.id), str(message.channel.id), message.created_at.strftime('%Y-%m-%d %H:%M:%S'), message.content,))
                            counter += 1
                        except mysql.connector.errors.DataError:
                            print("Couldn't insert, probs a time issue")
                        except mysql.connector.errors.IntegrityError:
                            already_added += 1
                print("{} scraped for {} users - added {} messages, found {} already added".format(summer_channel.name, len(members), counter, already_added))
                cnx.commit()
        print("Completed guild {}".format(guild.name))
async def delete_option(bot, ctx, message, delete_emoji, timeout=config['discord']['delete_timeout']):
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
    except concurrent.futures._base.TimeoutError:
        await message.remove_reaction(delete_emoji, bot.user)

async def get_times(username):
    """
    username : user you want to get messages for

    Returns:

    times: list of all timestamps of users messages
    """


    get_times = "SELECT `time` FROM `%s` ORDER BY TIME ASC"
    cursor.execute(get_times, (username, ))
    timesA = cursor.fetchall()
    times = []
    for time in timesA:
        times.append(time[0])
    return times

@client.command()
async def nyoom(ctx, user: discord.Member=None):
    """
    Calculated the specified users nyoom metric.
    e.g. The number of messages per hour they post while active (posts within 10mins of each other count as active)

    user : user to get nyoom metric for, if not author
    """
    if user is None:
        user = ctx.message.author

    output = await ctx.send(strings['nyoom_calc']['status']['calculating'])
    username = opted_in(user_id=user.id)
    # load interval between messages we're using from the configs
    interval = config['discord']['nyoom_interval']
    if not username:
        return await output.edit(content=output.content + '\n' + strings['nyoom_calc']['status']['not_opted_in'])
    # grab a list of times that user has posted
    times = await get_times(username)
    # group them into periods of activity
    periods = []
    curPeriod = [times[0],times[0],0] # begining of period, end of period, number of messages in period
    for time in times:
        if time > curPeriod[1] + datetime.timedelta(0,interval): # if theres more than a 10min dif between this time and last time
            #make a new period
            periods.append(curPeriod)
            curPeriod = [time,time,1]
        else:
            curPeriod[1] = time#the period now ends with the most recent timestamp
            curPeriod[2] += 1#add the message to the period
    #sum the total length of activity periods and divide by total number of messages
    totalT = 0
    totalM = 0
    for period in periods:
        totalM += period[2] #sum all the number of messages [can probs be done with len(times)]
        totalT += ((period[1]-period[0]).total_seconds()/60) +1 # total number of minutes for the activity period, plus a fudge factor to prevent single message periods from causing a divide by zero issue later
    totalT /= 60 # makes the total active time and nyoom_metric count hours of activity rather than minutes
    nyoom_metric = totalM / totalT#number of message per minute during periods of activity
    #print the nyoom metric
    return await output.edit(content=strings['nyoom_calc']['status']['finished'].format(username,totalM,totalT,nyoom_metric))

if __name__=="__main__":
    client.run(token)
