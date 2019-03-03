import math
import random

import discord
from discord.ext import commands

from ags_experiments.algorithmia import algo_client
from ags_experiments.client_tools import ClientTools
from ags_experiments.database.database_tools import DatabaseTools
from ags_experiments.settings.config import config, strings
import ags_experiments.colours as colours

class Sentiment(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.client_extras = ClientTools(client)
        self.database_extras = DatabaseTools(self.client_extras)

    @commands.command(aliases=["s"])
    async def sentiment(self, ctx, raw: bool = False, nsfw: bool = False, selected_channel: discord.TextChannel = None):
        """
        Calculate sentiment.json from your messages!
        """
        raw = bool(raw)
        if (not ctx.message.channel.is_nsfw()) and nsfw:
            return await ctx.send(strings['tagger']['errors']['nsfw'].format(str(ctx.author)))

        output = await ctx.send(strings['tagger']['title'] + strings['emojis']['loading'])

        await output.edit(content=output.content + "\n" + strings['tagger']['status']['messages'])
        async with ctx.channel.typing():
            username = self.database_extras.opted_in(user_id=ctx.author.id)
            if not username:
                return await output.edit(content=output.content + strings['tagger']['errors']['not_opted_in'])
            messages, channels = await self.database_extras.get_messages(ctx.author.id, config['limit'] / 10)

            text = []

            text = await self.client_extras.build_messages(ctx, nsfw, messages, channels,
                                                           selected_channel=selected_channel)
            await output.edit(
                content=output.content + strings['emojis']['success'] + "\n" + strings['tagger']['status'][
                    'analytical_data'])
            algo = algo_client.algo('nlp/SocialSentimentAnalysis/0.1.4')
            response = algo.pipe({"sentenceList": text})
            tags = list(response.result)
            await output.delete()
            file = open("sentiment.json", "w")
            file.write(str(tags))
            positive = 0
            negative = 0
            neutral = 0
            compound = 0
            for tag in tags:
                positive += tag['positive']
                negative += tag['negative']
                neutral += tag['neutral']
                compound += tag['compound']

            em = discord.Embed(title="Sentiment", color=colours.blue)
            positive = (math.ceil((positive / len(tags)) * 10000)) / 100
            negative = (math.ceil((negative / len(tags)) * 10000)) / 100
            neutral = (math.ceil((neutral / len(tags)) * 10000)) / 100
            compound = (math.ceil((compound / len(tags)) * 10000)) / 100
            if raw:

                file.close()

                em.add_field(name="Positivity", value=str(positive))
                em.add_field(name="Negativity", value=str(negative))
                em.add_field(name="Neutrality", value=str(neutral), inline=False)
                em.add_field(name = "Flip-floppity-ness", value = str(compound))
                em.add_field(name="Info", value="*Max value for these are 100 points, min are -100 points*",
                             inline=False)
            else:

                positive = math.floor(positive / 2)
                negative = math.floor(negative / 2)
                em.add_field(name="Niceness", value=(":heart:" * positive), inline=False)
                em.add_field(name="Evilness", value=(":smiling_imp:" * math.floor(negative)), inline=False)
                shoe = random.randint(0, 5)
                if shoe == 0:
                    emoji_flip = ":sandal:"
                elif shoe == 1:
                    emoji_flip = ":arrows_counterclockwise:"
                elif shoe == 2:
                    emoji_flip = ":yin_yang:"
                elif shoe == 3:
                    emoji_flip = ":libra:"
                else:
                    emoji_flip = "<a:zthonkspin:399368569500205056>"
                em.add_field(name = "Flip-floppitiness", value = (emoji_flip * math.floor(compound)), inline = False)

            output = await ctx.send(embed=em)
        emoji = await self.client_extras.get_delete_emoji()
        emoji = emoji[1]
        return await self.client_extras.delete_option(self.client, output, ctx, emoji)


def setup(client):
    client.add_cog(Sentiment(client))
