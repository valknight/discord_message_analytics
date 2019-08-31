import json
import subprocess
import sys

import discord
import emoji
import mysql
from discord.ext import commands

from ags_experiments.checks import is_owner_or_admin, is_server_allowed
from ags_experiments.client_tools import ClientTools, add_message
from ags_experiments.colours import green, red, yellow
from ags_experiments.database import cnx, cursor
from ags_experiments.database.database_tools import DatabaseTools, insert_role, update_role
from ags_experiments.role_c import DbRole
from ags_experiments.settings.config import config, strings
from ags_experiments.utils import get_role
from ags_experiments.logger import logger
from ags_experiments.settings import guild_settings


class Admin(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.database_tools = DatabaseTools(client)
        self.client_tools = ClientTools(client)

    @commands.group(hidden=True)
    async def debug(self, ctx):
        """Debug utilities for AGSE and Discord"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Invalid params. Run `help debug` to get all commands.")

    @is_server_allowed()
    @debug.command(aliases=["isprocessed", "processed"])
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

    @is_owner_or_admin()
    @debug.command(aliases=["dumproles"])
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

    @debug.command(aliases=["lag"])
    async def latency(self, ctx, detailed=None):
        detailed = bool(detailed)
        # this is a tuple, with [0] being the shard_id, and [1] being the latency
        latencies = self.client.latencies
        lowest_lag = latencies[0]
        highest_lag = latencies[0]
        sum = 0
        for i in latencies:
            if i[1] < lowest_lag[1]:
                lowest_lag = i
            if i[1] > highest_lag[1]:
                highest_lag = i
            # could probably do this in a one liner, but may as well as we have to iterate anyway
            sum += i[1]

        avg = (sum/len(latencies))

        embed = discord.Embed(title="Latency")

        # add specific information about latency
        embed.add_field(name="Avg", value="{}".format(str(avg)))
        embed.add_field(name="Lowest Latency", value="{} on shard {}".format(
            lowest_lag[1], lowest_lag[0]))
        embed.add_field(name="Highest Latency", value="{} on shard {}".format(
            highest_lag[1], highest_lag[0]))

        if detailed:
            embed.add_field(name="RawData", value=str(latencies))

        return await ctx.channel.send(embed=embed)

    @debug.command(aliases=["role_id"])
    async def roleid(self, ctx, role_name):
        for role in ctx.guild.roles:
            if role_name.lower() == role.name.lower():
                return await ctx.send(role.id)
        return await ctx.send(embed=discord.Embed(title="Could not find role {}".format(role_name)))

    @is_server_allowed()
    @commands.group(aliases=["rolem"])
    async def role_manage(self, ctx):
        """Manages AGSE roles (ping groups)"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Invalid params. Run `help rolem` to get all commands.")

    @role_manage.command()
    async def add(self, ctx, *, role_name):
        """Add a role. Note: by default, it isn't joinable"""
        if role_name[0]=='"' and role_name[-1] == '"':
            role_name=role_name[1:-1]
        role_check = get_role(ctx.guild.id, role_name)
        em = discord.Embed(
            title="Success", description="Created role {}".format(role_name), color=green)
        if role_check is not None:
            em = discord.Embed(
                title="Error", description="Role is already in the DB", color=red)
        else:
            query = "INSERT INTO `gssp`.`roles` (`role_name`, `guild_id`) VALUES (%s, %s);"
            cursor.execute(query, (role_name, ctx.guild.id))
            cnx.commit()
        return await ctx.channel.send(embed=em)

    @role_manage.command(aliases=["remove"])
    async def delete(self, ctx, *, role_name):
        """Deletes a role - cannot be undone!"""
        if role_name[0]=='"' and role_name[-1] == '"':
            role_name=role_name[1:-1]
        role_check = get_role(ctx.guild.id, role_name)
        em = discord.Embed(
            title="Success", description="Deleted role {}".format(role_name), color=green)
        if role_check is None:
            em = discord.Embed(
                title="Error", description="{} is not in the DB".format(role_name), color=red)
        else:
            query = "DELETE FROM `gssp`.`roles` WHERE `role_name` = %s AND `guild_id` = %s"
            cursor.execute(query, (role_name, ctx.guild.id))
            cnx.commit()
        return await ctx.channel.send(embed=em)

    @role_manage.command(aliases=["togglepingable"])
    async def pingable(self, ctx, *, role_name):
        """Change a role from not pingable to pingable or vice versa"""
        if role_name[0]=='"' and role_name[-1] == '"':
            role_name=role_name[1:-1]
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

    @role_manage.command(aliases=["togglejoinable", "togglejoin", "toggle_join"])
    async def joinable(self, ctx, *, role_name):
        """
        Toggles whether a role is joinable
        """
        if role_name[0]=='"' and role_name[-1] == '"':
            role_name=role_name[1:-1]
        role = get_role(ctx.guild.id, role_name)
        if role is None:
            em = discord.Embed(title="Error", description="Could not find role {}".format(
                role_name), color=red)
            return await ctx.channel.send(embed=em)
        if role['is_joinable'] == 1:
            update_query = "UPDATE `gssp`.`roles` SET `is_joinable`='0' WHERE `role_id`=%s;"
            text = "not joinable"
        else:
            update_query = "UPDATE `gssp`.`roles` SET `is_joinable`='1' WHERE `role_id`=%s;"
            text = "joinable"
        cursor.execute(update_query, (role['role_id'],))
        em = discord.Embed(title="Success", description="Set {} ({} to {}".format(
            role['role_name'], role['role_id'], text), color=green)
        cnx.commit()

        await ctx.channel.send(embed=em)

    @is_owner_or_admin()
    @commands.group(aliases=["config"])
    async def settings(self, ctx):
        """Manages settings of AGSE"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Invalid params. Run `help settings` to get all commands.")

    @settings.command(aliases=["resyncroles", "syncroles", "rolesync", "role_sync", "sync_roles"])
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

    @is_owner_or_admin()
    @settings.group(aliases=["permissions"])
    async def perms(self, ctx):
        """Manages AGSE roles (ping groups)"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Run `help settings perms` to get info on subcommands")

    @perms.command()
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

    @perms.command()
    async def demote_role(self, ctx, role_id):
        role_id = int(role_id)
        role_to_remove = ctx.guild.get_role(int(role_id))
        if role_to_remove is None:
            return await ctx.send(embed=discord.Embed(title="Error", description="That role does not exist", color=red))
        settings = guild_settings.get_settings(guild=ctx.guild)
        if role_id in ctx.author.roles:  # this means the user is removing a role that gives them perms
            users_permitted_roles = []  # list of roles that give user permission to run this
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

    @is_owner_or_admin()
    @commands.command()
    async def sync(self, ctx):
        clone_target = self.client.get_guild(
            config['discord'].get("clone_server_target"))
        def generate_progress_embed(m_text, colour=yellow, url=None):
            em = discord.Embed(title="Server Clone Progress", description="Status: {text}".format(text=m_text), colour=colour)
            if url is not None:
                em.add_field(name="Invite link", value=url)
            return em
        guild = ctx.guild
        # we just need to now create an instant invite to *somewhere* on the server
        progress = await ctx.send(embed=generate_progress_embed("Dumping existing data from {guild.name}".format(guild=guild)))
        channels = []
        roles = []

        def get_channel_position(old_id=None, new_id=None):
            if new_id is None and old_id is None:
                raise AttributeError
            for x in range(0, len(channels)):
                channel = channels[x]
                # the and is not None prevent us from returning whatever channel has None as an attribute
                if (channel.get("old_id") == old_id and old_id is not None) or (channel.get("new_id") == new_id and new_id is not None):
                    return x
            return None

        def get_channel(old_id=None, new_id=None):
            position = get_channel_position(old_id=old_id, new_id=new_id)
            if position is None:
                return None
            return channels[position]

        def add_channel(old_channel, new_channel=None):
            to_append = (dict(old_id=old_channel.id, old_channel=old_channel))
            if new_channel is None:
                to_append['new_id'] = None
                to_append['new_channel'] = None
            else:
                to_append['new_id'] = new_channel.id
                to_append['new_channel'] = new_channel
            channels.append(to_append)

        def set_new_channel(old_channel_id, new_channel):
            # we don't use the new_channel id, as not merged yet
            position = get_channel_position(old_id=old_channel_id)
            new_channel = get_channel_object_dict(new_channel)
            channels[position]['new_channel'] = new_channel
            channels[position]['new_id'] = new_channel['id']

        def get_role_position(old_id=None, new_id=None):
            if new_id is None and old_id is None:
                return None  # means we don't have to do unnecesary searches
            if old_id is not None:
                old_id = int(old_id)
            if new_id is not None:
                new_id = int(new_id)
            for x in range(0, len(roles)):
                role = roles[x]
                # the and is not None prevent us from returning whatever channel has None as an attribute
                if (role.get("old_id") == old_id and old_id is not None) or (role.get("new_id") == new_id and new_id is not None):
                    return x
            return None

        def get_role(old_id=None, new_id=None):
            position = get_role_position(old_id=old_id, new_id=new_id)
            if position is None:
                return None
            return roles[position]

        def add_role(old_role, new_role=None):
            to_append = (dict(old_id=old_role.id, old_role=old_role))
            if new_role is None:
                to_append['new_id'] = None
                to_append['new_role'] = None
            else:
                to_append['new_id'] = new_role.id
                to_append['new_role'] = new_role
            roles.append(to_append)

        def set_new_role(old_role_id, new_role):
            # we don't use the new_role id, as not merged yet
            position = get_role_position(old_id=old_role_id)
            roles[position]['new_role'] = new_role
            roles[position]['new_id'] = new_role.id

        def get_role_object_dict(role):
            if type(role) == dict:
                return role  # if already role, just return it
            return dict(id=role.id, name=role.name, permissions=role.permissions.value, colour=role.colour.value, hoist=role.hoist, mentionable=role.mentionable)

        def get_role_dicts(roles=roles):
            backup_roles = roles
            role_dicts = []
            for role in roles:
                if role.get('old_role') is not None:
                    role['old_role'] = get_role_object_dict(role['old_role'])
                if role.get('new_role') is not None:
                    role['new_role'] = get_role_object_dict(role['new_role'])
                role_dicts.append(role)
            return role_dicts

        def get_channel_type(channel):

            if type(channel) == discord.channel.TextChannel:
                return "Text"
            if type(channel) == discord.channel.VoiceChannel:
                return "Voice"
            if type(channel) == discord.channel.CategoryChannel:
                return "Category"
            return "Unknown"

        def get_channel_object_dict(channel):
            if type(channel) == dict:
                return channel  # already converted
            new_overwrites = []
            overwrites = channel.overwrites
            for overwrite in overwrites:
                allow, deny = overwrite[1].pair()
                if type(overwrite[0]) == discord.role.Role:
                    role = get_role(old_id=overwrite[0].id)
                    if role is None:
                        to_append = dict(grantee=dict(
                            old_id=overwrite[0].id, type="Role"))
                    else:
                        to_append = dict(grantee=dict(old_id=role.get('old_id'), new_id=role.get(
                            'new_id'), old_name=role.get('old_role', dict()).get('name'), type="Role"))
                else:  # user overwrite
                    to_append = dict(grantee=dict(
                        id=overwrite[0].id, type="User"))
                to_append['allow_permission'] = allow.value
                to_append['deny_permission'] = deny.value
                new_overwrites.append(to_append)
            to_return = dict(id=channel.id, name=channel.name, type=get_channel_type(
                channel), overwrites=new_overwrites, position=channel.position)
            if to_return['type'] != "Category":
                if channel.category is not None:
                    to_return['category'] = get_channel_object_dict(
                        channel.category)
                else:
                    to_return['category'] = None
                if to_return['type'] == "Text":
                    # do text
                    to_return['topic'] = channel.topic
                    to_return['slowmode_delay'] = channel.slowmode_delay
                    to_return['nsfw'] = channel.nsfw

                elif to_return['type'] == "Voice":
                    # do voice
                    if channel.bitrate > 96000:
                        # Higher bitrates require nitro boosts, which the destination server may not have. Assume not.
                        to_return['bitrate'] = 96000
                    else:
                        to_return['bitrate'] = channel.bitrate
                    to_return['user_limit'] = channel.user_limit
            return to_return

        def get_channel_dicts(channels=channels):
            backup_channels = channels
            channel_dicts = []
            for channel in channels:
                if channel.get('old_channel') is not None:
                    channel['old_channel'] = get_channel_object_dict(
                        channel['old_channel'])
                if channel.get('new_channel') is not None:
                    channel['new_role'] = get_channel_object_dict(
                        channel['new_channel'])
                channel_dicts.append(channel)
            channels = backup_channels
            return channel_dicts

        def generate_overwrites(old_channel):
            overwrites = dict()
            for overwrite in old_channel['overwrites']:
                allow = discord.Permissions(overwrite['allow_permission'])
                deny = discord.Permissions(overwrite['deny_permission'])
                permission_pair = discord.PermissionOverwrite.from_pair(
                    allow, deny)
                target = None  # we do this incase down the road there's a new type of grantee we haven't handled
                # if a user isn't in the new server, we can't add overwrites for them
                if overwrite['grantee']['type'] == "User":
                    target = clone_target.get_member(
                        overwrite['grantee']['id'])
                # this is the code which will convert the old_id in the overwrite into the new_id
                elif overwrite['grantee']['type'] == "Role":
                    role = get_role(old_id=overwrite['grantee']['old_id'])
                    if role is not None:
                        target = clone_target.get_role(role['new_id'])
                    else:
                        old_role = ctx.guild.get_role(
                            overwrite['grantee']['old_id'])
                        if old_role.name == "@everyone":
                            target = clone_target.default_role
                        else:
                            print("Could not find new role pair for old role with ID {}".format(
                                overwrite['grantee']['old_id']))
                if target is not None:
                    overwrites[target] = permission_pair
            return overwrites
        s_channels = guild.channels
        s_channels.sort(key=lambda x: x.position, reverse=False)

        for channel in s_channels:
            add_channel(channel)

        s_roles = guild.roles
        s_roles.reverse()
        for role in s_roles:
            if role.name != "@everyone":
                add_role(role)
        await progress.edit(embed=generate_progress_embed("Wiping roles of {clone_target.name}".format(clone_target=clone_target)))

        for role in clone_target.roles:
            try:
                await role.delete(reason="Cleaning for copying")
            except discord.errors.HTTPException:
                pass
        
        await progress.edit(embed=generate_progress_embed("Wiping channels of {clone_target.name}".format(clone_target=clone_target)))
        for channel in clone_target.channels:
            await channel.delete(reason="Cleaning for copying")
        print("Wiped channels")

        await progress.edit(embed=generate_progress_embed("Creating new roles in {clone_target.name}".format(clone_target=clone_target)))
        for role in get_role_dicts():
            old_role = role['old_role']
            logger.info(
                "Adding role{id} - {name}".format(id=role['old_id'], name=role['old_role']['name']))
            new_role_to_merge = await clone_target.create_role(name=old_role['name'], permissions=discord.Permissions(permissions=old_role['permissions']), colour=discord.Colour(old_role['colour']), hoist=old_role['hoist'], mentionable=old_role['mentionable'])
            set_new_role(old_role['id'], new_role_to_merge)

        get_role_dicts()  # this converts all the new channels into nice dictionary formats

        await progress.edit(embed=generate_progress_embed("Creating new channels in {clone_target.name}".format(clone_target=clone_target)))

        # first, we add the categories
        channels_to_add = get_channel_dicts()
        channels.sort(key=lambda x: x['old_channel']
                      ['position'], reverse=False)
        for channel in channels_to_add:
            old_channel = channel['old_channel']
            if old_channel['type'] == "Category":
                logger.info(
                    "Adding category {id} - {name}".format(id=old_channel['id'], name=old_channel['name']))
                # build overwrites
                overwrites = generate_overwrites(old_channel)

                channel = await clone_target.create_category_channel(old_channel['name'], overwrites=overwrites, reason="Syncing of channels")
                set_new_channel(old_channel['id'], channel)
        # this makes sure everything is still in dictionary formats
        channels_to_add = get_channel_dicts()
        # now we know all our categories are added, we can add all other channels
        for channel in channels_to_add:
            old_channel = channel['old_channel']
            if old_channel['type'] != "Category":
                logger.info("Adding {type} channel {id} - {name}".format(
                    type=old_channel['type'], id=old_channel['id'], name=old_channel['name']))
                overwrites = generate_overwrites(old_channel)

                category = get_channel(
                    old_id=old_channel['category'].get('id'))
                if category is not None:
                    category_id = category['new_id']
                    # gets the role object that we need to create the channel
                    category = clone_target.get_channel(category_id)
                if old_channel['type'] == "Text":
                    channel = await clone_target.create_text_channel(old_channel['name'], overwrites=overwrites, reason="Syncing of channels", position=old_channel['position'], topic=old_channel['topic'], slowmode_delay=old_channel['slowmode_delay'], nsfw=old_channel['nsfw'], category=category)
                elif old_channel['type'] == "Voice":
                    channel = await clone_target.create_voice_channel(old_channel['name'], overwrites=overwrites, reason="Syncing of channels", position=old_channel['position'], bitrate=old_channel['bitrate'], user_limit=old_channel['user_limit'], category=category)
                channel = get_channel_object_dict(channel)
                set_new_channel(old_channel['id'], channel)
        with open(".last_sync.json", "w") as f:
            f.write(json.dumps(dict(roles=get_role_dicts(roles=roles),
                                    channels=get_channel_dicts(channels=channels)), indent=4))

        invite = await clone_target.text_channels[0].create_invite(max_age=0, max_uses=0, unique=True, reason="Generating invite link to join with")
        await progress.edit(embed=generate_progress_embed("Done!", colour=green, url=invite.url))


def setup(client):
    client.add_cog(Admin(client))
