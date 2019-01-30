from discord.ext import commands

from gssp_experiments.settings.config import config
from gssp_experiments.settings import guild_settings

def is_owner_or_admin():
    def predicate(ctx):
        if ctx.author.id == config['discord']['owner_id']:
            return True
        else:
            for role in ctx.author.roles:
                if str(role.id) in config['discord']["admin_roles"]:
                    return True
        return False

    return commands.check(predicate)

def is_server_allowed():
    def predicate(ctx):
        if ctx.author.id == config['discord']['owner_id']:
            return True # we do this so owner has a constant override
        server_settings = guild_settings.get_settings(guild=ctx.guild)
        if ctx.author.id == ctx.guild.owner.id:
            return True
        for role in ctx.author.roles:
            if str(role.id) in server_settings['staff_roles']:
                return True
        return False
        
    return commands.check(predicate)
