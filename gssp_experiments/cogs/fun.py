from discord.ext import commands

from gssp_experiments.settings.config import strings, config


class Fun():
    def __init__(self, client):
        self.client = client

    @commands.is_owner()
    @commands.command()
    async def thonkang(self, cnx):
        """
        Do a big thonk
        :return:
        """
        await cnx.message.delete()
        await cnx.send(strings['emojis']['loading'])

    @commands.is_owner()
    @commands.command()
    async def send_emoji(self, ctx, name, emoji_id):
        """
        Send an emoji!
        :param name: Name of emoji
        :param emoji_id: Emoji ID
        :return:
        """
        await ctx.message.delete()
        await ctx.send(strings['emojis']['animated_emoji_template'].format(name, int(id)))

    if config['despacito_enabled']:
        @commands.command()
        async def despacito(self, ctx):
            """
            This is so sad, alexa play...
            :return:
            """
            for channel in ctx.guild.voice_channels:
                if str(channel) == "Music":
                    voice_c = channel
            try:
                if not ctx.voice_client.is_playing():
                    pass
            except AttributeError:
                await voice_c.connect()
            return await ctx.send(';play https://www.youtube.com/watch?v=kJQP7kiw5Fk')


def setup(client):
    client.add_cog(Fun(client))
