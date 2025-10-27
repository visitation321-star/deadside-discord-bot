import discord
from discord.ext import tasks, commands
import asyncio
import csv
import datetime
import os
import pytz

# === НАСТРОЙКИ ===
TOKEN = "ВСТАВЬ_СВОЙ_ТОКЕН_БОТА"  # вставь сюда токен из Discord Developer Portal
KILL_LOG_PATH = r"/91.218.113.132_7340/Deadside/Saved/actual1/deathlogs/world_0"
STATS_CHANNEL_ID = 1432119029518303454     # канал для статистики
KILLFEED_CHANNEL_ID = 1432119029518303454  # канал для кил-чата (можно другой ID)
TIMEZONE = pytz.timezone("Europe/Moscow")

intents = discord.Intents.default()
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# === ФУНКЦИИ ===
def parse_log_line(line):
    parts = line.strip().split(";")
    if len(parts) < 8:
        return None
    return {
        "time": parts[0],
        "killer": parts[1],
        "victim": parts[3],
        "weapon": parts[5],
        "distance": parts[7]
    }

def load_kill_data():
    kills = []
    if not os.path.exists(KILL_LOG_PATH):
        return kills

    with open(KILL_LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if parsed := parse_log_line(line):
                kills.append(parsed)
    return kills[-10:]  # последние 10 убийств

def build_killfeed_embed(kills):
    embed = discord.Embed(
        title="💀 Лента убийств — последние 10 событий",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(TIMEZONE)
    )
    for k in kills:
        embed.add_field(
            name=f"💥 {k['killer']} убил {k['victim']}",
            value=f"🔫 Оружие: **{k['weapon']}**\n📏 Дистанция: **{k['distance']}м**\n🕓 Время: {k['time']}",
            inline=False
        )
    embed.set_footer(text="Обновляется каждую минуту (время сервера — Москва)")
    return embed

# === ЗАПУСК ===
@bot.event
async def on_ready():
    print(f"✅ Бот запущен как {bot.user}")
    update_killfeed.start()

@tasks.loop(minutes=1)
async def update_killfeed():
    try:
        kills = load_kill_data()
        channel = bot.get_channel(KILLFEED_CHANNEL_ID)
        if not channel:
            print("❌ Канал не найден!")
            return

        embed = build_killfeed_embed(kills)
        async for msg in channel.history(limit=1):
            await msg.edit(embed=embed)
            break
        else:
            await channel.send(embed=embed)

        print("✅ Лента убийств обновлена.")
    except Exception as e:
        print(f"⚠️ Ошибка при обновлении: {e}")

bot.run(TOKEN)
