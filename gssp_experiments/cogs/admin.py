import subprocess
import sys

import discord
import emoji
import mysql
from discord.ext import commands

from gssp_experiments.checks import is_owner_or_admin
from gssp_experiments.client_tools import ClientTools, add_message
from gssp_experiments.colours import green, red
from gssp_experiments.database import cnx, cursor
from gssp_experiments.database.database_tools import DatabaseTools, insert_role, update_role
from gssp_experiments.role_c import DbRole
from gssp_experiments.settings.config import config, strings
from gssp_experiments.utils import get_role
from gssp_experiments.logger import logger


class Admin():

    def __init__(self, client):
        self.client = client
        self.database_tools = DatabaseTools(client)
        self.client_tools = ClientTools(client)

    @commands.is_owner()
    @commands.command()
    async def process_server(self, ctx):
        """
        Admin command used to record anonymous analytical data.
        """
        for channel in ctx.guild.text_channels:
            # we run through every channel as discord doesn't provide an
            # easy alternative
            logger.info(str(channel.name) +
                        " is being processed. Please wait.")
            async for message in channel.history(limit=None, reverse=True):
                try:
                    cursor.execute(add_message,
                                   (int(message.id), str(ctx.channel.id),
                                    message.created_at.strftime('%Y-%m-%d %H:%M:%S')))
                except mysql.connector.errors.DataError:
                    logger.info(
                        "Couldn't insert {} - likely a time issue".format(message.id))
                except mysql.connector.errors.IntegrityError:
                    pass
            # commit is here, as putting it in for every message causes
            # mysql to nearly slow to a halt with the amount of queries
            cnx.commit()
            print(str(channel.name) + " has been processed.")
        logger.info("Server {} processing completed".format(str(ctx.guild)))

    @is_owner_or_admin()
    @commands.command()
    async def is_processed(self, ctx, user=None):
        """
        Admin command used to check if a member has opted in
        """
        if user is None:
            user = ctx.author.name

        await ctx.send(strings['process_check']['status']['checking'])
        if not self.database_tools.opted_in(user=user):
            return await ctx.send(strings['process_check']['status']['not_opted_in'])
        await ctx.send(strings['process_check']['status']['opted_in'])
        return

    @is_owner_or_admin()
    @commands.command()
    async def dump_roles(self, ctx):
        to_write = ""
        for guild in self.bot.guilds:
            to_write += "\n\n=== {} ===\n\n".format(str(guild))
            for role in guild.roles:
                to_write += "{} : {}\n".format(role.name, role.id)
        roles = open("roles.txt", "w")
        roles.write(to_write)
        roles.close()
        await ctx.channel.send("Done! Check roles.txt")

    @is_owner_or_admin()
    @commands.command()
    async def get_enabled_roles(self, ctx):
        await ctx.channel.send(str(config.enabled_roles) + "\n\nCheck this against your roles.txt")

    @is_owner_or_admin()
    @commands.command()
    async def add_role(self, ctx, role_name):
        """Add a role. Note: by default, it isn't joinable"""
        role_check = get_role(role_name)
        if role_check is not None:
            return await ctx.channel.send("**FAIL**: Role already exists in DB.")
        query = "INSERT INTO `gssp`.`roles` (`role_name`) VALUES (%s);"
        cursor.execute(query, (role_name,))
        cnx.commit()
        return await ctx.channel.send("**SUCCESS** : Created role {}".format(role_name))

    @is_owner_or_admin()
    @commands.command()
    async def delete_role(self, ctx, role_name):
        """Deletes a role - cannot be undone!"""
        role_check = get_role(role_name)
        if role_check is None:
            return await ctx.channel.send("**FAIL**: Role does not exist in DB.")
        query = "DELETE FROM `gssp`.`roles` WHERE `role_name` = %s;"
        cursor.execute(query, (role_name,))
        cnx.commit()
        return await ctx.channel.send("**SUCCESS** : Deleted role {}".format(role_name))

    @is_owner_or_admin()
    @commands.command()
    async def toggle_pingable(self, ctx, role_name):
        """Change a role from not pingable to pingable or vice versa"""
        role = get_role(role_name)
        if role is None:
            return await ctx.channel.send("Could not find that role!")
        if role['is_pingable'] == 1:
            update_query = "UPDATE `gssp`.`roles` SET `is_pingable`='0' WHERE `role_id`=%s;"
            text = "not pingable"
        else:
            update_query = "UPDATE `gssp`.`roles` SET `is_pingable`='1' WHERE `role_id`=%s;"
            text = "pingable"
        cursor.execute(update_query, (role['role_id'],))
        await ctx.channel.send("**SUCCESS** : Set {} ({}) to {}".format(role['role_name'], role['role_id'], text))

        cnx.commit()

    @is_owner_or_admin()
    @commands.command()
    async def toggle_joinable(self, ctx, role_name):
        """
        Toggles whether a role is joinable
        """
        role = get_role(role_name)
        if role is None:
            return await ctx.channel.send("Could not find that role!")
        if role['is_joinable'] == 1:
            update_query = "UPDATE `gssp`.`roles` SET `is_joinable`='0' WHERE `role_id`=%s;"
            text = "not joinable"
        else:
            update_query = "UPDATE `gssp`.`roles` SET `is_joinable`='1' WHERE `role_id`=%s;"
            text = "joinable"
        cursor.execute(update_query, (role['role_id'],))
        await ctx.channel.send("**SUCCESS** : Set {} ({}) to {}".format(role['role_name'], role['role_id'], text))

        cnx.commit()

    @is_owner_or_admin()
    @commands.command()
    async def resync_roles(self, ctx):
        for guild in self.client.guilds:
            for role in guild.roles:
                if role.name != "@everyone":
                    try:
                        cursor.execute(insert_role, (role.id, role.name))
                    except mysql.connector.errors.IntegrityError:
                        pass

                    # this is designed to assist with migration, by moving old discord role members over to the new
                    # system seamlessly
                    member_ids = []
                    for member in role.members:
                        member_ids.append(member.id)
                    role_db = DbRole(role.id, role.name, 0, members=member_ids)
                    role_db.save_members()
                    cursor.execute(
                        update_role, (emoji.demojize(role.name), role.id))


def setup(client):
    client.add_cog(Admin(client))
