import discord
from discord.ext import commands
import yt_dlp
import asyncio
import subprocess
import json
import os
import random
import math
import time

# #yt-dlp自動更新
# def auto_update_yt_dlp():
#     try:
#         result = subprocess.run(['yt-dlp', '-U'], capture_output=True, text=True)
#         if "Updated" in result.stdout:
#             print("[yt-dlp]已自動更新")
#         elif "yt-dlp is up to date" in result.stdout:
#             print("[yt-dlp]已是最新版本")
#         else:
#             print("[yt-dlp]更新狀態不明：", result.stdout)
#     except Exception as e:
#         print(f"[yt-dlp]自動更新失敗：{e}")

# auto_update_yt_dlp()

#設定 intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# FFMPEG播放參數
FFMPEG_OPTIONS = {'before_options':'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5' , 'options' : '-vn -bufsize 64k'}

# YT_DLP播放參數
YDL_OPTIONS = {
    'format': 'bestaudio',
    'noplaylist': True,
    'quiet': True,
    'ignoreerrors': True,
    'default_search': 'ytsearch',
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'source_address': '0.0.0.0',
    'cookiefile': 'cookies.txt'
}

HISTORY_FILE = "history.json"

def load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        print("[警告] 無法載入 history.json, 回傳空列表")
        return []
    
def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history[-100:], f, indent=4, ensure_ascii=False)

class MusicBot(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.queue = []
        self.repeat = False
        self.current_url = None
        self.current_title = None
        self.current_video_info = None
        self.disconnect_task= None
        self.history = load_history()
        self.start_time = 0
        self.duration = 0

    @commands.command(name="help") #指令說明
    async def commands_help(self, ctx):
        help_text = (
            "**🎶 EN專屬 指令說明：**\n\n"
            "`!play <歌曲名稱或YouTube連結>` - 播放音樂或加入歌單中\n"
            "`!skip` - 跳過目前歌曲\n"
            "`!queue` - 顯示目前所有歌單\n"
            "`!np` - 顯示目前播放歌曲\n"
            "`!stop` - 停止目前播放歌曲\n"
            "`!start` - 繼續播放目前歌曲\n"
            "`!repeat` - 重複播放目前歌曲\n"
            "`!delete 編號` - 刪除指定歌曲\n"
            "`!history` - 查看歷史播放紀錄\n"
            "`!select` - 從歷史紀錄中隨機播放歌曲\n"
            "`!select 編號` - 從歷史紀錄中指定播放歌曲\n"
            "`!help` - 顯示指令幫助列表\n\n"
            "`!special` - 特別的"

        )
        await ctx.send(help_text)

#special
    @commands.command()
    async def special(self, ctx):
        allowed_user_id = 1193270988700393502
        if ctx.author.id == allowed_user_id:
            await ctx.send("想我啦主人~人家也好想妳喔!")
        else:
            await ctx.send("喊啥呢？啥身分跟我喊！我呸")

#切換repeat模式
    @commands.command() 
    async def repeat(self, ctx):
        self.repeat = not self.repeat
        if self.repeat:
            await ctx.send("重複目前歌曲：啟用")
        else:
            await ctx.send("重複目前歌曲：停用")

#播放下一首歌
    async def play_next(self, ctx):
        voice_client = ctx.voice_client
        
        def after_playing(error):
            if error:
                print(f"[錯誤] 播放中途出錯:{error}")
            try:
                self.client.loop.create_task(self.play_next(ctx))
            except Exception as e:
                print(f'[例外] 播放下一首發生錯誤:{e}')

#repeat模式重播目前歌曲
        if self.repeat and self.current_url:
            try:
                source = await discord.FFmpegOpusAudio.from_probe(self.current_url, **FFMPEG_OPTIONS)
                voice_client.play(source, after=after_playing)
                await ctx.send(f'重複播放 **{self.current_title}**')
            except Exception as e:
                await ctx.send("重複播放失敗，跳過此首")
                print(f'[錯誤] 重複播放失敗:{e}')
                await self.play_next(ctx)
            return

#播放下一首歌
        if self.queue:
            url, video_info = self.queue.pop(0)
            self.current_url = url
            self.current_title = video_info['title']
            self.current_video_info = video_info
            try:
                source = await discord.FFmpegOpusAudio.from_probe(self.current_url, **FFMPEG_OPTIONS)
                voice_client.play(source, after=after_playing)
                await ctx.send(f'現在播放 **{self.current_title}**')
            except Exception as e:
                await ctx.send(f"播放 **{self.current_title}** 失敗，自動跳過")
                print (f"[錯誤] 播放 {self.current_title} 時失敗")
                await self.play_next(ctx)
        else:
            await ctx.send("歌單現在是空的耶！")
            if not self.disconnect_task:
                self.disconnect_task = self.client.loop.create_task(self.auto_disconnect_task(ctx))

# #歷史紀錄
#     @commands.command()
#     async def history(self, ctx):
#         if not os.path.exists(HISTORY_FILE):
#             return await ctx.send("目前沒有任何播放紀錄")
        
#         with open(HISTORY_FILE, "r", encoding="utf-8") as f:
#             data = json.load(f)
        
#         if not data:
#             return await ctx.send("目前沒有任何播放紀錄")
        
#         per_page = 10
#         total_pages = math.ceil(len(data) / per_page)
#         current_page = 0

#         def get_page_content(page):
#             start = page * per_page
#             end = start + per_page
#             entries = data[start:end]
#             return "\n".join([f"**{i+1+start}.** {item['title']}" for i, item in enumerate(entries)])
        
#         embed = discord.Embed(
#             title="📜歷史記錄：",
#             description=get_page_content(current_page),
#             color=discord.Color.green()
#         )
#         embed.set_footer(text=f"第 {current_page+1} 頁 / 共 {total_pages} 頁")
#         message = await ctx.send(embed=embed)

#         if total_pages <= 1:
#             return
        
#         reactions = ["⏪", "⬅️", "➡️", "⏩"]
#         for r in reactions:
#             await message.add_reaction(r)

#         def check(reaction, user):
#             return(
#                 user == ctx.author and
#                 reaction.message.id == message.id and
#                 str(reaction.emoji) in reactions
#             )
        
#         while True:
#             try:
#                 reaction, user = await self.client.wait_for("reaction_add", timeout= 60.0,check=check)
#                 emoji = str(reaction.emoji)

#                 if emoji == "⏪":
#                     current_page = 0
#                 elif emoji == "⬅️" and current_page > 0:
#                     current_page -= 1
#                 elif emoji == "➡️" and current_page < total_pages - 1:
#                     current_page += 1
#                 elif emoji == "⏩":
#                     current_page = total_pages - 1
#                 embed.description = get_page_content(current_page)
#                 embed.set_footer(text=f"第 {current_page+1} 頁 / 共 {total_pages} 頁")
#                 await message.edit(embed=embed)
#                 await message.remove_reaction(reaction.emoji, user)
#             except asyncio.TimeoutError:
#                 try:
#                     await message.clear_reactions()
#                 except discord.Forbidden:
#                     pass
#                 break

#播放新歌曲或加入隊列
    @commands.command()
    async def play(self, ctx, *, search):
        if self.disconnect_task:
            self.disconnect_task.cancel()
            self.disconnect_task = None
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None
        if not voice_channel:
            return await ctx.send("進房間才能使用人家唷")
        if not ctx.voice_client:
            await voice_channel.connect()

        async with ctx.typing():
            try:
                with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                # ✅ 判斷是網址還是關鍵字
                    if search.startswith("http://") or search.startswith("https://"):
                        info = ydl.extract_info(search, download=False)
                    else:
                        info = ydl.extract_info(f"ytsearch1:{search}", download=False)
                        if 'entries' in info and info['entries']:
                            info = info['entries'][0]

                if not info:
                    await ctx.send(f"找不到 {search} 相關歌曲")
                    return
                
                stream_url = info.get('url')
                if not stream_url:
                    await ctx.send("出錯了，請再嘗試點播一次，抱歉")
                    return
            
                video_info = {
                    'title': info.get('title'),
                    'webpage_url': info.get('webpage_url'),
                    'channel': info.get('channel', '未知頻道'),
                    'thumbnail': info.get('thumbnail'),
                    'stream_url': stream_url
                    }
                self.queue.append((stream_url, video_info))
                await ctx.send(f'加入歌單: **{video_info["title"]}**')
            except Exception as e:
                await ctx.send(f"取得歌曲時發生錯誤：{e}")
                print(f"[錯誤] play指令抓取錯誤")
                return
    
            if not ctx.voice_client.is_playing():
                url, video_info = self.queue.pop(0)
                self.current_url = url
                self.current_title = video_info['title']
                if self.disconnect_task:
                    self.disconnect_task.cancel()
                    self.disconnect_task = None
                try:
                    source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
                    ctx.voice_client.play(
                        source,
                        after=lambda e: self.client.loop.create_task(self.play_next(ctx))
                    )
                    await ctx.send(f'現在播放 **{video_info["title"]}**')

                    self.history.append({
                        "title": video_info['title'],
                       "url": video_info['webpage_url'],
                        "channel": video_info['channel']
                    })
                    save_history(self.history)
                except Exception as e:
                    await ctx.send(f"出錯了，請再嘗試點播一次，抱歉")
                    print(f"[錯誤] 播放失敗：{e}")

                    self.start_time = time.time()
                    self.duration = info.get("duration", 0)
                    self.current_video_info = info

#跳過歌曲
    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("已跳過目前播放歌曲 ")

#刪除指定歌曲
    @commands.command()
    async def delete(self, ctx, index:int):
        if not self.queue:
            await ctx.send("歌單目前是空的，沒有歌曲可以刪除")
            return
    
        if index < 1 or index > len(self.queue):
            await ctx.send(f"編號錯誤，請輸入 1 到 {len(self.queue)} 之間的數字")
            return
    
        removed_song = self.queue.pop(index-1)
        await ctx.send (f"已從歌單刪除第 {index} 首歌：**{removed_song[1]['title']}**")

#歷史紀錄選歌
    @commands.command()
    async def select(self, ctx, index: str = None):
        history = load_history()
        if not history:
            await ctx.send("歷史紀錄是空的")
            return
        if index and index.isdigit():
            idx = int(index) - 1
            if idx < 0 or idx >= len(history):
                await ctx.send(f"編號超出範圍，目前有 {len(history)} 筆紀錄")
                return
            song = history[idx]
        else:
            song = random.choice(history)
        
        video_url = song["url"]

        try:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(video_url, download=False)
                stream_url = info.get('url')
                if not stream_url:
                    await ctx.send("無法取得音訊串流，請稍後再試")
                    return
                
        except Exception as e:
            await ctx.send(f"取得音訊串流錯誤：{e}")
            return
        
        self.queue.append((stream_url, song))
        await ctx.send(f"隨機挑了一首： **{song['title']}**, 並加入歌單中")

        if not ctx.voice_client:
            voice_channel = ctx.author.voice.channel if ctx.author.voice else None
            if voice_channel:
                await voice_channel.connect()
            else:
                await ctx.send("又不在語音！等你進來再播！")
                return
            
        if not ctx.voice_client.is_playing():
            if self.disconnect_task:
                self.disconnect_task.cancel()
                self.disconnect_task = None
            self.current_url = stream_url
            self.current_title = song['title']
            source = await discord.FFmpegOpusAudio.from_probe(stream_url, **FFMPEG_OPTIONS)
            ctx.voice_client.play(
                source,
                after=lambda _: self.client.loop.create_task(self.play_next(ctx))
            )
            await ctx.send(f"現在播放 **{song['title']}**")
        self.start_time = time.time()
        self.duration = info.get("duration", 0)
        self.current_video_info = info


#離開語音頻道
    @commands.command()
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("我走啦~")
        else:
            await ctx.send("我都還沒進頻道就想叫人家走呀！")

#目前播放歌曲資訊
    @commands.command()
    async def np(self, ctx):
        try:
            voice_client = ctx.voice_client
            if voice_client and voice_client.is_playing() and self.current_title:
                info = self.current_video_info
                if isinstance(info, dict) and 'title' in info and 'webpage_url' in info and 'channel' and 'thumbnail' in info:
                    if hasattr(self, "start_time") and hasattr(self.duration, (int, float)) and self.duration > 0:
                        elapsed = time.time() - self.start_time
                        elapsed = min(elapsed, self.duration)

                        def create_progress_bar(current, total, bar_length=20):
                            filled_length = int(bar_length * current // total)
                            bar = "■" * filled_length + "□" * (bar_length - filled_length)
                            return f"[{bar}] {int(current//60)}:{int(current%60):02d} / {int(total//60)}:{int(total%60):02d}"
                        progress_bar = create_progress_bar(elapsed, self.duration)
                    else:
                        progress_bar = "(無法取得播放進度)"

                    embed = discord.Embed(
                        title = info['title'],
                        url = info['webpage_url'],
                        description=f"頻道：{info['channel']}\n\n{progress_bar}",
                        color = discord.Color.blue()
                    )
                    embed.set_thumbnail(url=info['thumbnail'])
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("目前歌曲資訊不完整")
            else:
                await ctx.send("目前沒有播放任何音樂！")
        except Exception as e:
            await ctx.send(f"發生錯誤：{e}")
            print(f"[錯誤] np 指令錯誤：{e}")

#暫停音樂
    @commands.command()
    async def stop(self, ctx):
        voice_client = ctx.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await ctx.send("幹啥暫停呢！我還沒嗨起來！")
        else:
            await ctx.send("目前沒有播放任何音樂！")

#開始音樂
    @commands.command()
    async def start(self, ctx):
        voice_client = ctx.voice_client
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await ctx.send("就是這樣繼續聽！")
        else:
            await ctx.send("目前沒有播放任何音樂！")

#顯示歌單內容
    @commands.command()
    async def queue(self, ctx):
        if not self.queue:
            await ctx.send("歌單現在是空的耶！")
            return
        
        queue_list =""
        for i, (_, video_info) in enumerate(self.queue, start=1):
            queue_list += f"{i}. {video_info['title']}\n"

        await ctx.send(f"目前歌單：\n{queue_list}")

#五分鐘無人使用 自動斷開
    async def auto_disconnect_task(self, ctx):
        await asyncio.sleep(300)
        voice_client = ctx.voice_client
        if voice_client and not voice_client.is_playing():
            await ctx.send("人家五分鐘都沒事做，那我先走好了...")
            await voice_client.disconnect()
            self.disconnect_task = None


#啟動機器人並掛載Cog
client = commands.Bot(command_prefix="!" , intents=intents, help_command=None)

async def main():
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("[部署錯誤] 找不到'DISCORD_TOKEN' 環境變數。")
        return

    async with client:
        await client.add_cog(MusicBot(client))
        await client.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
