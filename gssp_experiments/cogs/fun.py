from discord.ext import commands
from discord import Embed
from gssp_experiments.checks import is_owner_or_admin
from gssp_experiments.settings.config import strings, config


class Fun():
    def __init__(self, client):
        self.client = client
    
    @commands.command(aliases=["source", "gitlab", "repo"])
    async def github(self, ctx):
        em = Embed(title="Github link", description="This bot is open source! Check the source, and help development at https://github.com/valknight/discord_message_analytics")
        await ctx.send(embed=em)
    
    @commands.command(aliases=["role_id"])
    async def roleid(self, ctx, role_name):
        for role in ctx.guild.roles:
            if role_name.lower() == role.name.lower():
                return await ctx.send(role.id)
        return await ctx.send(Embed(title="Could not find role {}".format(role_name)))

def setup(client):
    client.add_cog(Fun(client))
