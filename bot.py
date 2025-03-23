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
        "removecaptions": True, # preserves the original caption if false, otherwise removes it
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
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_queue(queue):
    try:
        with open(QUEUE_PATH, "w") as f:
            json.dump(queue, f)
    except Exception as e:
        logging.error(f"Failed to save queue: {e}")

config = load_config()
message_queue = load_queue()
bot = telebot.TeleBot(config["bot_token"])

forced_message = None
last_ping_id = None

def copy_messages():
    global message_queue, forced_message, last_ping_id
    while True:
        try:
            if not message_queue:
                time.sleep(25)
                continue
            if forced_message:
                message_id = forced_message
                forced_message = None
            else:
                if config["shuffle"]:
                    message_id = random.choice(message_queue)
                else:
                    message_id = message_queue[0]
                    save_queue(message_queue)
            if config["debug_mode"]:
                logging.info(f"Copying message ID {message_id} from admin {config['admin_id']} to {config['channel_id']}")
            if config["removecaptions"]:
                bot.copy_message(config["channel_id"], config["admin_id"], message_id, caption="")
            else:
                bot.copy_message(config["channel_id"], config["admin_id"], message_id)
            if last_ping_id:
                bot.edit_message_reply_markup(config["admin_id"], last_ping_id, reply_markup=None)
                last_ping_id = None
            message_queue.remove(message_id)
            save_queue(message_queue)
            bot.set_message_reaction(config["admin_id"], message_id, [telebot.types.ReactionTypeEmoji(emoji="⚡")])
            time.sleep(config["forward_interval"])
        except requests.exceptions.ReadTimeout:
            logging.warning("Read timeout, retrying...")
            time.sleep(5)
        except Exception as e:
            logging.error(f"Error in copy_messages: {e}")
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
    telebot.types.BotCommand("start", "Starts the bot"),
    telebot.types.BotCommand("ping", "Checks if the bot is running and shows queue status"),
    telebot.types.BotCommand("kys", "Stops the bot"),
    telebot.types.BotCommand("dryrun", "Forwards the message back to you without posting it to test correct formatting"),
    telebot.types.BotCommand("postnow", "Instantly posts a replied message"),
    telebot.types.BotCommand("remove", "Removes a replied message from the queue"),
    telebot.types.BotCommand("isinqueue", "Returns true if the message is in queue, otherwise returns false")
]
bot.set_my_commands(commands)

@bot.message_handler(commands=["start", "ping", "kys", "remove", "dryrun", "postnow", "isinqueue"])
def handle_commands(message: Message):
    global message_queue, forced_message, last_ping_id
    if not is_admin(message):
        return
    if config["debug_mode"]:
        logging.info(f"Received command: {message.text} from {message.chat.id}")
    if message.text == "/ping":
        if last_ping_id:
            bot.edit_message_reply_markup(config["admin_id"], last_ping_id, reply_markup=None)
            last_ping_id = None
        queue_count = len(message_queue)
        if message_queue:
            if config["shuffle"] and forced_message:
                message_id = forced_message
            elif config["shuffle"] and message_queue:
                forced_message = random.choice(message_queue)
                logging.info(f"Selected message ID {forced_message} for forced posting.")
                message_id = forced_message
            else:
                message_id = message_queue[0]
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("Post now", callback_data="postnow"))
            keyboard.add(InlineKeyboardButton("Delete this post", callback_data="delete"))
            ping_message = bot.send_message(chat_id=config["admin_id"],text=f"↑↑↑ Next message ↑↑↑\nbeep boop, still alive. Got {queue_count} posts in the queue.",reply_to_message_id=message_id, reply_markup=keyboard)
            last_ping_id = ping_message.message_id
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
        else:
            bot.send_message(message.chat.id, "false")

    elif message.text == "/dryrun":
        if not message.reply_to_message:
            bot.send_message(message.chat.id, "you gotta reply to a message to dry run it!(｡•́︿•̀｡)")
            return
        logging.info(f"Dry running message ID {message.reply_to_message.message_id}.")
        if config["removecaptions"]:
            bot.copy_message(config["admin_id"], config["admin_id"], message.reply_to_message.message_id, caption="")
        else:
            bot.copy_message(config["admin_id"], config["admin_id"], message.reply_to_message.message_id)
        if message.reply_to_message.message_id not in message_queue:
            bot.send_message(message.chat.id, "just fyi, that message isnt in the queue")

    elif message.text == "/postnow":
        if not message.reply_to_message:
            bot.send_message(message.chat.id, "𓀐𓂸. you gotta reply to a message to post it now!")
            return
        logging.info(f"Force posting message ID {message.reply_to_message.message_id} to the channel.")
        if message.reply_to_message.message_id in message_queue:
            if config["removecaptions"]:
                bot.copy_message(config["channel_id"], config["admin_id"], message.reply_to_message.message_id, caption="")
            else:
                bot.copy_message(config["channel_id"], config["admin_id"], message.reply_to_message.message_id)
            if last_ping_id:
                bot.edit_message_reply_markup(config["admin_id"], last_ping_id, reply_markup=None)
                last_ping_id = None
            message_queue.remove(message.reply_to_message.message_id)
            bot.send_message(message.chat.id, "posted")
            save_queue(message_queue)
            bot.set_message_reaction(config["admin_id"], message.reply_to_message.message_id, [telebot.types.ReactionTypeEmoji(emoji="⚡")])
        else:
            bot.send_message(message.chat.id, "uh oh, that message isnt in the queue!")
        
    elif message.text == "/remove":
        if not message.reply_to_message:
            bot.send_message(message.chat.id, "you gotta reply to a message to remove it")
            return
        if forced_message == message.reply_to_message.message_id:
            forced_message = None
        if message.reply_to_message.message_id in message_queue:
            logging.info(f"Deleting message ID {message.reply_to_message.message_id} from the queue.")
            message_queue.remove(message.reply_to_message.message_id)
            save_queue(message_queue)
            bot.send_message(message.chat.id, "( -_•)▄︻テحكـ━一💥 KABLAM! this message was taken out back and shot.")
            if last_ping_id:
                bot.edit_message_reply_markup(config["admin_id"], last_ping_id, reply_markup=None)
                last_ping_id = None
            bot.set_message_reaction(config["admin_id"], message.reply_to_message.message_id, [telebot.types.ReactionTypeEmoji(emoji="💔")])
        else:
            bot.send_message(message.chat.id, "uh oh, that message isnt in the queue!")

@bot.callback_query_handler(func=lambda call: call.data == "postnow")
def handle_callback(call: CallbackQuery):
    global message_queue, forced_message, last_ping_id
    bot.answer_callback_query(call.id,"")
    if last_ping_id:
                bot.edit_message_reply_markup(config["admin_id"], last_ping_id, reply_markup=None)
                last_ping_id = None
    if config["shuffle"]:
        if config["removecaptions"]:
            bot.copy_message(config["channel_id"], config["admin_id"], forced_message, caption="")
        else:
            bot.copy_message(config["channel_id"], config["admin_id"], forced_message)
        bot.set_message_reaction(config["admin_id"], forced_message, [telebot.types.ReactionTypeEmoji(emoji="⚡")])
        logging.info(f"Force posting message ID {forced_message} to the channel.")
        message_queue.remove(forced_message)
        save_queue(message_queue)
        forced_message = None
        bot.send_message(call.message.chat.id, "Posted")
    elif message_queue:
        if config["removecaptions"]:
            bot.copy_message(config["channel_id"], config["admin_id"], message_queue[0], caption="")
        else:
            bot.copy_message(config["channel_id"], config["admin_id"], message_queue[0])
        bot.set_message_reaction(config["admin_id"], message_queue[0], [telebot.types.ReactionTypeEmoji(emoji="⚡")])
        logging.info(f"Force posting message ID {message_queue[0]} to the channel.")
        del message_queue[0]
        save_queue(message_queue)
        bot.send_message(call.message.chat.id, "Posted")
    else:
        logging.error("Unexpected error in callback_query_handler postnow")
        bot.send_message(call.message.chat.id, "Unexpected error.")

@bot.callback_query_handler(func=lambda call: call.data == "delete")
def handle_callback(call: CallbackQuery):
    global message_queue, forced_message, last_ping_id
    bot.answer_callback_query(call.id,"")
    if last_ping_id:
                bot.edit_message_reply_markup(config["admin_id"], last_ping_id, reply_markup=None)
                last_ping_id = None
    if config["shuffle"] and forced_message:
        message_queue.remove(forced_message)
        save_queue(message_queue)
        logging.info(f"Deleting message ID {forced_message} from the queue.")
        bot.set_message_reaction(config["admin_id"], forced_message, [telebot.types.ReactionTypeEmoji(emoji="💔")])
        forced_message = None
        bot.send_message(call.message.chat.id, "Removed")
    elif message_queue:
        logging.info(f"Deleting message ID {message_queue[0]} from the queue.")
        bot.send_message(call.message.chat.id, "Removed")
        bot.set_message_reaction(config["admin_id"], message_queue[0], [telebot.types.ReactionTypeEmoji(emoji="💔")])
        del message_queue[0]
        save_queue(message_queue)
    else:
        logging.error("Unexpected error in callback_query_handler delete")
        bot.send_message(call.message.chat.id, "Unexpected error.")

@bot.message_handler(func=lambda message: True, content_types=["text", "photo", "video", "document", "animation"])
def handle_new_message(message: Message):
    if not is_admin(message):
        return
    if config["debug_mode"]:
        logging.info(f"Received message from {message.chat.id}: {message.content_type}. Added to the queue as ID {message.message_id}")
    message_queue.append(message.message_id)
    save_queue(message_queue)
    bot.set_message_reaction(message.chat.id, message.message_id, [telebot.types.ReactionTypeEmoji(emoji="👍")])

def is_connected():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False

if __name__ == "__main__":
    start_forwarding()
    while True:
        if is_connected():
            try:
                bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
            except requests.exceptions.ReadTimeout:
                logging.warning("Read timeout occurred, retrying polling...")
                if config["debug_mode"]:
                    bot.send_message(config["admin_id"], "Read timeout occurred, retrying polling...")
                time.sleep(5)
            except Exception as e:
                logging.error(f"Unexpected error: {e}, restarting polling...")
                if config["debug_mode"]:
                    bot.send_message(config["admin_id"], f"Unexpected error: {e}, restarting polling...")
                time.sleep(5)
        else:
            logging.error("No internet connection. Retrying in 10 seconds...")
            time.sleep(10)
