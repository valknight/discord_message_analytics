import discord
from discord import Embed
from discord.ext import commands

from gssp_experiments.client_tools import ClientTools
from gssp_experiments.colours import gold
from gssp_experiments.database import cnx, cursor_dict as cursor
from gssp_experiments.database.database_tools import DatabaseTools
from gssp_experiments.role_c import DbRole
from gssp_experiments.utils import get_role, get_user


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
        role = get_role(role_name)
        if role is None:
            return await ctx.channel.send("**FAIL** : Cannot find that role.")
        print(role)
        if role['is_pingable']:
            public_message = ""
            for member in role['members']:
                user_db = get_user(member)
                user_discord = ctx.guild.get_member(member)  # get_member is used instead of get_user as User doesn't
                # not have a status property, only Members
                print(member)
                if user_discord.status != discord.Status.offline or (user_db['ping_online_only'] != 1):
                    print("Member allowed")
                    if user_db['ping_public'] == 1:
                        public_message += user_discord.mention + " "
                    else:
                        em = Embed(title = "Ping!", colour = gold)
                        em.add_field(name = "Message", value = str(ctx.message.content), inline = False)
                        em.add_field(name = "Channel", value = ctx.channel)
                        em.add_field(name = "Role", value = role_name)
                        em.add_field(name = "Time", value = ctx.message.created_at)
                        em.add_field(name = "Pinger", value = str(ctx.author))
                        em.add_field(name = "Click here to jump to message",
                                     value = "https://discordapp.com/channels/{}/{}/{}".format(ctx.guild.id,
                                                                                               ctx.channel.id,
                                                                                               ctx.message.id),
                                     inline = False)
                        await user_discord.send(embed = em)
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
        updated_role = DbRole(role['role_id'], role['role_name'], role['is_pingable'], members=cur_members)
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
        updated_role = DbRole(role['role_id'], role['role_name'], role['is_pingable'], members = cur_members)
        updated_role.save_members()
        return await ctx.channel.send("**SUCCESS** : You have now left {}".format(role['role_name']))
def setup(client):
    client.add_cog(Ping(client))
