from discord.ext import commands
from discord import Embed
from ags_experiments.checks import is_owner_or_admin
from ags_experiments.settings.config import strings, config
from random import randint
from ags_experiments.colours import green, red, yellow
import discord.errors
import json
import concurrent

class WordList():
    def __init__(self, file_path=None, word_list=None):
        if file_path is None and word_list is None:
            file_path = "ags_experiments/data/hang_man.json"
        if word_list is None:
            with open(file_path, "r") as file:
                raw_string = file.read()
            word_list = json.loads(raw_string)['words']
        self.words = word_list


class Hangman():
    def check_word(self, word):
        return True # TODO: add actual checks
    
    def get_attributes(self, difficulty):
        if difficulty == 0:
            self.lives = 12
        elif difficulty == 1:
            self.lives = 10
        elif difficulty == 2:
            self.lives = 8

    def __init__(self, difficulty=0, word_list=None):
        """
        difficulty: 0 for easy, 1 for medium, 2 for hard. Default: 0
        word_list: List of strings, or path to JSON file on disk
        """
        self.get_attributes(difficulty) # this sets up lives and whatevs for us

        # load our word list if it's not already present
        if word_list is None:
            word_list = WordList()
        elif type(word_list) == list:
            word_list = WordList(word_list=word_list)
        else:
            word_list = WordList(file_path=word_list)
        word = None
        while word is None:
            x = (randint(0, len(word_list.words)))
            if self.check_word(word_list.words[x]):
                word = word_list.words[x]
        
        # set u
        self.word = word
        self.revealed = ""
        self.guessed = []
        for x in range(0, len(word)):
            self.revealed = self.revealed + "_"
    def format_reveal(self):
        chars_revealed = []
        [chars_revealed.append(x) for x in self.revealed]
        return " ".join(chars_revealed)
    def check_letter(self, letter):
        """
        letter: letter to guess (single character)
        Returns False if there are future guesses to be made, or True if hangman finished
        """
        if self.lives<=0:
            return True # we do this, so a person can't cheat their way into extra guesses
        
        if len(letter)>1:
            raise ValueError("More than one letter passed")
        if letter.lower() in self.guessed:
            return False
        
        chars_revealed = []
        [chars_revealed.append(x) for x in self.revealed]
        found = False
        for x in range(0, len(self.word)):
            if self.word[x].lower() == letter.lower():
                chars_revealed[x] = self.word[x]
                found = True
        self.revealed = "".join(chars_revealed)
        # add word to attempted list, and return results
        self.guessed.append(letter.lower())

        if self.word.lower() == self.revealed.lower():
            return True
        
        if not found:
            self.lives-=1
        
        if self.lives<=0:
            return True
        return False

class Fun():
    def __init__(self, client):
        self.client = client
        self.hangman_in_progress = []
    
    @commands.command(aliases=["source", "gitlab", "repo"])
    async def github(self, ctx):
        em = Embed(title="Github link", description="This bot is open source! Check the source, and help development at https://github.com/valknight/discord_message_analytics")
        await ctx.send(embed=em)
    
    @commands.group()
    async def games(self, ctx):
        """Play fun games, right in discord chat!"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Welcome to AGSE's games! To see a full list of what we have, run `help games`")
    
    @games.command()
    async def hangman(self, ctx):
        # these two values multiplied together are total timeout time
        embed = Embed(title="It's hangman time!", color=green)
        await ctx.send(embed=embed)
        timeout_seconds = 3
        timeout_attempts = 5
        def check_message(m):
            return m.channel == ctx.channel and m.author.id != self.client.user.id
        hangman = Hangman()
        timeouts = timeout_attempts
        statuses = []
        while True:
            def generate_embed():
                a = Embed(title="Current status", description="Your word is `{}` - it is {} letters long\nPlease make a guess".format(hangman.format_reveal(), len(hangman.revealed), timeouts*timeout_seconds), color=yellow)
                a.add_field(name="Time left", value="{} seconds".format(timeouts*timeout_seconds))
                a.add_field(name="Lives", value="{} lives".format(hangman.lives))
                a.set_footer(text="To stop, type `quit` (this works even if you didn't start this) - use this if a word is not appropriate, as a quit game won't tell you the correct word")
                return a
            message = await ctx.send(embed=generate_embed(), delete_after=(timeout_seconds*timeout_attempts+5))
            statuses.append(message)
            while True:
                try:
                    msg = await self.client.wait_for('message', check=check_message, timeout=timeout_seconds)
                    break
                except concurrent.futures._base.TimeoutError:
                    await message.edit(embed=generate_embed())
                    timeouts-=1
                    if timeouts<=0:
                        break
            if timeouts<=0 or msg.content.lower() == "quit":
                break
            if len(msg.content)>1:
                await ctx.send(embed=discord.Embed(title="Invalid letter", description="{}, your guess `{}` is too long! Go for only one letter at a time".format(msg.author.nick, msg.content)), delete_after=timeouts*timeout_seconds+5)
                timeouts = timeout_attempts
            elif msg.content.lower() in hangman.guessed:
                await ctx.send(embed=discord.Embed(title="Move already made!", description="{}, your guess has already been made. Be unique!".format(msg.author.nick)), delete_after=timeouts*timeout_seconds+5)
            else:
                if(hangman.check_letter(msg.content)):
                    break
                else:
                    if msg.content.lower() in hangman.revealed.lower():
                        await ctx.send(embed=Embed(title="{} , you found a letter!".format(msg.author.nick), color=green), delete_after=15)
                    else:
                        await ctx.send(embed=Embed(title="Uh oh, `{}` was not in the word : -1 life".format(msg.content.lower()), color=red), delete_after=15)
                timeouts = timeout_attempts
        
        success_embed = Embed(title="Congratulations!", description="You managed to guess the word `{}` with {} lives remaining!".format(hangman.word, hangman.lives), color=green)
        failiure_generic = Embed(title="You lost", description="The word was `{}` - better luck next time".format(hangman.word), color=red)
        failiure_quit = Embed(title="Quit", description="The game has been stopped. Come back soon!", color=red)
        failiure_timeout = Embed(title="Ran out of time", description="No one made a guess fast enough. The word was `{}`".format(hangman.word), color=red)
        failiure_no_lives = Embed(title="You ran out of lives", description="You guessed wrong one too many times, and dropped out of the game - the word was `{}`. Better luck next time!".format(hangman.word), color=red)
        if hangman.word.lower() == hangman.revealed.lower():
            embed = success_embed
        elif hangman.lives<= 0:
            embed = failiure_no_lives
        elif timeouts<=0:
            embed = failiure_timeout
        elif msg.content.lower() == "quit":
            embed = failiure_quit
            for message in statuses:
                try:
                    await message.delete()
                except discord.errors.NotFound:
                    pass
        else:
            embed = failiure_generic
        
        await ctx.send(embed=embed)


def setup(client):
    client.add_cog(Fun(client))
