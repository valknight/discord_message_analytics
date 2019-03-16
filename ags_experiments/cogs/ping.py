import discord
from discord import Embed
from discord.ext import commands

from ags_experiments.client_tools import ClientTools
from ags_experiments.colours import gold, green, red
from ags_experiments.database import cnx, cursor_dict as cursor
from ags_experiments.database.database_tools import DatabaseTools
from ags_experiments.role_c import DbRole
from ags_experiments.utils import get_role, get_roles, get_user
from ags_experiments.settings.config import config, strings


class Ping(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.prefix = config['discord']['prefix']
        self.client_extras = ClientTools(client)
        self.database_extras = DatabaseTools(self.client_extras)

    async def output_my_roles(self, ctx):
        roles = get_roles(ctx.guild.id, limit_to_joinable=False)
        to_send = "Roles that can be pinged are highlighted in bold.\n"
        em = Embed(title="Roles you are part of", colour=gold)
        for role in roles:
            if str(ctx.author.id) in role['role_assignees']:
                if role['is_pingable']:
                    role['role_name'] = "**{}**".format(role['role_name'])
                temp_to_send = to_send + \
                    " - {}\n".format(role['role_name'])
                if len(temp_to_send) > 2048:  # stops going over char limit
                    em.description = to_send
                    await ctx.channel.send(embed=em)
                    em = Embed(colour=gold)
                    to_send = "- {}\n".format(role['role_name'])
                else:
                    to_send = temp_to_send
        em.description = to_send
        em.description = em.description + \
            "\nTo find more roles to join, run {}`role list`".format(
                self.prefix)
        em.set_footer(text=strings['ping']['help'])
        return await ctx.channel.send(embed=em)

    @commands.group()
    async def role(self, ctx):
        """Manage your roles"""
        if ctx.invoked_subcommand is None:
            await self.output_my_roles(ctx)

    async def output_roles(self, ctx, show_all=0):
        just_joinable = not bool(show_all)
        if just_joinable:
            spacer = " joinable "
        else:
            spacer = " "
        roles = get_roles(ctx.guild.id, limit_to_joinable=just_joinable)
        to_send = ""
        em = Embed(title="All{}roles".format(spacer),
                   colour=gold)
        for role in roles:
            if role['is_pingable']:
                role['role_name'] = "**{}**".format(role['role_name'])
            temp_to_send = to_send + \
                " - {}\n".format(role['role_name'])
            if len(temp_to_send) > 2000:  # stops going over char limit
                em.description = to_send
                await ctx.channel.send(embed=em)
                em = Embed(colour=gold)
                to_send = "- {}\n".format(role['role_name'])
            else:
                to_send = temp_to_send
        em.description = to_send
        em.description = em.description + \
            "To join one of these roles, run `{}role join [role_name]`".format(
                self.prefix)
        em.set_footer(text=strings['ping']['help'])
        return await ctx.channel.send(embed=em)

    @role.command()
    async def list(self, ctx, show_all=0):
        """Get all possible roles"""
        await self.output_roles(ctx, show_all=show_all)

    async def output_join_role(self, ctx, role_name):
        """Join a ping group / role given a name"""
        if role_name[0]=='"' and role_name[-1] == '"':
            role_name=role_name[1:-1]
        role = get_role(ctx.guild.id, role_name)
        try:
            if not role['is_joinable']:
                return await ctx.channel.send("**FAIL** : This role cannot currently be joined.")
        except TypeError:
            return await ctx.channel.send("**FAIL** : Could not find role - are you sure this isn't a Discord based role?")
        cur_members = role['members']
        if ctx.author.id in cur_members:
            return await ctx.channel.send("**FAIL** : You are already a member of this role!")
        cur_members.append(ctx.author.id)
        updated_role = DbRole(
            role['role_id'], role['role_name'], role['is_pingable'], members=cur_members)
        updated_role.save_members()
        return await ctx.channel.send("**SUCCESS** : You have now joined {}".format(role['role_name']))

    @role.command()
    async def join(self, ctx, *, role_name):
        await self.output_join_role(ctx, role_name)

    @role.command()
    async def info(self, ctx, *, role_name):
        if role_name[0]=='"' and role_name[-1] == '"':
            role_name=role_name[1:-1]
        role = get_role(ctx.guild.id, role_name)
        if role is None:
            em = Embed(title="{} does not exist".format(role_name), color=red)
        else:
            em = Embed(title="Information for {}".format(role['role_name']), color=green)
            em.add_field(name="Joinable?", value=str(bool(role['is_joinable'])), inline=True)
            em.add_field(name="Pingable?", value=str(bool(role['is_pingable'])), inline=True)
        em.set_footer(text=strings['ping']['help'])
        await ctx.send(embed=em)
    async def output_leave_role(self, ctx, role_name):
        if role_name[0]=='"' and role_name[-1] == '"':
            role_name=role_name[1:-1]
        role = get_role(ctx.guild.id, role_name)
        if role is None:
            return await ctx.channel.send("**FAIL** : This role does not exist - are you sure it's not a Discord based role?")
        cur_members = role['members']

        if ctx.author.id not in cur_members:
            return await ctx.channel.send("**FAIL** : You are not a member of this role!")

        cur_members.remove(ctx.author.id)
        updated_role = DbRole(
            role['role_id'], role['role_name'], role['is_pingable'], members=cur_members)
        updated_role.save_members()
        return await ctx.channel.send("**SUCCESS** : You have now left {}".format(role['role_name']))

    @role.command()
    async def leave(self, ctx, *, role_name):
        """Join a ping group / role given a name"""
        await self.output_leave_role(ctx, role_name)

    async def output_about_pings(self, ctx):
        prefix = self.prefix
        message = """
Hi there! You've probably had this command given to you to explain how the new ping system works. Below are some quick guides on how to use this new system.

*What roles are currently in this system?*

To find the roles currently in this system, run `{}role list` - this command will spit out the current, up to date list of enabled roles for you to ping.

*How do I join a role?*

Just type `{}role join "[role_name]"` where `role_name` is the name in bold given to you by the command above. Note: the quotes are important!

*How do I ping a role?*

You can either copy paste the command from {}role list, or, if you already know the role name, run `{}ping "[role_name]"` - again, the quotes are important!

*How do I leave a role?*

Just repeat what you did to join a role, but, replace `{}role join` with `{}role leave`.

*I want to find the roles I'm part of? How do I do that?*

Run `{}role` on it's own, and AGSE will tell you!

*Can I turn off being pinged while offline?*

Yes! Just run `{}role settings toggle_offline`

*Can I turn off my username being shown in the channel when pinged?*

Again, yes! Run `{}role settings toggle_public` and all pings will be sent to you over DM, with a link to the message that trigerred it.

*I was already part of a role - do I have to join again?*

No. If you were part of a role before it's migration to this system, your membership was transferred over. Note, this may not apply if you joined after this system went live - you can check with `{}role`

        """.format(prefix, prefix, prefix, prefix, prefix, prefix, prefix, prefix, prefix, prefix)
        em = Embed(title="About roles!", description=message)

        return await ctx.channel.send(embed=em)

    @role.command()
    async def about(self, ctx):
        """Get help on how to use pings"""
        await self.output_about_pings(ctx)

    async def output_get_settings(self, ctx):
        em = discord.Embed(title="Current settings", description="To see how to change this, run `help role settings` ```{}```".format(
            str(get_user(ctx.author.id))))
        return await ctx.channel.send(embed=em)

    @role.group()
    async def settings(self, ctx):
        """Get your current settings for how pings should work"""
        if str(ctx.message.content).endswith("role settings"):
            await self.output_get_settings(ctx)

    async def output_toggle_offline_ping(self, ctx):
        user_settings = get_user(ctx.author.id)

        if user_settings['ping_online_only'] == 1:
            query = "UPDATE `gssp`.`ping_settings` SET `ping_online_only`='0' WHERE `user_id`='%s';"
            return_msg = "You will now be pinged when offline"
        else:
            query = "UPDATE `gssp`.`ping_settings` SET `ping_online_only`='1' WHERE `user_id`='%s';"
            return_msg = "You will now be pinged only when online"

        cursor.execute(query, (ctx.author.id,))
        cnx.commit()
        await ctx.channel.send(embed=discord.Embed(title="Success", description=return_msg, color=green))

    @settings.command()
    async def toggle_offline(self, ctx):
        """Toggle whether or not you should recieve pings while offline"""
        await self.output_toggle_offline_ping(ctx)

    async def output_toggle_public_ping(self, ctx):
        user_settings = get_user(ctx.author.id)

        if user_settings['ping_public'] == 1:
            query = "UPDATE `gssp`.`ping_settings` SET `ping_public`='0' WHERE `user_id`='%s';"
            return_msg = "You will now be pinged over DM"
        else:
            query = "UPDATE `gssp`.`ping_settings` SET `ping_public`='1' WHERE `user_id`='%s';"
            return_msg = "You will now be pinged publicly"

        cursor.execute(query, (ctx.author.id,))
        cnx.commit()
        await ctx.channel.send(embed=discord.Embed(title="Success", description=return_msg, color=green))

    @settings.command()
    async def toggle_public(self, ctx):
        """Toggle whether you are pinged publicly or in private over direct message"""
        self.output_toggle_public_ping(ctx)

    @commands.command(aliases=["toggle_ping_public", "togglepublicping", "togglepingpublic"], hidden=True)
    async def toggle_public_ping(self, ctx):
        """Toggle whether you are pinged publicly or in private over direct message"""
        await self.toggle_public_ping(ctx)

    @commands.command(aliases=["toggle_ping_offline", "toggleofflineping"], hidden=True)
    async def toggle_offline_ping(self, ctx):
        """Toggle whether or not you should recieve pings while offline"""
        await self.output_toggle_offline_ping(ctx)

    @commands.command(hidden=True)
    async def get_settings(self, ctx):
        """Get your current settings for how pings should work"""
        await self.output_get_settings(ctx)

    @commands.command()
    async def ping(self, ctx, *, role_name):
        """
        Usage: ??ping role_name

        To find out more about how the bot based roles work, run the command ?about_pings
        """
        if role_name[0]=='"' and role_name[-1] == '"':
            role_name=role_name[1:-1]
        role = get_role(ctx.guild.id, role_name)
        if role is None:
            return await ctx.channel.send(embed=discord.Embed(title="Fail", description="Cannot find that role.", color=red))
        if role['is_pingable']:
            public_message = ""
            for member in role['members']:
                user_db = get_user(member)
                # get_member is used instead of get_user as User doesn't
                user_discord = ctx.guild.get_member(member)
                if user_discord is not None:
                    # not have a status property, only Members
                    if user_discord.status != discord.Status.offline or (user_db['ping_online_only'] != 1):
                        if user_db['ping_public'] == 1:
                            public_message += user_discord.mention + " "
                        else:
                            em = Embed(title="Ping!", colour=gold)
                            em.add_field(name="Message", value=str(
                                ctx.message.content), inline=False)
                            em.add_field(name="Channel", value=ctx.channel)
                            em.add_field(name="Role", value=role_name)
                            em.add_field(name="Time", value=ctx.message.created_at)
                            em.add_field(name="Pinger", value=str(ctx.author))
                            em.add_field(name="Click here to jump to message",
                                        value="https://discordapp.com/channels/{}/{}/{}".format(ctx.guild.id,
                                                                                                ctx.channel.id,
                                                                                                ctx.message.id),
                                        inline=False)
                            em.set_footer(text=strings['ping']['help'])
                            await user_discord.send(embed=em)
            if public_message == "":
                return await ctx.channel.send(embed=discord.Embed(title="Sent!", description="All users have been pinged privately with the message.", color=green))
            else:
                return await ctx.channel.send(
                    public_message + "\n\n **Message**: {} \n **Author:** {}".format(str(ctx.message.content),
                                                                                     str(ctx.author.mention)))
        else:
            return await ctx.channel.send("**FAIL** : Role not pingable")

    @commands.command(aliases=["join", "joinrole"], hidden=True)
    async def join_role(self, ctx, *, role_name):
        """Join a ping group / role given a name"""
        await self.output_join_role(ctx, role_name)

    @commands.command(aliases=["leave", "leaverole"], hidden=True)
    async def leave_role(self, ctx, *, role_name):
        """Join a ping group / role given a name"""
        await self.output_leave_role(ctx, role_name)

    @commands.command(aliases=["allroles", "all_roles"], hidden=True)
    async def roles(self, ctx, show_all=0):
        """Get all possible roles"""
        await self.output_roles(ctx, show_all=show_all)

    @commands.command(aliases=["myroles", "joinedroles", "joined_roles"], hidden=True)
    async def my_roles(self, ctx):
        """Show roles you are currently part of"""
        await self.output_my_roles(ctx)

    @commands.command(aliases=["pinghelp", "ping_help", "aboutpings"], hidden=True)
    async def about_pings(self, ctx):
        """Get help on how to use pings"""
        await self.output_about_pings(ctx)


def setup(client):
    client.add_cog(Ping(client))
