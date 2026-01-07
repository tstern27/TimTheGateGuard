# TimTheGateGuard

A Discord music bot that streams audio from various sources (YouTube, and any other source supported by yt-dlp) directly into Discord voice channels. The bot supports timestamp-based playback, allowing you to play specific sections of videos.

## Features

- **Multi-Source Audio Streaming**: Plays audio from YouTube and any other source supported by yt-dlp
- **Timestamp Support**: Play specific sections of videos using timestamp ranges (e.g., `1:30-2:45`)
- **Voice Channel Management**: Join, leave, and manage voice channel connections
- **Playback Controls**: Play, pause, resume, stop, and volume control
- **Multi-Guild Support**: Handles multiple Discord servers simultaneously
- **Uptime Tracking**: Ping command to check bot uptime
- **Comprehensive Logging**: Detailed logging to both file (`bot.log`) and console

## Prerequisites

- Python 3.7 or higher
- FFmpeg installed on your system
- A Discord bot token (see [Discord Developer Portal](https://discord.com/developers/applications))
- Discord bot with the following permissions:
  - Connect to voice channels
  - Speak in voice channels
  - Send messages
  - Read message history

### Installing FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from [FFmpeg official website](https://ffmpeg.org/download.html) and add to PATH.

## Installation

1. **Clone or download this repository:**
   ```bash
   git clone <repository-url>
   cd TimTheGateGuard
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   ```

3. **Activate the virtual environment:**
   ```bash
   # Linux/macOS
   source venv/bin/activate
   
   # Windows
   venv\Scripts\activate
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **Create your bot configuration file:**
   ```bash
   cp config/template.json config/yourbot.json
   ```

2. **Edit the configuration file** (`config/yourbot.json`):
   ```json
   {
       "project_path": "/absolute/path/to/TimTheGateGuard",
       "TOKEN": "YOUR_DISCORD_BOT_TOKEN_HERE"
   }
   ```

   - `project_path`: 77The absolute path to the project root directory
   - `TOKEN`: Your Discord bot token from the Discord Developer Portal

   **Important:** Never commit your actual configuration file with the token. The `config/` directory is already in `.gitignore` (except `template.json`).

3. **Get your Discord Bot Token:**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application or select an existing one
   - Navigate to the "Bot" section
   - Click "Reset Token" or "Copy" to get your bot token
   - Enable "Message Content Intent" and "Server Members Intent" under "Privileged Gateway Intents" if needed

4. **Invite your bot to your server:**
   - In the Discord Developer Portal, go to "OAuth2" > "URL Generator"
   - Select scopes: `bot` and `applications.commands`
   - Select bot permissions:
     - Connect
     - Speak
     - Send Messages
     - Read Message History
   - Copy the generated URL and open it in your browser to invite the bot

## Usage

### Starting the Bot

**Development mode (using Makefile):**
```bash
make dev
```

**Or manually:**
```bash
./venv/bin/python main.py config/yourbot.json
```

**Production mode (systemd service):**
1. Edit `service/wonderbot.service` and update the paths to match your installation
2. Run the install script:
   ```bash
   ./scripts/install.sh
   ```
3. Start the service:
   ```bash
   sudo systemctl start wonderbot
   ```
4. Enable auto-start on boot:
   ```bash
   sudo systemctl enable wonderbot
   ```

### Commands

All commands use the prefix `-` (hyphen).

#### Voice Channel Commands

- **`-join <channel>`** - Joins the specified voice channel
  - Example: `-join General`
  - The bot must have permission to connect and speak in the channel

- **`-leave`** - Leaves the current voice channel

#### Playback Commands

- **`-play <url> [timestamp]`** or **`-p <url> [timestamp]`** - Plays audio from a URL
  - If you're in a voice channel, the bot will automatically join your channel
  - Supports any URL that yt-dlp can handle (YouTube, SoundCloud, etc.)
  - Timestamp format:
    - No timestamp: Plays from the beginning
    - Single timestamp: `-play <url> 1:30` (starts at 1 minute 30 seconds)
    - Range: `-play <url> 1:30-2:45` (plays from 1:30 to 2:45)
  - Examples:
    - `-play https://www.youtube.com/watch?v=dQw4w9WgXcQ`
    - `-play https://www.youtube.com/watch?v=dQw4w9WgXcQ 1:30`
    - `-play https://www.youtube.com/watch?v=dQw4w9WgXcQ 0:30-1:15`

- **`-pause`** or **`-pa`** or **`-pau`** - Pauses the current playback

- **`-resume`** or **`-r`** or **`-res`** - Resumes paused playback

- **`-stop`** or **`-s`** or **`-sto`** - Stops the current playback

- **`-volume <0-100>`** - Sets the playback volume (0-100)
  - Example: `-volume 50` (sets volume to 50%)

#### Utility Commands

- **`-ping`** - Shows bot uptime (requires "Manage Messages" permission)
  - Displays how long the bot has been running since last restart

- **`-debug`** - Shows current bot status and connection information
  - Useful for troubleshooting connection issues

## Project Structure

```
TimTheGateGuard/
├── main.py                 # Main entry point and bot initialization
├── requirements.txt        # Python dependencies
├── Makefile               # Development shortcuts
├── bot.log                # Application logs (generated at runtime)
│
├── cogs/                  # Discord bot command modules
│   ├── core.py           # Core commands (ping, etc.)
│   └── youtube.py        # Music/audio playback commands
│
├── lib/                   # Library modules
│   └── YTDLSource.py     # YouTube/audio source handler using yt-dlp
│
├── config/                # Configuration files
│   ├── template.json     # Configuration template
│   └── yourbot.json      # Your actual config (not in git)
│
├── scripts/               # Utility scripts
│   ├── install.sh        # Systemd service installation
│   └── startup.sh        # Manual startup script
│
└── service/               # Systemd service files
    └── wonderbot.service  # Systemd service configuration
```

## Troubleshooting

### Bot won't connect to voice channel
- Verify the bot has "Connect" and "Speak" permissions in the channel
- Check that FFmpeg is installed: `ffmpeg -version`
- Ensure the bot is online and not rate-limited

### Audio not playing
- Check bot logs in `bot.log` for error messages
- Verify the URL is valid and accessible
- Ensure the bot is connected to a voice channel
- Try the `-debug` command to check connection status

### "OpusNotLoaded" error
- This usually indicates a missing audio codec library
- On Linux, install: `sudo apt install libopus0`
- On macOS: `brew install opus`

### Connection timeouts
- Check your network connection
- Verify Discord servers are accessible
- Try restarting the bot

### Bot not responding to commands
- Verify the command prefix is `-` (hyphen)
- Check that the bot has "Send Messages" permission
- Ensure the bot is online (check Discord status)

## Logging

The bot logs to both:
- **Console**: Real-time output during development
- **File**: `bot.log` in the project root

Log levels include INFO, WARNING, ERROR, and DEBUG. Check `bot.log` for detailed information about bot operations and errors.

## Dependencies

- **discord.py** (2.4.0) - Discord API wrapper
- **yt-dlp** (2025.1.26) - Audio/video extraction from various sources
- **PyNaCl** (1.5.0) - Voice encryption library
- **aiohttp** (3.11.12) - Async HTTP client

See `requirements.txt` for the complete list of dependencies.

## Future Planned Features

- Soundboard synced to emotes
- Admin controls
- Statistics on usage (top played tracks, top users)

## Credits

The YouTube/audio streaming functionality was initially based on the [discord.py basic voice example](https://github.com/Rapptz/discord.py/blob/master/examples/basic_voice.py).

## License

This is a hobby project maintained for personal use. Use at your own discretion.
