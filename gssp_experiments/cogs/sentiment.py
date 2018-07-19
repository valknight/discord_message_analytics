import math

import discord
from discord.ext import commands

from gssp_experiments.algorithmia import algo_client
from gssp_experiments.client_tools import ClientTools
from gssp_experiments.database.database_tools import DatabaseTools
from gssp_experiments.settings.config import strings, config


class Sentiment():

    def __init__(self, client):
        self.client = client
        self.client_extras = ClientTools(client)
        self.database_extras = DatabaseTools(self.client_extras)

    @commands.command(aliases=["s"])
    async def sentiment(self, ctx, nsfw: bool = False, selected_channel: discord.TextChannel = None):
        """
        Calculate sentiment.json from your messages!
        """
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
            for tag in tags:
                positive += tag['positive']
                negative += tag['negative']
                neutral += tag['neutral']
            positive = (math.ceil((positive / len(tags)) * 10000)) / 100
            negative = (math.ceil((negative / len(tags)) * 10000)) / 100
            neutral = (math.ceil((neutral / len(tags)) * 10000)) / 100

            file.close()

            em = discord.Embed(title="Sentiment")

            em.add_field(name="Positivity", value=str(positive))
            em.add_field(name="Negativity", value=str(negative))
            em.add_field(name="Neutrality", value=str(neutral))
            em.add_field(name="Info", value="*Max value for these are 100 points, min are -100 points*")
            output = await ctx.send(embed=em)
        emoji = await self.client_extras.get_delete_emoji()
        emoji = emoji[1]
        return await self.client_extras.delete_option(self.client, output, ctx, emoji)


def setup(client):
    client.add_cog(Sentiment(client))
