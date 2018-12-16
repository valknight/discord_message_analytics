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
        with open("gssp_experiments/data/bad_words.json") as bad_words_f:
            bad_words = json.loads(bad_words_f.read())
        em = discord.Embed(title="Slurs", description = "")
        for word in bad_words:
            em.description = em.description + "- {}\n".format(word)
        await ctx.author.send(embed=em)
        await ctx.channel.send(":e_mail: Sent!")

    @is_owner_or_admin()
    @commands.command()
    async def add_slur(self, ctx, slur):
        """Add a slur to the global flag list"""
        await ctx.message.delete()
        with open("gssp_experiments/data/bad_words.json", 'r') as slur_f:
            slurs = json.loads(slur_f.read())

        slurs.append(slur.lower())

        with open("gssp_experiments/data/bad_words.json", 'w') as slur_f:
            slur_f.write(json.dumps(slurs, indent=4))

        await ctx.channel.send(embed=discord.Embed(title="Added slur", color=green))

    @is_owner_or_admin()
    @commands.command()
    async def remove_slur(self, ctx, slur):
        """Remove a slur from the global flag list"""
        await ctx.message.delete()
        with open("gssp_experiments/data/bad_words.json", 'r') as existing_words:
            slurs = json.loads(existing_words.read())

        if slur.lower() in slurs:
            slurs.remove(slur.lower())
        else:
            return await ctx.channel.send(embed=discord.Embed(title="Slur does not exist", color=red))
        slur_json = json.dumps(slurs, indent=4)
        file = open("gssp_experiments/data/bad_words.json", "w")
        file.write(slur_json)
        file.close()
        await ctx.channel.send(embed=discord.Embed(title="Removed slur", color=green))


def setup(client):
    client.add_cog(Slurs(client))
