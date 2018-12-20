import concurrent

import discord
import markovify
import time
from discord.ext import commands

from gssp_experiments.client_tools import ClientTools
from gssp_experiments.database import cnx
from gssp_experiments.database.database_tools import DatabaseTools
from gssp_experiments.settings.config import config, strings

client = commands.Bot(command_prefix="--------------------", owner_id=config['discord']['owner_id'])
client_tools = ClientTools(client)
database_tools = DatabaseTools(client)


@client.event
async def on_ready():
    print("[ Automated bot connected. ]")
    found = False
    for server in client.guilds:
        for channel in server.channels:
            if channel.id == config['discord']['automated_channel']:
                found = True
                break
        if found:
            break

    while True:
        opted_in_users = []
        for user in server.members:
            if database_tools.is_automated(user):
                opted_in_users.append(user)
        for user in opted_in_users:
            messages, channels = await database_tools.get_messages(user.id, config['limit'])
            cnx.commit()
            text_full = ""

            for x in range(0, len(messages)):
                channel_temp = client.get_channel(int(channels[x]))
                if not channel_temp.is_nsfw():
                    text_full = text_full + messages[x] + "\n"
            try:
                text_model = markovify.NewlineText(text_full, state_size=config['state_size'])
                em = discord.Embed(title=user.display_name, description=text_model.make_short_sentence(140))
                em.set_thumbnail(url=user.avatar_url)
                name = await client_tools.get_delete_emoji()
                name = name[0]
                em.set_footer(text=strings['markov']['output']['footer'].format(name))
                output = await channel.send(embed=em)
                time.sleep(1)
                async for message in channel.history(limit=1, reverse=True):
                    message = message
                    break
                await delete_option(client, message, channel, client.get_emoji(int(strings['emojis']['delete'])) or "❌")
            except KeyError:
                pass


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
