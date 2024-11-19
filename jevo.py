import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Carga el token del archivo .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} está en línea.')

async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')

@bot.command()
@commands.has_permissions(administrator=True)
async def reload(ctx, extension):
    await bot.unload_extension(f'cogs.{extension}')
    await bot.load_extension(f'cogs.{extension}')
    await ctx.send(f'{extension} ha sido recargado.')

async def main():
    await load_extensions()
    await bot.start(TOKEN)

import asyncio
asyncio.run(main())
