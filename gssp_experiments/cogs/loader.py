import subprocess
import sys
import traceback

import discord
from discord.ext import commands

from gssp_experiments.checks import is_owner_or_admin
from gssp_experiments.client_tools import ClientTools
from gssp_experiments.colours import green, red
from gssp_experiments.settings.config import config, strings
from gssp_experiments.logger import logger
startup_extensions = [
    "gssp_experiments.cogs.admin",
    "gssp_experiments.cogs.controls",
    "gssp_experiments.cogs.markov",
    "gssp_experiments.cogs.sentiment",
    "gssp_experiments.cogs.slurs",
    "gssp_experiments.cogs.nyoom",
    "gssp_experiments.cogs.tagger",
    "gssp_experiments.cogs.fun",
    "gssp_experiments.cogs.ping",
    "gssp_experiments.cogs.unembed"
]


class Loader():
    """
    This short cog is just intended to be a loader for other cogs.
    Don't add to this unless you have to, as this is designed to be minimal so to prevent breaking all cogs
    """

    def __init__(self, client):
        # self.automated = subprocess.Popen(
        #    [sys.executable, "automated_messages.py"])
        self.client = client
        self.client_tools = ClientTools(client)
        # we look for ".admin" and then add "." to prevent matching a root directory ending in admin
        path = __name__.replace(".admin", "") + "."
        for extension in startup_extensions:
            try:
                client.load_extension(extension)
                logger.info("Loaded {}".format(extension.replace(path, "")))
            except Exception as e:
                exc = '{}: {}'.format(type(e).__name__, e)
                logger.error(
                    'Failed to load extension {}\n{}\n{}'.format(extension, exc, traceback.format_exc()))

    @commands.is_owner()
    @commands.command()
    async def unload(self, ctx, extension_name: str):
        """Unloads an extension."""
        self.client.unload_extension(extension_name)
        await ctx.send("{} unloaded.".format(extension_name))

    @commands.is_owner()
    @commands.command()
    async def load(self, ctx, extension_name: str):
        """Loads an extension. """
        self.client.load_extension(extension_name)
        await ctx.send("{} loaded.".format(extension_name))

    @is_owner_or_admin()
    @commands.command()
    async def reload(self, ctx):
        """Reload all existing cogs"""
        startup_extensions_temp = startup_extensions
        startup_extensions_temp.insert(0, "gssp_experiments.cogs.loader")

        em = discord.Embed(title="Reloading - please wait", color=red)
        output = await ctx.send(embed=em)

        for cog in startup_extensions_temp:
            self.client.unload_extension(cog)
            self.client.load_extension(cog)

        em = discord.Embed(title="Finished!", colour=green)
        await output.edit(embed=em)


def setup(client):
    client.add_cog(Loader(client))
