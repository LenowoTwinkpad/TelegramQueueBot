import os
import json
import logging
import telebot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import threading
import time
import requests
import random
import socket

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
QUEUE_PATH = os.path.join(BASE_DIR, "message_queue.json")

def load_config():
    default_config = {
        "bot_token": "your_bot_token",  # Create your bot using BotFather
        "admin_id": 123456789,  # Telegram user ID of the admin
        "channel_id": -123456789,  # Channel or group ID
        "forward_interval": 60,  # Interval in seconds
        "debug_mode": False,  # Debug mode
        "shuffle": False,  # Enable/disable random message order
        "removecaptions": True, # Preserves the original caption if false, otherwise removes it
    }
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        with open(CONFIG_PATH, "w") as f:
            json.dump(default_config, f, indent=4)
        logging.info("Example config.json file created. Please update it with your credentials.")
        exit(1)

def load_queue():
    try:
        with open(QUEUE_PATH, "r") as f:
            return json.load(f)

    except FileNotFoundError:
        logging.info(f"Queue file not found at {QUEUE_PATH}. Creating an empty one.")
        with open(QUEUE_PATH, "w") as f:
            json.dump([], f)
        return []

    except Exception as e:
        logging.error(f"Failed to load queue.json: {type(e).__name__}")
        logging.error("Shutting down")
        os._exit(1)

def save_queue(queue):
    try:
        with open(QUEUE_PATH, "w") as f:
            json.dump(queue, f)
    except Exception as e:
        logging.error(f"Failed to save queue: {type(e).__name__}")

config = load_config()
message_queue = load_queue()
bot = telebot.TeleBot(config["bot_token"])

def copy_messages():
    global message_queue
    while True:
        try:
            if not message_queue:
                time.sleep(25)
                continue

            if config["shuffle"]:
                message_id = message_queue.pop(random.randrange(len(message_queue)))
            else:
                message_id = message_queue.pop(0)

            save_queue(message_queue)

            if config["debug_mode"]:
                logging.info(f"Copying message ID {message_id} from admin {config['admin_id']} to {config['channel_id']}")

            if config["removecaptions"]:
                bot.copy_message(config["channel_id"], config["admin_id"], message_id, caption="")
            else:
                bot.copy_message(config["channel_id"], config["admin_id"], message_id)

            bot.set_message_reaction(config["admin_id"], message_id, [telebot.types.ReactionTypeEmoji(emoji="⚡")])
            time.sleep(config["forward_interval"])

        except Exception as e:
            logging.error(f"An error occurred: {type(e).__name__}")
            time.sleep(5)


def start_forwarding():
    thread = threading.Thread(target=copy_messages, daemon=True)
    thread.start()

def is_admin(message: Message):
    if message.chat.id != config["admin_id"]:
        logging.warning(f"Unauthorized access attempt from {message.chat.id}")
        return False
    return True

commands = [
    telebot.types.BotCommand("ping", "Checks if the bot is running and shows queue status"),
    telebot.types.BotCommand("kys", "Stops the bot"),
    telebot.types.BotCommand("postnow", "Instantly posts a replied message"),
    telebot.types.BotCommand("remove", "Removes a replied message from the queue"),
    telebot.types.BotCommand("isinqueue", "Returns true if the message is in queue, otherwise returns false")
]
bot.set_my_commands(commands)

@bot.message_handler(commands=["ping", "kys", "remove", "postnow", "isinqueue"])
def handle_commands(message: Message):
    global message_queue
    if not is_admin(message):
        return
    if config["debug_mode"]:
        logging.info(f"Received command: {message.text} from {message.chat.id}")

    if message.text == "/ping":
        queue_count = len(message_queue)
        if message_queue:
            if not config["shuffle"]:
                message_id_to_show = message_queue[0]
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton("Post now", callback_data=f"postnow:{message_id_to_show}"))
                keyboard.add(InlineKeyboardButton("Delete this post", callback_data=f"delete:{message_id_to_show}"))
                bot.send_message(
                chat_id=config["admin_id"],
                text=f"↑↑↑ Next message (ID: {message_id_to_show}) ↑↑↑\nbeep boop, still alive. Got {queue_count} posts in the queue.",
                reply_to_message_id=message_id_to_show,
                reply_markup=keyboard
                )
            else:
                bot.send_message(
                chat_id=config["admin_id"],
                text=f"beep boop, still alive. Got {queue_count} posts in the queue. next post not shown since shuffle=true in config.",
                )

        else:
            bot.send_message(message.chat.id, "beep boop, still alive but out of memes (╥‸╥)")

    elif message.text == "/kys":
        bot.send_message(message.chat.id, "okie dokie killing myself ✘_✘")
        bot.stop_polling()
        os._exit(1)

    elif message.text == "/isinqueue":
        if not message.reply_to_message:
            bot.send_message(message.chat.id, "reply to a message to check if its in the queue")
            return
        if message.reply_to_message.message_id in message_queue:
            bot.send_message(message.chat.id, "true")
            bot.set_message_reaction(config["admin_id"], message.reply_to_message.message_id, [telebot.types.ReactionTypeEmoji(emoji="👍")])
        else:
            bot.send_message(message.chat.id, "false")
            bot.set_message_reaction(config["admin_id"], message.reply_to_message.message_id, [telebot.types.ReactionTypeEmoji(emoji="💔")])

    elif message.text == "/postnow":
        if not message.reply_to_message:
            bot.send_message(message.chat.id, "𓀐𓂸. you gotta reply to a message to post it now!")
            return

        message_id_to_post = message.reply_to_message.message_id

        if message_id_to_post in message_queue:
            logging.info(f"Force posting message ID {message_id_to_post} to the channel.")
            try:
                if config["removecaptions"]:
                    bot.copy_message(config["channel_id"], config["admin_id"], message_id_to_post, caption="")
                else:
                    bot.copy_message(config["channel_id"], config["admin_id"], message_id_to_post)

                message_queue.remove(message_id_to_post)
                save_queue(message_queue)
                bot.send_message(message.chat.id, "posted")
                bot.set_message_reaction(config["admin_id"], message_id_to_post, [telebot.types.ReactionTypeEmoji(emoji="⚡")])
            except Exception as e:
                logging.error(f"Error while force posting message {message_id_to_post}: {type(e).__name__}")
                bot.send_message(message.chat.id, "Failed to post the message.")
        else:
            bot.set_message_reaction(config["admin_id"], message_id_to_post, [telebot.types.ReactionTypeEmoji(emoji="💔")])
            bot.send_message(message.chat.id, "uh oh, that message isnt in the queue!")

    elif message.text == "/remove":
        if not message.reply_to_message:
            bot.send_message(message.chat.id, "you gotta reply to a message to remove it")
            return

        message_id_to_remove = message.reply_to_message.message_id

        if message_id_to_remove in message_queue:
            logging.info(f"Deleting message ID {message_id_to_remove} from the queue.")
            message_queue.remove(message_id_to_remove)
            save_queue(message_queue)
            bot.send_message(message.chat.id, "( -_•)▄︻テحكـ━一💥 KABLAM! this message was taken out back and shot.")
            bot.set_message_reaction(config["admin_id"], message_id_to_remove, [telebot.types.ReactionTypeEmoji(emoji="💔")])
        else:
            bot.set_message_reaction(config["admin_id"], message_id_to_remove, [telebot.types.ReactionTypeEmoji(emoji="💔")])
            bot.send_message(message.chat.id, "uh oh, that message isnt in the queue!")

#by god's grace hope this works 🙏🏻🙏🏻🙏🏻🙏🏻
@bot.callback_query_handler(func=lambda call: call.data.startswith(("postnow:", "delete:")))
def handle_callback(call: CallbackQuery):
    global message_queue

    bot.answer_callback_query(call.id, "")

    try:
        action, message_id_str = call.data.split(":")
        message_id = int(message_id_str)
    except Exception as e:
        logging.error(f"Error in callback handling: {type(e).__name__}")
        bot.send_message(call.message.chat.id, "Error in callback handling. ")
        return
    
    try:
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    except Exception as e:
        logging.warning(f"Failed to remove inline keyboard from ping message: {type(e).__name__}")

    if message_id not in message_queue:
        logging.error(f"Callback postnow received but message ID {message_id} is no longer in the queue.")
        bot.send_message(call.message.chat.id, f"Message ID {message_id} is no longer in the queue.")
        return

    if action == "postnow":
        logging.info(f"Callback: Force posting message ID {message_id} to the channel.")
        try:
            if config["removecaptions"]:
                bot.copy_message(config["channel_id"], config["admin_id"], message_id, caption="")
            else:
                bot.copy_message(config["channel_id"], config["admin_id"], message_id)

            message_queue.remove(message_id)
            save_queue(message_queue)
            bot.send_message(call.message.chat.id, "Posted")
            bot.set_message_reaction(config["admin_id"], message_id, [telebot.types.ReactionTypeEmoji(emoji="⚡")])
        except Exception as e:
            logging.error(f"Error force posting message {message_id} via callback: {type(e).__name__}")
            bot.send_message(call.message.chat.id, "Failed to post the message.")

    elif action == "delete":
        logging.info(f"Callback: Deleting message ID {message_id} from the queue.")
        try:
            message_queue.remove(message_id)
            save_queue(message_queue)
            bot.send_message(call.message.chat.id, "Removed")
            bot.set_message_reaction(config["admin_id"], message_id, [telebot.types.ReactionTypeEmoji(emoji="💔")])
        except Exception as e:
            logging.error(f"Error deleting message {message_id} via callback: {type(e).__name__}")
            bot.send_message(call.message.chat.id, "Failed to remove the message from the queue.")


@bot.message_handler(func=lambda message: is_admin(message) and (message.text is None or not message.text.startswith('/')) and message.reply_to_message is None, content_types=["text", "photo", "video", "document", "animation"])
#↑↑↑LONG!↑↑↑
def handle_new_message(message: Message):
    if config["debug_mode"]:
        logging.info(f"Received message from {message.chat.id}: {message.content_type}. Added to the queue as ID {message.message_id}")
    message_queue.append(message.message_id)
    save_queue(message_queue)
    bot.set_message_reaction(message.chat.id, message.message_id, [telebot.types.ReactionTypeEmoji(emoji="👍")])

start_forwarding()
timeout_backoff = 5
while True:
    try:
        bot.polling(none_stop=True, timeout=30, long_polling_timeout=30)
        timeout_backoff = 5
    except (requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectionError,
            socket.timeout) as e:
        logging.warning(f"Network error ({type(e).__name__}), retrying in {timeout_backoff}s...")
        time.sleep(timeout_backoff)
        if timeout_backoff <= 120:
            timeout_backoff = timeout_backoff + 5
    except Exception as e:
        logging.error(f"Unexpected error: {type(e).__name__}")
        time.sleep(timeout_backoff)
