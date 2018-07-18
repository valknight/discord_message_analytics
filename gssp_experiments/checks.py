from discord.ext import commands

from gssp_experiments.settings.config import config


def is_owner_or_admin():
    def predicate(ctx):
        if ctx.author.id == config['discord']['owner_id']:
            return True
        else:
            for role in ctx.author.roles:
                if role.id in config['discord']["admin_roles"]:
                    return True
        return False

    return commands.check(predicate)
