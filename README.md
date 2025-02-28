## Description

This Telegram bot built with pyTelegramBotAPI allows you to send posts to your TG channel on an interval, remove captions and send posts in random order.

## Requirements

- Python 3 or later
- `pyTelegramBotAPI`
- `requests`

## Installation

1. Clone or download the repository.
2. Install dependencies:
   ```sh
   pip install pyTelegramBotAPI requests
   ```
3. Create a `config.json` file in the same directory as `bot.py` with the following structure:
   ```json
   {
       "bot_token": your_bot_token,
       "admin_id": 123456789,
       "channel_id": -123456789,
       "forward_interval": 60,
       "debug_mode": false,
       "shuffle": false,
       "removecaptions": false
   }
   ```
   - Replace `your_bot_token` with your Telegram bot token.
   - Replace `admin_id` with your Telegram user ID.
   - Replace `channel_id` with your target channel ID.

## Usage

Run the bot using:

```sh
python bot.py
```

### Commands

- `/start` - Starts the bot
- `/ping` - Checks if the bot is running and shows queue status
- `/kys` - Stops the bot
- `/dryrun` - Forwards the message back to you without posting it to test correct formatting
- `/postnow` - Instantly posts a replied message
- `/remove` - Removes a replied message from the queue

#### Huge shout out to [@sethfoxen](https://github.com/sethfoxen) for the original code base and for finally making me stop using that annoying closed source bot with egotistical owners

#### Disclaimer: Some code for this bot was Ai-generated before i stopped being a lazy dumbass and started learning python like a big boy
