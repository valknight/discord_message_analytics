import discord
from discord.ext import commands

from gssp_experiments.settings import guild_settings
from gssp_experiments.checks import is_owner_or_admin
from gssp_experiments.client_tools import ClientTools
from gssp_experiments.colours import red, green, yellow
from gssp_experiments.database.database_tools import DatabaseTools
from gssp_experiments.settings.guild_settings import get_bad_words


class Flags():
    def __init__(self, client):
        self.client = client
        self.database_tools = DatabaseTools(client)
        self.client_tools = ClientTools(client)

    @is_owner_or_admin()
    @commands.command(aliases=["flags", "getflags", "slurs", "get_slurs", "getslurs"])
    async def get_flags(self, ctx):
        """Get the global flag list"""
        flags = get_bad_words(guild=ctx.guild)
        em = discord.Embed(title="Flag trigger list", description="")
        for word in flags['words']:
            em.description = em.description + "- {}\n".format(word)
        if len(flags['words']) == 0:
            em.description = "You have not configured a flag list for guild {}".format(ctx.guild.name)
        await ctx.author.send(embed=em)
        await ctx.channel.send(
            embed=discord.Embed(title="Success", description=":e_mail: Sent to your DMs!", color=green))

    @is_owner_or_admin()
    @commands.command(aliases=["addflag", "add_slur", "addslur"])
    async def add_flag(self, ctx, flag):
        """Add a flag to the global flag list"""
        await ctx.message.delete()
        flags = get_bad_words(guild=ctx.guild)

        flags['words'].append(flag.lower())

        guild_settings.write_bad_words(flags)

        color = green
        description = "Added flag"
        if flags['alert_channel'] is None:
            color = yellow
            description = description + ", but you have no channel configured to send notifications to"
        description = description + "."
        await ctx.channel.send(embed=discord.Embed(title="Success", description=description, color=color))

    @is_owner_or_admin()
    @commands.command(aliases=["removeflag", "remove_slur", "removeslur"])
    async def remove_flag(self, ctx, flag):
        """Remove a flag from the global flag list"""
        await ctx.message.delete()
        flags = get_bad_words(guild=ctx.guild)

        if flag.lower() in flags['words']:
            flags['words'].remove(flag.lower())
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
    @is_owner_or_admin()
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
