# Telegram Channel Search Bot

A personal Telegram bot for searching and discovering channels, built with Python using Aiogram and Telethon libraries.

## Features

- **Channel Search**: Search for Telegram channels using `/search` command
- **Webhook Management**: Commands to manage webhook status (`/webhook_status`, `/webhook_off`)
- **Admin Controls**: Restrict certain commands to authorized users
- **FastAPI Integration**: HTTP endpoint for health checks and search API
- **Deployable**: Ready for deployment on Render or Railway

## Prerequisites

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Telegram API credentials (from [my.telegram.org](https://my.telegram.org))

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/hamad44321-eng/telegram-bot.git
   cd telegram-bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   ```bash
   cp env.example .env
   # Edit .env with your credentials
   ```

## Configuration

Set the following environment variables in your `.env` file:

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Your bot token from BotFather |
| `API_ID` | Telegram API ID from my.telegram.org |
| `API_HASH` | Telegram API Hash from my.telegram.org |
| `ADMIN_IDS` | Comma-separated list of admin user IDs |
| `SEARCH_LIMIT` | Maximum number of search results (default: 20) |
| `PORT` | HTTP server port (default: 10000) |

## Usage

### Running the Bot

```bash
# Run bot only (polling mode)
python bot.py

# Run with HTTP keepalive server (for deployments)
python keepalive.py
```

### Bot Commands

- `/start` - Start the bot and see available commands
- `/ping` - Check if the bot is running
- `/search <query>` - Search for Telegram channels
- `/webhook_status` - Check current webhook status
- `/webhook_off` - Disable webhook (admin only)

## Deployment

### Render

The project includes a `render.yaml` configuration for one-click deployment to Render.

### Railway

See [README_RAILWAY.md](README_RAILWAY.md) for Railway deployment instructions.

## Project Structure

```
├── bot.py           # Main bot with aiogram
├── keepalive.py     # FastAPI keepalive server
├── .app.py          # Alternative FastAPI app
├── requirements.txt # Python dependencies
├── render.yaml      # Render deployment config
├── Procfile         # Heroku/Railway process file
└── env.example      # Environment variable template
```

## License

This project is for personal use.
