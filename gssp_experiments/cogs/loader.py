import subprocess
import sys
import traceback

import discord
from discord.ext import commands

from gssp_experiments.checks import is_owner_or_admin
from gssp_experiments.client_tools import ClientTools
from gssp_experiments.colours import green, red, blue
from gssp_experiments.settings.config import config, strings
from gssp_experiments.logger import logger
startup_extensions = [
    "admin",
    "controls",
    "markov",
    "sentiment",
    "slurs",
    "nyoom",
    "tagger",
    "fun",
    "ping",
    "unembed"
]


class Loader():
    """
    This short cog is just intended to be a loader for other cogs.
    Don't add to this unless you have to, as this is designed to be minimal so to prevent breaking all cogs
    """

    def get_path(self):
        return __name__.replace(".loader", "")

    def strip_path(self, extension_name):
        path = self.get_path() + "."
        return extension_name.replace(path, "")

    def __init__(self, client):
        # self.automated = subprocess.Popen(
        #    [sys.executable, "automated_messages.py"])
        self.client = client
        self.client_tools = ClientTools(client)
        # we look for ".admin" and then add "." to prevent matching a root directory ending in admin
        for extension in startup_extensions:
            try:
                to_load = "{}.{}".format(self.get_path(), extension)
                client.load_extension(to_load)
                del(to_load)
                logger.info("Loaded {}".format(extension))
            except Exception as e:
                exc = '{}: {}'.format(type(e).__name__, e)
                logger.error(
                    'Failed to load extension {}\n{}\n{}'.format(extension, exc, traceback.format_exc()))

    @commands.is_owner()
    @commands.command(aliases=["un_load"])
    async def unload(self, ctx, extension_name: str):
        """Unloads an extension."""
        to_unload = "{}.{}".format(self.get_path(), extension_name)
        self.client.unload_extension(to_unload)
        del(to_unload)
        unloaded = False
        em = discord.Embed(title="{} was already unloaded".format(
            extension_name), color=red)
        try:
            while True:  # this loop exists as sometimes we may get idiot users load the same cog twice
                startup_extensions.remove(extension_name)
                unloaded = True
        except ValueError:
            pass
        if unloaded:
            em = discord.Embed(title="{} unloaded".format(
                extension_name), color=green)
        await ctx.send(embed=em)

    @commands.is_owner()
    @commands.command()
    async def load(self, ctx, extension_name: str):
        """Loads an extension. """
        self.client.load_extension(self.get_path() + "." + extension_name)
        startup_extensions.append(extension_name)
        await ctx.send("{} loaded.".format(extension_name))

    @is_owner_or_admin()
    @commands.command(aliases=["get_loaded", "getloadedextensions", "get_loaded_extensions", "getloaded"])
    async def loaded(self, ctx):
        """Gets loaded extensions. """
        self.client

        em = discord.Embed(title="Cogs", color=blue)
        em.set_footer(text=strings['admin']['extensions_footer'].format(
            len(startup_extensions)))
        em.description = ""
        for extension in startup_extensions:
            em.description = em.description + \
                "- {} \n".format(self.strip_path(extension))
        await ctx.send(embed=em)

    @is_owner_or_admin()
    @commands.command(aliases=["re_load"])
    async def reload(self, ctx):
        """Reload all existing cogs"""
        startup_extensions_temp = startup_extensions
        startup_extensions_temp.insert(0, "loader")

        em = discord.Embed(title="Reloading - please wait", color=red)
        output = await ctx.send(embed=em)

        for cog in startup_extensions_temp:
            extension_full = "{}.{}".format(self.get_path(), cog)
            self.client.unload_extension(extension_full)
            self.client.load_extension(extension_full)

        em = discord.Embed(title="Finished!", colour=green)
        await output.edit(embed=em)


def setup(client):
    client.add_cog(Loader(client))
