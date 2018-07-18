import json

import discord
from discord.ext import commands

from gssp_experiments.checks import is_owner_or_admin
from gssp_experiments.client_tools import ClientTools
from gssp_experiments.colours import red, green
from gssp_experiments.database.database_tools import DatabaseTools


class Slurs():
    def __init__(self, client):
        self.client = client
        self.database_tools = DatabaseTools(client)
        self.client_tools = ClientTools(client)

    @is_owner_or_admin()
    @commands.command()
    async def get_slurs(self, ctx):
        """Get the global flag list"""
        await ctx.author.send("***Slurs:***\n```" + open("gssp_experiments/data/bad_words.json").read() + "```")
        await ctx.channel.send(":e_mail: Sent!")

    @is_owner_or_admin()
    @commands.command()
    async def add_slur(self, ctx, slur):
        """Add a slur to the global flag list"""
        await ctx.message.delete()
        file = open("gssp_experiments/data/bad_words.json", 'r')
        slurs = json.loads(file.read())
        slurs.append(slur.lower())
        file.close()
        file = open("gssp_experiments/data/bad_words.json", 'w')
        file.write(json.dumps(slurs))
        file.close()
        await ctx.channel.send(embed=discord.Embed(title="Added slur", color=green))

    @is_owner_or_admin()
    @commands.command()
    async def remove_slur(self, ctx, slur):
        """Remove a slur from the global flag list"""
        await ctx.message.delete()
        file = open("gssp_experiments/data/bad_words.json", 'r')
        slurs = json.loads(file.read())
        if slur.lower() in slurs:
            slurs.remove(slur.lower())
        else:
            return await ctx.channel.send(embed=discord.Embed(title="Slur does not exist", color=red))
        slur_json = json.dumps(slurs)
        file.close()
        file = open("gssp_experiments/data/bad_words.json", "w")
        file.write(slur_json)
        file.close()
        await ctx.channel.send(embed=discord.Embed(title="Removed slur", color=green))


def setup(client):
    client.add_cog(Slurs(client))
