"""
Created by Val Knight.
Copyright 2018 Val Knight (vallerie.knight@gmail.com)
"""
import discord

with open("ags_experiments/settings/version") as version:
    __version__ = version.read()

__license__ = "MIT"
__author__ = "Val Knight"

async def set_activity(client):
    game = discord.Game(__version__)
    await client.change_presence(status=discord.Status.idle, activity=game)