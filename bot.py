import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

queues = {}
looping = {}
volumes = {}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True
}

# ---------------- READY ----------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ---------------- JOIN ----------------
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
    else:
        await ctx.send("Join a voice channel first")

# ---------------- LEAVE ----------------
@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()

# ---------------- PLAY ----------------
@bot.command()
async def play(ctx, *, query):
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("Join a voice channel first")
            return

    guild_id = ctx.guild.id

    queues.setdefault(guild_id, [])
    looping.setdefault(guild_id, False)
    volumes.setdefault(guild_id, 0.5)

    queues[guild_id].append(query)

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

async def play_next(ctx):
    guild_id = ctx.guild.id
    vc = ctx.voice_client

    if not queues[guild_id]:
        return

    if looping[guild_id]:
        query = queues[guild_id][0]
    else:
        query = queues[guild_id].pop(0)

    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)
        url = info['entries'][0]['url']
        title = info['entries'][0]['title']

    source = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS),
        volume=volumes[guild_id]
    )

    def after_playing(e):
        asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

    vc.play(source, after=after_playing)

    await ctx.send(f"🎵 Now playing: {title}")

# ---------------- VOLUME ----------------
@bot.command()
async def volume(ctx, vol: int):
    guild_id = ctx.guild.id

    if 0 <= vol <= 100:
        volumes[guild_id] = vol / 100
        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source.volume = volumes[guild_id]
        await ctx.send(f"🔊 Volume set to {vol}%")
    else:
        await ctx.send("Enter value between 0-100")

# ---------------- LOOP ----------------
@bot.command()
async def loop(ctx):
    guild_id = ctx.guild.id
    looping[guild_id] = not looping.get(guild_id, False)
    status = "ON" if looping[guild_id] else "OFF"
    await ctx.send(f"🔁 Loop is now {status}")

# ---------------- SKIP ----------------
@bot.command()
async def skip(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()

# ---------------- PAUSE ----------------
@bot.command()
async def pause(ctx):
    if ctx.voice_client:
        ctx.voice_client.pause()

# ---------------- RESUME ----------------
@bot.command()
async def resume(ctx):
    if ctx.voice_client:
        ctx.voice_client.resume()

# ---------------- QUEUE ----------------
@bot.command()
async def queue(ctx):
    guild_id = ctx.guild.id
    if queues.get(guild_id):
        q = "\n".join(queues[guild_id])
        await ctx.send(f"📜 Queue:\n{q}")
    else:
        await ctx.send("Queue empty")

# ---------------- TOKEN ----------------
bot.run(os.getenv("TOKEN"))