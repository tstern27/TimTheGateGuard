import discord
import yt_dlp
import asyncio
import logging
import sys

# Suppress noise about console usage from errors
yt_dlp.utils.bug_reports_message = lambda: ''

logger = logging.getLogger('YTDLSource')

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
        
        # Basic URL validation
        if not url or not isinstance(url, str):
            raise ValueError("Invalid URL provided")
        
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        
        try:
            # Use asyncio.timeout for Python 3.11+, fallback to async_timeout for older versions
            if hasattr(asyncio, 'timeout'):
                # Python 3.11+
                timeout_context = asyncio.timeout(30)
            else:
                # Python < 3.11 fallback
                from async_timeout import timeout
                timeout_context = timeout(30)
            
            async with timeout_context:
                # Run extract_info in executor to prevent blocking
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

                if data is None:
                    raise ValueError("Could not fetch video data")

                if 'entries' in data:
                    # Handle playlists - take first item
                    if not data['entries']:
                        raise ValueError("Playlist is empty")
                    data = data['entries'][0]
                    if data is None:
                        raise ValueError("Could not extract video data from playlist")

                filename = data.get('url') if stream else ytdl.prepare_filename(data)
                if not filename:
                    raise ValueError("Could not determine audio source URL")

                # Combine pre_op with other FFmpeg options
                if 'before_options' in ffmpeg_options:
                    ffmpeg_options['before_options'] = f"{pre_op} {ffmpeg_options['before_options']}"
                else:
                    ffmpeg_options['before_options'] = pre_op

                try:
                    return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
                except Exception as e:
                    logger.error(f"Error creating FFmpeg audio: {e}")
                    raise

        except asyncio.TimeoutError:
            logger.error("Timeout while fetching video data")
            raise
        except Exception as e:
            logger.error(f"Error in YTDLSource.from_url: {e}")
            raise