# ===================== Deadside Stats Bot — Русская версия =====================

import os, csv, asyncio, paramiko, discord

from datetime import datetime, timedelta, timezone

from collections import Counter, defaultdict

from discord.ext import commands, tasks


TOKEN       = "MTQzMTcxNTM1MDE1NTg5MDc0OQ.GWFk_V.sJj2tgG0gbINhXbP9HeWjOZR6O8MUtqswkZy4o"

SFTP_HOST   = "91.218.113.132"

SFTP_PORT   = 8822

SFTP_USER   = "bogdang"

SFTP_PASS   = "Im4b83jYy4"

SFTP_DIR    = "/91.218.113.132_7340/Deadside/Saved/actual1/deathlogs/world_0"


CHANNEL_STATS_ID = 1432102681371217930      # 📊 Статистика

CHANNEL_FEED_ID  = 1432119029518303454      # 💀 Килл-чат

UPDATE_EVERY_MINUTES = 1

TOP_N = 20

CACHE_DIR = "ftp_cache"

MOSCOW_TZ = timezone(timedelta(hours=3))


paramiko.Transport._preferred_kex  = ('diffie-hellman-group14-sha1','diffie-hellman-group1-sha1')

paramiko.Transport._preferred_keys = ('ssh-rsa',)


intents = discord.Intents.default()

bot = commands.Bot(command_prefix="/", intents=intents)


_stats = defaultdict(lambda: {"kills": 0, "deaths": 0, "weapons": Counter(), "max_distance": 0})

_last_stats_message_id = None

_last_feed_message_id = None


def _parse_int_distance(s):

    return int(''.join(ch for ch in str(s) if ch.isdigit()) or 0)


def download_latest_csv_sync():

    os.makedirs(CACHE_DIR, exist_ok=True)

    try:

        t = paramiko.Transport((SFTP_HOST, SFTP_PORT))

        t.connect(username=SFTP_USER, password=SFTP_PASS)

        s = paramiko.SFTPClient.from_transport(t)

        files = sorted([f for f in s.listdir(SFTP_DIR) if f.lower().endswith(".csv")])

        if not files: return None

        latest = files[-1]

        remote, local = f"{SFTP_DIR}/{latest}", os.path.join(CACHE_DIR, latest)

        s.get(remote, local)

        print(f"✅ Скачан лог: {latest}")

        return local

    except Exception as e:

        print("Ошибка SFTP:", e)

        return None

    finally:

        try: s.close(); t.close()

        except: pass


def load_stats_from_csv_sync(path):

    stats = defaultdict(lambda: {"kills": 0, "deaths": 0, "weapons": Counter(), "max_distance": 0})

    kills = []

    for enc in ("utf-8-sig", "utf-8", "cp1251"):

        try:

            with open(path, encoding=enc) as f:

                for row in csv.reader(f, delimiter=";"):

                    if len(row) < 7: continue

                    t,kid,_,vid,_,weapon,dist = row[:7]

                    dist = _parse_int_distance(dist)

                    if kid: stats[kid]["kills"] += 1; stats[kid]["weapons"][weapon]+=1; stats[kid]["max_distance"]=max(stats[kid]["max_distance"], dist)

                    if vid: stats[vid]["deaths"] += 1

                    kills.append((t,kid,vid,weapon,dist))

            return stats,kills

        except: continue

    return stats,kills


def build_top_embed(stats):

    pairs = sorted(stats.items(), key=lambda kv: kv[1]["kills"], reverse=True)[:TOP_N]

    desc = []

    for i,(name,d) in enumerate(pairs,1):

        kd = round(d["kills"]/d["deaths"],2) if d["deaths"]>0 else d["kills"]

        fav = d["weapons"].most_common(1)[0][0] if d["weapons"] else "—"

        desc.append(f"**{i}. {name}**\n🔫 Убийств: {d['kills']} | 💀 Смертей: {d['deaths']} | ⚖️ K/D: {kd}\n🎯 Оружие: {fav} | 📏 Макс. дистанция: {d['max_distance']} м\n────────────────────")

    return discord.Embed(title="🏆 Топ-20 игроков RELAX FREEDOM", description="\n".join(desc) or "Нет данных.", color=discord.Color.green())


def build_killfeed_embed(kills, filename):

    try:

        dt = datetime.strptime(filename.split("/")[-1].split(".csv")[0], "%Y.%m.%d-%H.%M.%S").replace(tzinfo=timezone.utc).astimezone(MOSCOW_TZ)

        log_time = dt.strftime("%d.%m.%Y, %H:%M")

    except: log_time = "неизвестно"

    blocks=[]

    for t,killer,victim,weapon,dist in kills[-10:]:

        blocks.append(

            f"🎯 **Новое убийство**\n"

            f"👤 Убийца: **{killer or '—'}**\n"

            f"💀 Жертва: **{victim or '—'}**\n"

            f"🔫 Оружие: **{weapon or '—'}**\n"

            f"📏 Дистанция: **{dist} м**\n"

            f"⏰ Время: **{log_time} (МСК)**\n"

            f"═══════════════════════"

        )

    return discord.Embed(title="💀 Килл-чат — последние 10 убийств", description="\n".join(blocks) or "Пока нет убийств.", color=discord.Color.red())


@tasks.loop(minutes=UPDATE_EVERY_MINUTES)

async def periodic_update():

    global _stats, _last_stats_message_id, _last_feed_message_id

    local = await asyncio.to_thread(download_latest_csv_sync)

    if not local: return

    _stats,kills = await asyncio.to_thread(load_stats_from_csv_sync, local)


    chs, chf = bot.get_channel(CHANNEL_STATS_ID), bot.get_channel(CHANNEL_FEED_ID)

    if chs:

        emb = build_top_embed(_stats)

        try:

            if _last_stats_message_id:

                msg=await chs.fetch_message(_last_stats_message_id); await msg.edit(embed=emb)

            else:

                msg=await chs.send(embed=emb); _last_stats_message_id=msg.id

        except: msg=await chs.send(embed=emb); _last_stats_message_id=msg.id

    if chf:

        emb = build_killfeed_embed(kills, local)

        try:

            if _last_feed_message_id:

                msg=await chf.fetch_message(_last_feed_message_id); await msg.edit(embed=emb)

            else:

                msg=await chf.send(embed=emb); _last_feed_message_id=msg.id

        except: msg=await chf.send(embed=emb); _last_feed_message_id=msg.id


@bot.event

async def on_ready():

    print(f"✅ Бот запущен как {bot.user}")

    await bot.change_presence(activity=discord.Game("Deadside Stats 📊"))

    periodic_update.start()


bot.run(TOKEN)


# ==============================================================
