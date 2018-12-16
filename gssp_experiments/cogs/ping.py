import discord
from discord import Embed
from discord.ext import commands

from gssp_experiments.client_tools import ClientTools
from gssp_experiments.colours import gold, green, red
from gssp_experiments.database import cnx, cursor_dict as cursor
from gssp_experiments.database.database_tools import DatabaseTools
from gssp_experiments.role_c import DbRole
from gssp_experiments.utils import get_role, get_roles, get_user
from gssp_experiments.settings.config import config, strings


class Ping():

    def __init__(self, client):
        self.client = client
        self.client_extras = ClientTools(client)
        self.database_extras = DatabaseTools(self.client_extras)

    @commands.command(aliases=["toggle_ping_public", "togglepublicping", "togglepingpublic"])
    async def toggle_public_ping(self, ctx):
        """Toggle whether you are pinged publicly or in private over direct message"""
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

    @commands.command(aliases=["toggle_ping_offline", "toggleofflineping"])
    async def toggle_offline_ping(self, ctx):
        """Toggle whether or not you should recieve pings while offline"""
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

    @commands.command()
    async def get_settings(self, ctx):
        await ctx.channel.send(embed=discord.Embed(title="User settings", description="```{}```".format(str(get_user(ctx.author.id)))))

    @commands.command()
    async def ping(self, ctx, role_name):
        """
        Usage: ??ping role_name

        To find out more about how the bot based roles work, run the command ?about_pings
        """
        role = get_role(ctx.guild.id, role_name)
        if role is None:
            return await ctx.channel.send(embed=discord.Embed(title="Fail", description="Cannot find that role.", color=red))
        if role['is_pingable']:
            public_message = ""
            for member in role['members']:
                user_db = get_user(member)
                # get_member is used instead of get_user as User doesn't
                user_discord = ctx.guild.get_member(member)
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

    @commands.command(aliases=["join", "joinrole"])
    async def join_role(self, ctx, role_name):
        """Join a ping group / role given a name"""
        role = get_role(ctx.guild.id, role_name)
        try:
            if not role['is_joinable']:
                return await ctx.channel.send("**FAIL** : This role cannot currently be joined.")
        except TypeError:
            return await ctx.channel.send("**FAIL** : Could not find role - if you put spaces in, make sure it's in "
                                          "\"Quotation marks like this\"")
        cur_members = role['members']

        if ctx.author.id in cur_members:
            return await ctx.channel.send("**FAIL** : You are already a member of this role!")

        cur_members.append(ctx.author.id)
        updated_role = DbRole(
            role['role_id'], role['role_name'], role['is_pingable'], members=cur_members)
        updated_role.save_members()
        return await ctx.channel.send("**SUCCESS** : You have now joined {}".format(role['role_name']))

    @commands.command(aliases=["leave", "leaverole"])
    async def leave_role(self, ctx, role_name):
        """Join a ping group / role given a name"""
        role = get_role(ctx.guild.id, role_name)

        cur_members = role['members']

        if ctx.author.id not in cur_members:
            return await ctx.channel.send("**FAIL** : You are not a member of this role!")

        cur_members.remove(ctx.author.id)
        updated_role = DbRole(
            role['role_id'], role['role_name'], role['is_pingable'], members=cur_members)
        updated_role.save_members()
        return await ctx.channel.send("**SUCCESS** : You have now left {}".format(role['role_name']))

    @commands.command(aliases=["allroles", "all_roles"])
    async def roles(self, ctx, show_all=0):
        """Get all possible roles"""
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
            if len(temp_to_send) > 2048: # stops going over char limit
                em.description = to_send
                await ctx.channel.send(embed=em)
                em = Embed(colour=gold)
                to_send = "- {}\n".format(role['role_name'])
            else:
                to_send = temp_to_send
        em.description = to_send
        em.set_footer(text=strings['ping']['help'])
        return await ctx.channel.send(embed=em)

    @commands.command(aliases=["myroles", "joinedroles", "joined_roles"])
    async def my_roles(self, ctx):
        roles = get_roles(ctx.guild.id, limit_to_joinable=False)
        to_send = "Roles that can be pinged are highlighted in bold.\n"
        em = Embed(title="Roles you are part of", colour=gold)
        for role in roles:
            if str(ctx.author.id) in role['role_assignees']:
                if role['is_pingable']:
                    role['role_name'] = "**{}**".format(role['role_name'])
                temp_to_send = to_send + \
                    " - {}\n".format(role['role_name'])
                if len(temp_to_send) > 2048: # stops going over char limit
                    em.description = to_send
                    await ctx.channel.send(embed=em)
                    em = Embed(colour=gold)
                    to_send = "- {}\n".format(role['role_name'])
                else:
                    to_send = temp_to_send
        em.description = to_send
        em.set_footer(text=strings['ping']['help'])
        return await ctx.channel.send(embed=em)

    @commands.command(aliases=["pinghelp", "ping_help", "aboutpings"])
    async def about_pings(self, ctx):
        """Get help on how to use pings"""
        prefix = config['discord']['prefix']
        message = """
Hi there! You've probably had this command given to you to explain how the new ping system works. Below are some quick guides on how to use this new system.

*What roles are currently in this system?*

To find the roles currently in this system, run `{}roles` - this command will spit out the current, up to date list of enabled roles for you to ping.

*How do I join a role?*

Just type `{}join_role "[role_name]"` where `role_name` is the name in bold given to you by the command above. Note: the quotes are important!

*How do I ping a role?*

You can either copy paste the command from {}roles, or, if you already know the role name, run `{}ping "[role_name]"` - again, the quotes are important!

*How do I leave a role?*

Just repeat what you did to join a role, but, replace `{}join_role` with `{}leave_role`.

*Can I turn off being pinged while offline?*

Yes! Just run `{}toggle_offline_ping`

*Can I turn off my username being shown in the channel when pinged?*

Again, yes! Run `{}toggle_public_ping` and all pings will be sent to you over DM, with a link to the message that trigerred it.

*I was already part of a role - do I have to join again?*

No. If you were part of a role before it's migration to this system, your membership was transferred over.

        """.format(prefix, prefix, prefix, prefix, prefix, prefix, prefix, prefix)
        em = Embed(title="About roles!", description=message)

        return await ctx.channel.send(embed=em)


def setup(client):
    client.add_cog(Ping(client))
