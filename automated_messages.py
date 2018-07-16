import concurrent
import time

import discord
import markovify
from discord.ext import commands

from bot import cnx, get_messages, get_delete_emoji, delete_option, is_automated
from config import config, strings

client = commands.Bot(command_prefix="--------------------", owner_id=config['discord']['owner_id'])


@client.event
async def on_ready():
    print("Connected.")
    found = False
    for server in client.guilds:
        for channel in server.channels:
            if channel.id == config['discord']['automated_channel']:
                found = True
                await channel.send("Channel found!")
                webhook = await channel.create_webhook(name="Announcer")
                await webhook.delete()
                break
        if found:
            break

    while True:
        opted_in_users = []
        for user in server.members:
            if is_automated(user):
                opted_in_users.append(user)
        for user in opted_in_users:
            output = await channel.send("Generating message for " + user.display_name)
            webhook = await channel.create_webhook(name=user.display_name)
            messages, channels = await get_messages(user.id, config['limit'])
            cnx.commit()
            text_full = ""

            for x in range(0, len(messages)):
                channel_temp = client.get_channel(int(channels[x]))
                if not channel_temp.is_nsfw():
                    text_full = text_full + messages[x] + "\n"
            try:
                text_model = markovify.NewlineText(text_full, state_size=config['state_size'])
                em = discord.Embed(description=text_model.make_short_sentence(140))
                name = await get_delete_emoji()
                name = name[0]
                em.set_footer(text=strings['markov']['output']['footer'].format(name))
                await output.delete()
                output = await webhook.send(embed=em, avatar_url=user.avatar_url)
                await webhook.delete()
                time.sleep(1)
                async for message in channel.history(limit=1, reverse=True):
                    message = message
                    break
                await delete_option(client, message, channel, client.get_emoji(int(strings['emojis']['delete'])) or "❌")
            except KeyError:
                await output.delete()
                await channel.send("Could not create markov for " + user.display_name)



async def delete_option(bot, message, channel, delete_emoji, timeout=config['discord']['delete_timeout']):
    """Utility function that allows for you to add a delete option to the end of a command.
    This makes it easier for users to control the output of commands, esp handy for random output ones."""
    await message.add_reaction(delete_emoji)

    def check(r, u):
        return str(r) == str(delete_emoji) and r.message.id == message.id

    try:
        await bot.wait_for("reaction_add", timeout=timeout, check=check)
        await bot.wait_for("reaction_add", timeout=timeout, check=check)
        await message.delete()
        return await channel.send("Message deleted.")
    except concurrent.futures._base.TimeoutError:
        await message.remove_reaction(delete_emoji, bot.user)


if __name__ == "__main__":
    client.run(config['discord']['token'])
