# ===================== Deadside Stats Bot — безопасная версия =====================
import os
import csv
import asyncio
from collections import Counter, defaultdict
import paramiko
import discord
from discord.ext import commands, tasks

# ---------- НАСТРОЙКИ ----------
TOKEN = os.getenv("DISCORD_TOKEN")  # токен теперь берется из Render Secrets
SFTP_HOST = "91.218.113.132"
SFTP_PORT = 8822
SFTP_USER = "bogdang"
SFTP_PASS = "Im4b83jYy4"
SFTP_DIR = "/91.218.113.132_7340/Deadside/Saved/actual1/deathlogs/world_0"

CHANNEL_STATS = 1432102681371217930  # 📊 канал статистики
CHANNEL_KILLFEED = 1432119029518303454  # 🔫 кил-чат

UPDATE_EVERY_MINUTES = 1
TOP_N = 20
MESSAGE_ID_FILE = "last_stats_message_id.txt"
CACHE_DIR = "ftp_cache"

# ---------- Фиксы ----------
paramiko.Transport._preferred_kex = (
    "diffie-hellman-group14-sha1", "diffie-hellman-group1-sha1"
)
paramiko.Transport._preferred_keys = ("ssh-rsa",)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

_latest_local_file = None
_stats = defaultdict(lambda: {"kills": 0, "deaths": 0, "weapons": Counter(), "max_distance": 0})
_last_kills = []

# ---------- УТИЛИТЫ ----------
def _parse_int_distance(s):
    if not s:
        return 0
    digits = "".join(ch for ch in str(s) if ch.isdigit())
    return int(digits) if digits else 0

def _detect_fields(fields):
    if not fields:
        return None, None, None, None
    lower = {f.lower(): f for f in fields}
    def find(names):
        for n in names:
            for lk, orig in lower.items():
                if n in lk:
                    return orig
        return None
    return (
        find(["killer", "attacker"]),
        find(["victim", "target"]),
        find(["weapon", "gun"]),
        find(["distance", "range", "meters"]),
    )

# ---------- SFTP ----------
def download_latest_csv():
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASS)
        sftp = paramiko.SFTPClient.from_transport(transport)

        files = [f for f in sftp.listdir(SFTP_DIR) if f.lower().endswith(".csv")]
        if not files:
            print("⚠️ Нет CSV файлов на сервере.")
            return None
        latest = sorted(files)[-1]
        local = os.path.join(CACHE_DIR, latest)
        sftp.get(os.path.join(SFTP_DIR, latest), local)
        sftp.close()
        transport.close()
        print(f"✅ Скачан лог: {latest}")
        return local
    except Exception as e:
        print("❌ Ошибка SFTP:", e)
        return None

# ---------- ОБРАБОТКА CSV ----------
def load_stats(local_path):
    stats = defaultdict(lambda: {"kills": 0, "deaths": 0, "weapons": Counter(), "max_distance": 0})
    kills = []
    for enc in ("utf-8", "utf-8-sig", "cp1251"):
        try:
            with open(local_path, newline="", encoding=enc) as f:
                reader = csv.reader(f, delimiter=";")
                for row in reader:
                    if len(row) < 6:
                        continue
                    _, killer, _, victim, weapon, dist = row
                    killer, victim, weapon = killer.strip(), victim.strip(), weapon.strip()
                    dist = _parse_int_distance(dist)
                    if killer:
                        stats[killer]["kills"] += 1
                        stats[killer]["weapons"][weapon] += 1
                        stats[killer]["max_distance"] = max(stats[killer]["max_distance"], dist)
                    if victim:
                        stats[victim]["deaths"] += 1
                    kills.append((killer, victim, weapon, dist))
                return stats, kills
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            return stats, kills
    return stats, kills

# ---------- EMBED ----------
def build_embed(stats, title="🏆 Топ игроков RELAX FREEDOM (каждую минуту)"):
    sorted_players = sorted(stats.items(), key=lambda kv: kv[1]["kills"], reverse=True)[:TOP_N]
    desc = ""
    for i, (name, data) in enumerate(sorted_players, start=1):
        kd = round(data["kills"] / data["deaths"], 2) if data["deaths"] else data["kills"]
        fav_weapon = data["weapons"].most_common(1)[0][0] if data["weapons"] else "—"
        desc += (
            f"**{i}. {name}**\n"
            f"🔫 Убийств: {data['kills']} 💀 Смертей: {data['deaths']} ⚖️ K/D: {kd}\n"
            f"🎯 Оружие: {fav_weapon} 📏 Макс. дистанция: {data['max_distance']}м\n"
            f"───────────────────────\n"
        )
    return discord.Embed(title=title, description=desc or "Нет данных", color=0x2ecc71)

def build_killfeed(kills):
    desc = "\n".join(
        f"💥 **{k}** убил **{v}** | {w} | {d}м" for k, v, w, d in kills[-10:]
    ) or "Пока убийств нет."
    embed = discord.Embed(title="🎯 Последние убийства", description=desc, color=0xe74c3c)
    return embed

# ---------- ОБНОВЛЕНИЕ ----------
@tasks.loop(minutes=UPDATE_EVERY_MINUTES)
async def update_data():
    global _stats, _last_kills
    local = await asyncio.to_thread(download_latest_csv)
    if not local:
        return
    new_stats, new_kills = await asyncio.to_thread(load_stats, local)
    if new_kills == _last_kills:
        return
    _stats, _last_kills = new_stats, new_kills
    print("📊 Статистика обновлена.")

    ch_stats = bot.get_channel(CHANNEL_STATS)
    ch_kills = bot.get_channel(CHANNEL_KILLFEED)
    if not ch_stats or not ch_kills:
        print("⚠️ Каналы не найдены.")
        return

    await ch_stats.purge(limit=1)
    await ch_kills.purge(limit=1)

    await ch_stats.send(embed=build_embed(_stats))
    await ch_kills.send(embed=build_killfeed(_last_kills))

# ---------- СТАРТ ----------
@bot.event
async def on_ready():
    print(f"✅ Бот запущен как {bot.user}")
    await bot.change_presence(activity=discord.Game("Deadside Killfeed"))
    update_data.start()

bot.run(TOKEN)
# ====================================================================
