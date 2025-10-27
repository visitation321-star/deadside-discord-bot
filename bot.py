# ===================== Deadside Stats Bot — Render Edition (Русская версия) =====================
import os, csv, asyncio, paramiko, discord
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict
from discord.ext import commands, tasks

# === Настройки соединения и каналов ===
SFTP_HOST = "91.218.113.132"
SFTP_PORT = 8822
SFTP_USER = "bogdang"
SFTP_PASS = "Im4b83jYy4"
SFTP_DIR = "/91.218.113.132_7340/Deadside/Saved/actual1/deathlogs/world_0"

CHANNEL_STATS_ID = 1432102681371217930  # 📊 Статистика
CHANNEL_FEED_ID = 1432119029518303454   # 💀 Килл-чат
UPDATE_EVERY_MINUTES = 1
TOP_N = 20
CACHE_DIR = "ftp_cache"

# === Временная зона Москва ===
MOSCOW_TZ = timezone(timedelta(hours=3))

# === Discord intents ===
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# === Внутренние переменные ===
_stats = defaultdict(lambda: {"kills": 0, "deaths": 0, "weapons": Counter(), "max_distance": 0})
_last_stats_message_id = None
_last_feed_message_id = None

# === Настройка Paramiko (для старых серверов) ===
paramiko.Transport._preferred_kex = ('diffie-hellman-group14-sha1', 'diffie-hellman-group1-sha1')
paramiko.Transport._preferred_keys = ('ssh-rsa',)

# === Функции ===
# === Цикл обновления ===
# === Запуск ===
@bot.event
async def on_ready():
    print(f"✅ Бот запущен как {bot.user}")
    await bot.change_presence(activity=discord.Game("Deadside Stats 📊"))
    periodic_update.start()

# === Токен из переменных окружения ===
if __name__ == "__main__":
    token = os.getenv("TOKEN")
    if not token:
        print("❌ Ошибка: TOKEN не найден! Добавь его в Environment Variables на Render.")
    else:
        bot.run(token)
