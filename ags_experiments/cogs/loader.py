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
import importlib
startup_extensions = [
    "admin",
    "controls",
    "markov",
    "sentiment",
    "flags",
    "nyoom",
    "tagger",
    "fun",
    "ping",
    "unembed",
    "message_logger"
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
    
    
    def load_all_extensions(self):
        """
        This will import all of our extensions, and set extension_imported to the code of the imports
        """
        self.extension_imported = []
        for extension in startup_extensions:
            try:
                to_load = "{}.{}".format(self.get_path(), extension)
                self.extension_imported.append(dict(name=extension, module=importlib.import_module(to_load)))
                self.client.load_extension(to_load)
                logger.info("Loaded {} (from {})".format(extension, to_load))
                del(to_load)
            except Exception as e:
                exc = '{}: {}'.format(type(e).__name__, e)
                logger.error(
                    'Failed to load extension {}\n{}\n{}'.format(extension, exc, traceback.format_exc()))
    
    def __init__(self, client):
        # self.automated = subprocess.Popen(
        #    [sys.executable, "automated_messages.py"])
        self.client = client
        self.client_tools = ClientTools(client)
        # we look for ".admin" and then add "." to prevent matching a root directory ending in admin
        
        self.load_all_extensions()
    
    @is_owner_or_admin()
    @commands.group(aliases=["module"])
    async def cog(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid command passed')

    @commands.is_owner()
    @cog.command(aliases=["un_load"])
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
    @cog.command()
    async def load(self, ctx, extension_name: str):
        """Loads an extension. """
        self.client.load_extension(self.get_path() + "." + extension_name)
        startup_extensions.append(extension_name)
        await ctx.send("{} loaded.".format(extension_name))

    @cog.command(aliases=["get_loaded", "getloadedextensions", "get_loaded_extensions", "getloaded"])
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

    @cog.command(aliases=["re_load"])
    async def reload(self, ctx):
        """Reload all existing cogs"""
        startup_extensions_temp = startup_extensions
        startup_extensions_temp.insert(0, "loader")

        em = discord.Embed(title="Reloading - please wait", color=red)
        output = await ctx.send(embed=em)

        # before loading any extensions, we need to ensure they are all unloaded first
        for cog in startup_extensions_temp:
            extension_full = "{}.{}".format(self.get_path(), cog)
            self.client.unload_extension(extension_full)
        
        self.load_all_extensions()

        em = discord.Embed(title="Finished!", colour=green)
        await output.edit(embed=em)
        
        
    

def setup(client):
    client.add_cog(Loader(client))
