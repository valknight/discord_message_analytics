import discord
import markovify
from discord.ext import commands

from ags_experiments.client_tools import ClientTools
import ags_experiments.colours as colours
from ags_experiments.database.database_tools import DatabaseTools
from ags_experiments.settings.config import strings, config


class Markov(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.database_tools = DatabaseTools(client)
        self.client_tools = ClientTools(client)

    @commands.command(aliases=["m_s"])
    async def markov_server(self, ctx, nsfw: bool = False, selected_channel: discord.TextChannel = None):
        """
        Generates markov output based on entire server's messages.
        """
        nsfw_mismatch = False
        if selected_channel is not None:
            if selected_channel.is_nsfw() and not nsfw:
                nsfw_mismatch = True
            elif not selected_channel.is_nsfw() and nsfw:
                nsfw_mismatch = True
        if nsfw_mismatch:
            return await ctx.send(embed=discord.Embed(title="Error", description="The selected channel and the NSFW flag do not match. Please ensure these are both correct.", color=colours.red))
        output = await ctx.send(strings['markov']['title'] + strings['emojis']['loading'])
        await output.edit(content=output.content + "\n" + strings['markov']['status']['messages'])
        async with ctx.channel.typing():
            text = []
            messages, channels = await self.database_tools.get_messages(ctx.author.id, config['limit_server'],
                                                                        server=True)
            text = await self.client_tools.build_messages(ctx, nsfw, messages, channels,
                                                          selected_channel=selected_channel)

            text1 = ""
            for m in text:
                text1 += str(m) + "\n"
            if len(text) < 10:
                return await output.edit(content=output.content + strings['markov']['errors']['low_activity'])
            try:
                await output.edit(
                    content=output.content + strings['emojis']['success'] + "\n" + strings['markov']['status'][
                        'building_markov'])
                # text_model = POSifiedText(text)
                text_model = markovify.NewlineText(text, state_size=config['state_size'])
            except KeyError:
                return ctx.send('Not enough data yet, sorry!')
            await output.edit(
                content=output.content + strings['emojis']['success'] + "\n" + strings['markov']['status']['making'])
            text = text_model.make_short_sentence(140)
            attempt = 0
            while (True):
                attempt += 1
                if attempt >= 10:
                    return await ctx.send(strings['markov']['errors']['failed_to_generate'])
                message_formatted = str(text)
                if message_formatted != "None":
                    break

            await output.delete()
            em = await self.client_tools.markov_embed(strings['markov']['output']['title_server'], message_formatted)
            output = await ctx.send(embed=em)
        return await self.client_tools.delete_option(self.client, output, ctx,
                                                     self.client.get_emoji(int(strings['emojis']['delete'])) or "❌")

    @commands.command(aliases=["m"])
    async def markov(self, ctx, nsfw: bool = False, selected_channel: discord.TextChannel = None):
        """
        Generates markov output for user who ran this command
        """
        if (not ctx.message.channel.is_nsfw()) and nsfw:
            return await ctx.send(strings['markov']['errors']['nsfw'].format(str(ctx.author)))

        output = await ctx.send(strings['markov']['title'] + strings['emojis']['loading'])

        await output.edit(content=output.content + "\n" + strings['markov']['status']['messages'])
        async with ctx.channel.typing():
            username = self.database_tools.opted_in(user_id=ctx.author.id)
            if not username:
                return await output.edit(content=output.content + strings['markov']['errors']['not_opted_in'])
            messages, channels = await self.database_tools.get_messages(ctx.author.id, config['limit'])

            text = []

            text = await self.client_tools.build_messages(ctx, nsfw, messages, channels,
                                                          selected_channel=selected_channel)

            text1 = ""
            for m in text:
                text1 += str(m) + "\n"

            try:
                await output.edit(
                    content=output.content + strings['emojis']['success'] + "\n" + strings['markov']['status'][
                        'building_markov'])
                # text_model = POSifiedText(text)
                text_model = markovify.NewlineText(text, state_size=config['state_size'])
            except KeyError:
                return ctx.send('Not enough data yet, sorry!')

            attempt = 0
            while (True):
                attempt += 1
                if attempt >= 10:
                    await output.delete()
                    return await ctx.send(strings['markov']['errors']['failed_to_generate'])
                new_sentance = text_model.make_short_sentence(140)
                message_formatted = str(new_sentance)
                if message_formatted != "None":
                    break

            await output.edit(
                content=output.content + strings['emojis']['success'] + "\n" + strings['markov']['status'][
                    'analytical_data'])
            await self.database_tools.save_markov(text_model, ctx.author.id)

            await output.edit(
                content=output.content + strings['emojis']['success'] + "\n" + strings['markov']['status']['making'])
            await output.delete()

            em = await self.client_tools.markov_embed(str(ctx.author), message_formatted)
            output = await ctx.send(embed=em)
        return await self.client_tools.delete_option(self.client, output, ctx,
                                                     self.client.get_emoji(int(strings['emojis']['delete'])) or "❌")


def setup(client):
    client.add_cog(Markov(client))
