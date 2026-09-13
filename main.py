import discord
from discord.ext import commands
import asyncio
import config

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=config.PREFIX, intents=intents, help_command=None)

EXTENSIONS = [
    "cogs.moderation",
    "cogs.leveling",
    "cogs.economy",
    "cogs.automod",
    "cogs.fun",
    "cogs.tickets",
    "cogs.utility",
    "cogs.help",
]

@bot.event
async def on_ready():
    print(f"✅ Loggato come {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Sincronizzati {len(synced)} slash command")
    except Exception as e:
        print(f"Errore sync: {e}")

async def main():
    async with bot:
        for ext in EXTENSIONS:
            try:
                await bot.load_extension(ext)
                print(f"✅ Estensione caricata: {ext}")
            except Exception as e:
                print(f"❌ Errore caricando {ext}: {e}")
        await bot.start(config.TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
