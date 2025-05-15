import discord
from discord.ext import commands
from discord.ui import Button, View
import logging
from dotenv import load_dotenv
import os
import random
from blackjackBot import Blackjack
import webserver

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="?", intents=intents)

secret_role = "new role"

@bot.event
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")
    await bot.add_cog(Blackjack(bot))

@bot.event
async def on_member_join(member):
    await member.send(f"Welcome to the server {member.name}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if "nigger" in message.content.lower():
        await message.delete()
        await message.channel.send(f"{message.author.mention} - dont use that word!")

    await bot.process_commands(message)

@bot.command()
async def hello(ctx):
    await  ctx.send(f"Hello {ctx.author.mention}!")

@bot.command()
async  def dm(ctx, *, msg):
    await ctx.author.send(f"You said {msg}")

@bot.command()
async def reply(ctx):
    await ctx.reply("This is a reply to your message!")

@bot.command()
async def poll(ctx, *, question):
    embed = discord.Embed(title="New Poll", description=question)
    poll_message = await ctx.send(embed=embed)
    await poll_message.add_reaction("❤️")
    await poll_message.add_reaction("😍")

@bot.command()
@commands.has_role(secret_role)
async def secret(ctx):
    await ctx.send("Welcome to the club!")

@secret.error
async  def secret_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("You do not have permission to do that!")

webserver.keep_alive()
bot.run(token, log_handler=handler, log_level=logging.DEBUG)
