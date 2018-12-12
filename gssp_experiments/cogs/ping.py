import discord
from discord import Embed
from discord.ext import commands

from gssp_experiments.client_tools import ClientTools
from gssp_experiments.colours import gold
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

    @commands.command()
    async def toggle_public_ping(self, ctx):

        user_settings = get_user(ctx.author.id)

        if user_settings['ping_public'] == 1:
            query = "UPDATE `gssp`.`ping_settings` SET `ping_public`='0' WHERE `user_id`='%s';"
            return_msg = "You will now be pinged over DM"
        else:
            query = "UPDATE `gssp`.`ping_settings` SET `ping_public`='1' WHERE `user_id`='%s';"
            return_msg = "You will now be pinged publicly"

        cursor.execute(query, (ctx.author.id,))
        cnx.commit()
        await ctx.channel.send("**SUCCESS** : " + return_msg)

    @commands.command()
    async def toggle_offline_ping(self, ctx):
        user_settings = get_user(ctx.author.id)

        if user_settings['ping_online_only'] == 1:
            query = "UPDATE `gssp`.`ping_settings` SET `ping_online_only`='0' WHERE `user_id`='%s';"
            return_msg = "You will now be pinged when offline"
        else:
            query = "UPDATE `gssp`.`ping_settings` SET `ping_online_only`='1' WHERE `user_id`='%s';"
            return_msg = "You will now be pinged only when online"

        cursor.execute(query, (ctx.author.id,))
        cnx.commit()
        await ctx.channel.send("**SUCCESS** : " + return_msg)

    @commands.command()
    async def get_settings(self, ctx):
        await ctx.channel.send(str(get_user(ctx.author.id)))

    @commands.command()
    async def ping(self, ctx, role_name):
        """
        Usage: ??ping role_name

        To find out more about how the bot based roles work, run the command ?about_pings
        """
        role = get_role(role_name)
        if role is None:
            return await ctx.channel.send("**FAIL** : Cannot find that role.")
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
                return await ctx.channel.send("All users have been pinged privately with the message.")
            else:
                return await ctx.channel.send(
                    public_message + "\n\n Message: {} \n **Author:** {}".format(str(ctx.message.content),
                                                                                 str(ctx.author)))
        else:
            return await ctx.channel.send("**FAIL** : Role not pingable")

    @commands.command()
    async def join_role(self, ctx, role_name):
        """Join a ping group / role given a name"""
        role = get_role(role_name)
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

    @commands.command()
    async def leave_role(self, ctx, role_name):
        """Join a ping group / role given a name"""
        role = get_role(role_name)

        cur_members = role['members']

        if ctx.author.id not in cur_members:
            return await ctx.channel.send("**FAIL** : You are not a member of this role!")

        cur_members.remove(ctx.author.id)
        updated_role = DbRole(
            role['role_id'], role['role_name'], role['is_pingable'], members=cur_members)
        updated_role.save_members()
        return await ctx.channel.send("**SUCCESS** : You have now left {}".format(role['role_name']))

    @commands.command()
    async def roles(self, ctx):
        roles = get_roles()
        to_send = ""
        for role in roles:
            to_send = to_send + \
                " - {}ping **{}**\n".format(config['discord']
                                            ['prefix'], role['role_name'])
        em = Embed(title="Premade commands to ping every enabled role",
                   colour=gold, description=to_send)
        em.set_footer(text=strings['ping']['help'])
        return await ctx.channel.send(embed=em)

    @commands.command()
    async def about_pings(self, ctx):
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
