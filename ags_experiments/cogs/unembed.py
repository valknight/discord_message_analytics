import discord
from discord.ext import commands
from discord.errors import DiscordException

import hashlib
import io

from gssp_experiments import colours
from gssp_experiments.client_tools import ClientTools
from gssp_experiments.settings.config import strings, config


class Unembed():

    def __init__(self, client):
        self.client = client
        self.client_tools = ClientTools(client)

    async def process_unembed(self, ctx, description, link_format):
        await ctx.trigger_typing()
        attachments = ctx.message.attachments
        if not attachments:
            return await ctx.send(strings['unembed']['status']['no_attachments'])
        files = []
        # Loop through all attachments, download them, and store that data in a list for re-upload.
        try:
            for attachment in attachments:
                attachment_data = io.BytesIO()
                await attachment.save(attachment_data)
                files.append(discord.File(attachment_data, attachment.filename))
        except DiscordException as e:
            return await self.client_tools.error_embed(ctx, e, message=strings['unembed']['errors']['download'],
                                                       colour=colours.red)
        finally:
            # Attachments are either in memory now or failed to download; original message is no longer needed.
            await ctx.message.delete()
        unembed_channel = self.client.get_channel(config['discord']['unembed_channel'])
        try:
            unembed_message = await unembed_channel.send(hashlib.sha256(str(ctx.author.id).encode()).hexdigest(),
                                                         files=files)
        except DiscordException as e:
            return await self.client_tools.error_embed(ctx, e, message=strings['unembed']['errors']['upload'],
                                                       colour=colours.red)
        output = ""
        for attachment in unembed_message.attachments:
            output += link_format.format(attachment.url) + "\n"  # Trailing newline is stripped, thankfully
        await ctx.send("(" + str(ctx.author) + ") " + description)
        await ctx.send(output)

    @commands.command(aliases=["cw", "deembed"])
    async def unembed(self, ctx, *, description=strings['unembed']['status']['no_message']):
        """
        Un-embed one or more uploaded images.
        :param description: A description of the un-embedded image(s).
        :return:
        """
        await self.process_unembed(ctx, description, "<{}>")

    # Slight convention break by allowing ?cwc but the goal is for this to be fast to type and "_" is not.
    @commands.command(aliases=["cw_c", "cwc", "deembed_code"])
    async def unembed_code(self, ctx, *, description=strings['unembed']['status']['no_message']):
        """
        Un-embed one or more uploaded images, placing the result into code block(s).
        :param description: A description of the un-embedded image(s).
        :return:
        """
        await self.process_unembed(ctx, description, "`<{}>`")


def setup(client):
    client.add_cog(Unembed(client))
