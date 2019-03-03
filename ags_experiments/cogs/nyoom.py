import datetime

import discord
from discord.ext import commands

from ags_experiments.client_tools import ClientTools
from ags_experiments.database import cursor
from ags_experiments.database.database_tools import DatabaseTools
from ags_experiments.settings.config import strings, config
from ags_experiments import colours

class Nyoom(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.client_extras = ClientTools(client)
        self.database_extras = DatabaseTools(self.client_extras)

    async def get_times(self, user_id=None):
        """
        username : user you want to get messages for

        Returns:

        times: list of all timestamps of users messages
        """
        if user_id is None:
            get_time = "SELECT `time` FROM `messages_detailed` ORDER BY TIME ASC"
            cursor.execute(get_time)
        else:
            get_time = "SELECT `time` FROM `messages_detailed` WHERE `user_id` = %s ORDER BY TIME ASC"
            cursor.execute(get_time, (user_id,))
        timesA = cursor.fetchall()
        times = []
        for time in timesA:
            times.append(time[0])
        return times

    async def calculate_nyoom(self, output, user_id=None):
        # load interval between messages we're using from the configs
        interval = config['discord']['nyoom_interval']
        times = await self.get_times(user_id=user_id)
        # group them into periods of activity
        periods = []
        curPeriod = [times[0], times[0], 0]  # begining of period, end of period, number of messages in period
        for time in times:
            if time > curPeriod[1] + datetime.timedelta(0,
                                                        interval):  # if theres more than a 10min dif between this time and last time
                # make a new period
                periods.append(curPeriod)
                curPeriod = [time, time, 1]
            else:
                curPeriod[1] = time  # the period now ends with the most recent timestamp
                curPeriod[2] += 1  # add the message to the period
        # sum the total length of activity periods and divide by total number of messages
        totalT = 0
        totalM = len(times)

        for period in periods:
            totalT += ((period[1] - period[
                0]).total_seconds() / 60) + 1  # total number of minutes for the activity period, plus a fudge factor to prevent single message periods from causing a divide by zero issue later
        totalT /= 60  # makes the total active time and nyoom_metric count hours of activity rather than minutes
        nyoom_metric = totalM / totalT  # number of message per minute during periods of activity
        return totalM, totalT, nyoom_metric

    @commands.command()
    async def nyoom(self, ctx, user: discord.Member = None):
        """
        Calculate the specified user's nyoom metric.
        e.g. The number of messages per hour they post while active (posts within 10mins of each other count as active)

        user : user to get nyoom metric for, if not author
        """
        if user is None:
            user = ctx.message.author

        output = await ctx.send(strings['nyoom_calc']['status']['calculating'] + strings['emojis']['loading'])
        username = self.database_extras.opted_in(user_id=user.id)
        if not username:
            return await output.edit(content=output.content + '\n' + strings['nyoom_calc']['status']['not_opted_in'])
        # grab a list of times that user has posted
        totalM, totalT, nyoom_metric = await self.calculate_nyoom(output, user_id=user.id)
        await output.delete()
        embed = discord.Embed(title="Nyoom metrics", color=colours.blue)
        embed.add_field(name="Message count", value=totalM)
        embed.add_field(name="Total hours", value=totalT)
        embed.add_field(name="Nyoom metric", value=nyoom_metric)
        embed.set_footer(text="These values may not be 100% accurate")
        return await ctx.send(embed=embed)

    @commands.command(aliases=["nyoomserver", "ns", "n_s"])
    async def nyoom_server(self, ctx):
        """
        Calculate nyoom metric for entire server
        """
        output = await ctx.send(strings['nyoom_calc']['status']['calculating'] + strings['emojis']['loading'])
        totalM, totalT, nyoom_metric = await self.calculate_nyoom(output)

        # prepare the final embed to send
        embed = discord.Embed(title="Nyoom metrics", color=colours.blue)
        embed.add_field(name="Message count", value=totalM)
        embed.add_field(name="Total hours", value=totalT)
        embed.add_field(name="Nyoom metric", value=nyoom_metric)
        embed.set_footer(text="These values may not be 100% accurate")
        await output.delete()
        return await ctx.send(embed=embed)


def setup(client):
    client.add_cog(Nyoom(client))
