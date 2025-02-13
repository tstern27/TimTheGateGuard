import discord
import yt_dlp
import asyncio
from async_timeout import timeout  # You might need to pip install async-timeout

# Suppress noise about console usage from errors
yt_dlp.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
    'extract_flat': 'in_playlist'  # Don't download entire playlists
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, ffmpeg_options, pre_op, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        
        try:
            async with timeout(30):  # 30 second timeout
                # Run extract_info in executor to prevent blocking
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

                if data is None:
                    raise ValueError("Could not fetch video data")

                if 'entries' in data:
                    # take first item from a playlist
                    data = data['entries'][0]

                filename = data['url'] if stream else ytdl.prepare_filename(data)
                
                # Combine pre_op with other FFmpeg options
                if 'before_options' in ffmpeg_options:
                    ffmpeg_options['before_options'] = f"{pre_op} {ffmpeg_options['before_options']}"
                else:
                    ffmpeg_options['before_options'] = pre_op

                try:
                    return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
                except Exception as e:
                    print(f"Error creating FFmpeg audio: {e}")
                    raise

        except asyncio.TimeoutError:
            print("Timeout while fetching video data")
            raise
        except Exception as e:
            print(f"Error in YTDLSource.from_url: {e}")
            raise