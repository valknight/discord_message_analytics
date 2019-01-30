import discord
import re
from discord.ext import commands

from gssp_experiments.settings import guild_settings
from gssp_experiments.checks import is_server_allowed
from gssp_experiments.client_tools import ClientTools
from gssp_experiments.colours import red, green, yellow
from gssp_experiments.database.database_tools import DatabaseTools
from gssp_experiments.settings.guild_settings import get_bad_words


class Flags():
    def __init__(self, client):
        self.client = client
        self.database_tools = DatabaseTools(client)
        self.client_tools = ClientTools(client)

    @is_server_allowed()
    @commands.command(aliases=["flags", "getflags", "slurs", "get_slurs", "getslurs"])
    async def get_flags(self, ctx):
        """Get the global flag list"""
        flags = get_bad_words(guild=ctx.guild)
        em = discord.Embed(title="Flag trigger list", description="")
        for word in flags['words']:
            em.description = em.description + "- {}\n".format(word)
        for word in flags.get('regex'):
            em.description = em.description + "- {}\n".format(word)
        if em.description == "":
            em.description = "You have not configured a flag list for guild {}".format(ctx.guild.name)
        await ctx.author.send(embed=em)
        await ctx.channel.send(
            embed=discord.Embed(title="Success", description=":e_mail: Sent to your DMs!", color=green))

    @is_server_allowed()
    @commands.command(aliases=["addflag", "add_slur", "addslur"])
    async def add_flag(self, ctx, flag, regex=False):
        """Add a flag to the global flag list"""
        flags = get_bad_words(guild=ctx.guild)
        if regex:
            if flags.get('regex') is None:
                flags['regex'] = []
            try:
                re.compile(flag)
            except:
                return await ctx.channel.send(embed=discord.Embed(title="Error", description="Your regex failed to validate", color=red))
            flags['regex'].append(flag)
        else:
            flags['words'].append(flag.lower())

        guild_settings.write_bad_words(flags)

        color = green
        description = "Added flag"
        if flags['alert_channel'] is None:
            color = yellow
            description = description + ", but you have no channel configured to send notifications to"
        description = description + "."
        await ctx.channel.send(embed=discord.Embed(title="Success", description=description, color=color))

    @is_server_allowed()
    @commands.command(aliases=["removeflag", "remove_slur", "removeslur"])
    async def remove_flag(self, ctx, flag):
        """Remove a flag from the global flag list"""
        flags = get_bad_words(guild=ctx.guild)
        flags['regex'] = flags.get('regex')
        if flags['regex'] is None:
            flags['regex'] = []
        if flag.lower() in flags['words']:
            flags['words'].remove(flag.lower())
        elif flag in flags['regex']:
            flags['regex'].remove(flag)
        else:
            return await ctx.channel.send(
                embed=discord.Embed(title="Error", description="Flag does not exist", color=red))
        guild_settings.write_bad_words(flags)
        color = green
        description = "Removed flag"
        if flags['alert_channel'] is None:
            color = yellow
            description = description + ", but you have no channel configured to send notifications to"
        description = description + "."
        await ctx.channel.send(embed=discord.Embed(title="Success", description=description, color=color))
    @is_server_allowed()
    @commands.command(aliases=['flagchannel', 'slurchannel', 'slur_channel'])
    async def flag_channel(self, ctx):
        """
        Set the channel the command is ran in to recieve warnings about usage of flags
        """
        flags = get_bad_words(guild=ctx.guild)
        flags['alert_channel'] = ctx.channel.id
        guild_settings.write_bad_words(flags)
        await ctx.send(embed=discord.Embed(title="Success", description="Set current channel to recieve flag warnings in future", color=green))

def setup(client):
    client.add_cog(Flags(client))
