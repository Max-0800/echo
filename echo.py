print("Initializing...")

import discord, asyncio, io, psutil, pytz, yt_dlp, subprocess, edge_tts
from datetime import datetime
from pynvml import *
from discord.ext import commands
from ollama import AsyncClient

nvmlInit()
client = AsyncClient()
intents = discord.Intents.default()
intents.message_content, intents.guilds, intents.members = True, True, True
bot = commands.Bot(command_prefix="/", intents=intents)

instructions = f"You are allowed to curse/swear when necessary."
persona0 = f"{instructions} You are an AI built to provide and assist and every name that speaks is a real person that you do not question."

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "nocheckcertificate": True,
    "quiet": True,
    "default_search": "auto"
}
FFMPEG_OPTIONS = {
    "options": "-vn",
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
}
ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.title = data.get("title")

    @classmethod
    async def from_input(cls, input, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(input, download=False))
        if "entries" in data:
            data = data["entries"][0]
        return cls(discord.FFmpegPCMAudio(data["input"], **FFMPEG_OPTIONS), data=data)

result = subprocess.run("ollama ps".split(), capture_output=True, text=True)
llm_status = len(str(result.stdout).splitlines())

history = [{'role': 'system', "content": persona0}]
model = "artifish/llama3.2-uncensored:latest"
TOKEN = ""
ai_toggle = False

# TTS
async def tts(txt):
    communicate = edge_tts.Communicate(txt, "en-US-AvaMultilingualNeural", rate="+20%")
    await communicate.save("output.mp3")
    print("Passed TTS generation.")

# LLM I/O
async def llm(ctx):
    global history

    print(f"\n{ctx.author} prompted: {ctx.content}")
    try:
        async with ctx.channel.typing():
            print("Generating...")
            prompt = ctx.content.lower().replace("echo", "")
            history.append({'role': 'user', "content": prompt})
            response = await client.chat(model=model, messages=history, keep_alive=-1)
            response = response.message.content
            print(f"LLM reply: {response}")
        if len(response) >= 2000:
            file = discord.File(io.BytesIO(response.encode('utf-8')), filename="response.txt")
            await ctx.reply(f"The text exceeded the 2,000 character limit ({len(response)} chars), TTS will not be generated so here is a file!", file=file)
            history.append({'role': 'assistant', "content": response})
            return
        else:
            await asyncio.gather(
                ctx.reply(response),
                tts(response)
            )
            await ctx.channel.send("Voice output.", file=discord.File("output.mp3"))
            history.append({'role': 'assistant', "content": response})
    except Exception as e:
        print(str(e))

# CHAT LISTENER
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    elif message.content.startswith("/"):
        return await bot.process_commands(message)

    msg = message.content.lower()
    if "echo" in msg:
        return await llm(message)
    elif ai_toggle == True:
        await llm(message)

# BOT COMMANDS

@bot.command()
async def play(ctx, *, url: str):  # Added '*' so search queries with multiple words don't break
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            return await ctx.send("Join a voice channel first!")

    async with ctx.typing():
        try:
            player = await YTDLSource.from_input(url, loop=bot.loop)
            await asyncio.gather(
                ctx.voice_client.play(player),
                print(f"playing: {player.title}"),
                ctx.send(f"🎵 **Now playing:** `{player.title}`")
            )

        except Exception as e:
            await ctx.voice_client.disconnect()
            await ctx.send(f"Error: {e}")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("`Disconnected.`")

@bot.command()
async def pc(ctx):
    mem = psutil.virtual_memory()
    handle = nvmlDeviceGetHandleByIndex(0)
    info = nvmlDeviceGetMemoryInfo(handle)
    used_vram = info.used / 1024 ** 2
    free_vram = info.free / 1024 ** 2
    summary = f"""
# GPU
GTX 1650 Max-Q 4GB
```Used VRAM: {used_vram:.0f} MB
Free VRAM: {free_vram:.0f} MB```
# RAM
16GB DDR4 3200Mhz
```Used: {mem.used / (1024 ** 3):.2f} GB
Free: {mem.available / (1024 ** 3):.2f} GB```"""
    print(summary)
    await ctx.send(summary)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def ai(ctx, *, args):
    global history, ai_toggle
    try:
        if args == "save":
            with open("../history.txt", "w") as f:
                f.write(str(history))
                print("Successfully saved chat history")
                await ctx.send("Successfully saved chat history.")
        elif args == "reset":
            history = [{'role': 'system', "content": persona0}]
            await client.chat(model=model, messages=history, keep_alive=-1)
            print("AI: Conversation memory and parameters have been reset.")
            await ctx.send("`AI: Conversation memory and parameters have been reset.`")
        elif args == "shutdown":
            await ctx.send("`Goodbye.`")
            exit()
        elif args == "toggle":
            if ai_toggle:
                ai_toggle = False
                print("AI: Echo will no longer listen to all messages")
                await ctx.send("`AI: Echo will no longer listen to all messages`")
            else:
                ai_toggle = True
                print("AI: Echo will now listen to every message")
                await ctx.send("`AI: Echo will now listen to every message`")
    except Exception as e:
        print(str(e))
        await ctx.send(str(e))

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    try:
        await ctx.channel.purge(limit=amount+1)
    except discord.Forbidden:
        await ctx.channel.send("Error: could not purge.")

@bot.command()
async def kill(ctx):
    global history
    with open("../history.txt", "w") as f:
        for item in history:
            f.write(f"{item}\n")
        print("Successfully saved chat history. Going offline.")
        ctx.send("Successfully saved chat history. Going offline.")
    exit() > null

@bot.event
async def on_ready():
    if llm_status == 2:
        print("LLM is online")
    else:
        print("LLM is offline")
    print(f"{bot.user} initialization complete.")

if __name__ == '__main__':
    bot.run(TOKEN)