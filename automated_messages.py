import sys
import concurrent

import discord
import markovify
import time
from discord.ext import commands
from discord import Embed
from ags_experiments.client_tools import ClientTools
from ags_experiments.database import cnx
from ags_experiments.database.database_tools import DatabaseTools
from ags_experiments.settings.config import config, strings

client = commands.Bot(command_prefix="--------------------",
                      owner_id=config['discord']['owner_id'])
client_tools = ClientTools(client)
database_tools = DatabaseTools(client)

print("Awaiting login")

position = 0
opted_in_users = []
channel = None
server = None

async def get_members(server, message=None):
    members = []
    for user in server.members:
        if database_tools.is_automated(user):
            print(user)
            members.append(user)
            if message is not None:
                await message.edit(content="Initialising - found {count} users".format(count=len(members)))
    return members


async def main():
    global opted_in_users
    global position
    global server
    global channel
    error_count = 0
    while True:
        try:
            for x in range(position, len(opted_in_users)):
                position = x
                user = opted_in_users[x]
                messages, channels = await database_tools.get_messages(user.id, config['limit'])
                cnx.commit()
                text_full = ""

                for x in range(0, len(messages)):
                    channel_temp = client.get_channel(int(channels[x]))
                    if not channel_temp.is_nsfw():
                        text_full = text_full + messages[x] + "\n"
                try:
                    text_model = markovify.NewlineText(
                        text_full, state_size=config['state_size'])
                    em = discord.Embed(
                        title=user.display_name, description=text_model.make_short_sentence(140))
                    em.set_thumbnail(url=user.avatar_url)
                    name = await client_tools.get_delete_emoji()
                    name = name[0]
                    em.set_footer(
                        text=strings['markov']['output']['footer'].format(name))
                    output = await channel.send(embed=em)
                    time.sleep(1)
                    async for message in channel.history(limit=1, reverse=True):
                        message = message
                        break
                    await delete_option(client, message, channel, client.get_emoji(int(strings['emojis']['delete'])) or "❌")
                except KeyError:
                    pass
            opted_in_users = await get_members(server)
            error_count = 0
            position = 0 # this means that, we don't continue from the *end*
        except Exception as e:
            error_count += 1
            print(e)
            if error_count > 3:
                sys.exit(1)


@client.event
async def on_ready():
    global server
    global channel
    found = False
    for server_1 in client.guilds:
        for channel_1 in server_1.channels:
            if channel_1.id == config['discord']['automated_channel']:
                found = True
                break
        if found:
            server = server_1
            channel = channel_1
            break
        print("Not found")
    if not found:
        print("Failed to find channel. Check your config")
        sys.exit(1)
    # initial propogation of users
    message = await channel.send("Starting message loop")
    global opted_in_users
    opted_in_users = await get_members(server, message=message)
    await message.delete()
    await main()


async def delete_option(bot, message, channel, delete_emoji, timeout=config['discord']['delete_timeout'] / 2):
    """Utility function that allows for you to add a delete option to the end of a command.
    This makes it easier for users to control the output of commands, esp handy for random output ones."""
    await message.add_reaction(delete_emoji)

    def check(r, u):
        return str(r) == str(delete_emoji) and r.message.id == message.id

    try:
        await bot.wait_for("reaction_add", timeout=timeout, check=check)
        await bot.wait_for("reaction_add", timeout=timeout, check=check)
        await message.delete()
        em = Embed(title="Message deleted.")
        return await channel.send(embed=em)
    except concurrent.futures._base.TimeoutError:
        try:
            await message.remove_reaction(delete_emoji, bot.user)
        except discord.errors.NotFound:
            pass


if __name__ == "__main__":
    client.run(config['discord']['token'])
