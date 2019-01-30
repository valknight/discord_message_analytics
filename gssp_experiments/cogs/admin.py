import subprocess
import sys

import discord
import emoji
import mysql
from discord.ext import commands

from gssp_experiments.checks import is_owner_or_admin, is_server_allowed
from gssp_experiments.client_tools import ClientTools, add_message
from gssp_experiments.colours import green, red
from gssp_experiments.database import cnx, cursor
from gssp_experiments.database.database_tools import DatabaseTools, insert_role, update_role
from gssp_experiments.role_c import DbRole
from gssp_experiments.settings.config import config, strings
from gssp_experiments.utils import get_role
from gssp_experiments.logger import logger
from gssp_experiments.settings import guild_settings



class Admin():

    def __init__(self, client):
        self.client = client
        self.database_tools = DatabaseTools(client)
        self.client_tools = ClientTools(client)

    @is_server_allowed()
    @commands.command(aliases=["isprocessed", "processed"])
    async def is_processed(self, ctx, user=None):
        """
        Admin command used to check if a member has opted in
        """
        if user is None:
            user = ctx.author.name

        msg = await ctx.send(strings['process_check']['status']['checking'])
        if not self.database_tools.opted_in(user=user):
            return await msg.edit(content=strings['process_check']['status']['not_opted_in'])
        return await ctx.edit(content=strings['process_check']['status']['opted_in'])


    @is_server_allowed()
    @commands.command(aliases=["dumproles"])
    async def dump_roles(self, ctx):
        """
        Dump all roles to a text file on the host
        """
        to_write = ""
        for guild in self.client.guilds:
            to_write += "\n\n=== {} ===\n\n".format(str(guild))
            for role in guild.roles:
                to_write += "{} : {}\n".format(role.name, role.id)
        roles = open("roles.txt", "w")
        roles.write(to_write)
        roles.close()
        em = discord.Embed(title="Done", description="Check roles.txt")
        await ctx.channel.send(embed=em)

    @is_server_allowed()
    @commands.command(aliases=["addrole"])
    async def add_role(self, ctx, role_name):
        """Add a role. Note: by default, it isn't joinable"""
        role_check = get_role(ctx.guild.id, role_name)
        em = discord.Embed(title="Success", description="Created role {}".format(role_name), color=green)
        if role_check is not None:
            em = discord.Embed(title="Error", description="Role is already in the DB", color=red)
        else:
            query = "INSERT INTO `gssp`.`roles` (`role_name`, `guild_id`) VALUES (%s, %s);"
            cursor.execute(query, (role_name, ctx.guild.id))
            cnx.commit()
        return await ctx.channel.send(embed=em)

    @is_server_allowed()
    @commands.command(aliases=["deleterole", "remove_role", "removerole"])
    async def delete_role(self, ctx, role_name):
        """Deletes a role - cannot be undone!"""
        role_check = get_role(ctx.guild.id, role_name)
        em = discord.Embed(title="Success", description="Deleted role {}".format(role_name), color=green)
        if role_check is None:
            em = discord.Embed(title="Error", description="{} is not in the DB".format(role_name), color=red)
        else:
            query = "DELETE FROM `gssp`.`roles` WHERE `role_name` = %s AND `guild_id` = %s"
            cursor.execute(query, (role_name, ctx.guild.id))
            cnx.commit()
        return await ctx.channel.send(embed=em)

    @is_server_allowed()
    @commands.command(aliases=["toggleping", "switchping", "toggle_ping", "switch_ping", "togglepingable"])
    async def toggle_pingable(self, ctx, role_name):
        """Change a role from not pingable to pingable or vice versa"""
        role = get_role(ctx.guild.id, role_name)
        if role is None:
            return await ctx.channel.send(embed=discord.Embed(title='Error', description='Could not find that role', color=red))
        if role['is_pingable'] == 1:
            update_query = "UPDATE `gssp`.`roles` SET `is_pingable`='0' WHERE `role_id`=%s AND `guild_id` = %s;"
            text = "not pingable"
        else:
            update_query = "UPDATE `gssp`.`roles` SET `is_pingable`='1' WHERE `role_id`=%s AND `guild_id` = %s;"
            text = "pingable"
        cursor.execute(update_query, (role['role_id'], ctx.guild.id, ))
        cnx.commit()
        await ctx.channel.send(embed=discord.Embed(title="SUCCESS", description="Set {} ({}) to {}".format(role['role_name'], role['role_id'], text), color=green))

    @is_server_allowed()
    @commands.command(aliases=["togglejoinable", "togglejoin", "toggle_join"])
    async def toggle_joinable(self, ctx, role_name):
        """
        Toggles whether a role is joinable
        """
        role = get_role(ctx.guild.id, role_name)
        if role is None:
            em = discord.Embed(title="Error", description = "Could not find role {}".format(role_name), color=red)
            return await ctx.channel.send(embed=em)
        if role['is_joinable'] == 1:
            update_query = "UPDATE `gssp`.`roles` SET `is_joinable`='0' WHERE `role_id`=%s;"
            text = "not joinable"
        else:
            update_query = "UPDATE `gssp`.`roles` SET `is_joinable`='1' WHERE `role_id`=%s;"
            text = "joinable"
        cursor.execute(update_query, (role['role_id'],))
        em = discord.Embed(title="Success", description="Set {} ({} to {}".format(role['role_name'], role['role_id'], text), color=green)
        cnx.commit()

        await ctx.channel.send(embed=em)

    @is_owner_or_admin()
    @commands.command(aliases=["resyncroles", "syncroles", "rolesync", "role_sync", "sync_roles"])
    async def resync_roles(self, ctx):
        """
        Force refresh the roles in the database with the roles discord has.
        """
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
        await ctx.send(embed=discord.Embed(title="Success", description="Resynced roles.", color=green))
    
    @is_server_allowed()
    @commands.command()
    async def promote_role(self, ctx, role_id):
        """
        Add a role to the list of allowed roles
        """
        role = ctx.guild.get_role(int(role_id))
                
        if role is None:
            return await ctx.send(embed=discord.Embed(title="Error", description="That role does not exist", color=red))
        settings = guild_settings.get_settings(guild=ctx.guild)
        if role_id in settings['staff_roles']:
            return await ctx.send(embed=discord.Embed(title="Error", description="Role already has admin perms", color=red))
        settings['staff_roles'].append(role_id)
        guild_settings.write_settings(settings)
        return await ctx.send(embed=discord.Embed(title="Success", description="Role {} added to admin list".format(role.name), color=green))
    
    @is_server_allowed()
    @commands.command()
    async def demote_role(self, ctx, role_id):
        role_id = int(role_id)
        role_to_remove = ctx.guild.get_role(int(role_id))
        if role_to_remove is None:
            return await ctx.send(embed=discord.Embed(title="Error", description="That role does not exist", color=red))
        settings = guild_settings.get_settings(guild=ctx.guild)
        if role_id in ctx.author.roles: # this means the user is removing a role that gives them perms
            users_permitted_roles = [] # list of roles that give user permission to run this
            for role in ctx.author.roles:
                for role_existing in settings['staff_roles']:
                    if role_existing == role.id:
                        users_permitted_roles.append(role)
            if len(users_permitted_roles) <= 1:
                return await ctx.send(embed=discord.Embed(title="Error", description="You cannot remove a role that gives permissions without another role which has permissions to do so", color=red))
        try:
            settings['staff_roles'].remove(str(role_id))
            guild_settings.write_settings(settings)
            return await ctx.send(embed=discord.Embed(title="Success", description="Removed {} from permitted role list".format(role_to_remove.name), color=green))
        except ValueError:
            return await ctx.send(embed=discord.Embed(title="Error", description="That role does not exist in the permitted role list", color=red))
        


def setup(client):
    client.add_cog(Admin(client))
