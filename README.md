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
       "bot_token": "123456789",
       "admin_id": 123456789,
       "channel_id": -123456789,
       "forward_interval": 60,
       "debug_mode": false,
       "shuffle": false,
       "remove_captions": false
   }
   ```

## Usage

Run the bot using:

```sh
python bot.py
```

### Commands

- `/start` - Starts the bot
- `/ping` - Checks if the bot is running and shows queue status
- `/kys` - Stops the bot
- `/postnow` - Instantly posts a replied message
- `/remove` - Removes a replied message from the queue
- `/isinqueue` - Returns true if the message is in queue, otherwise returns false"

### Bot doesnt support grouped attachments/albums yet, they will be added to the queue as separate messages. will be fixed one day.
