"""
Created by Val Knight.
Copyright 2018 Val Knight (vallerie.knight@gmail.com)
"""
import discord

def get_version():
    with open("ags_experiments/settings/version") as version:
        version = version.read()
    return version

__license__ = "MIT"
__author__ = "Val Knight"
__version__ = str(get_version())

async def set_activity(client):
    output = str(get_version())
    if __version__ != str(get_version()): # version must've changed, bot may need rebooting
        output = output+" [R]"
    game = discord.Game(output)
    await client.change_presence(status=discord.Status.idle, activity=game)