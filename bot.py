import os
import json
import logging
import telebot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import threading
import time
import requests
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define relative paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
QUEUE_PATH = os.path.join(BASE_DIR, "message_queue.json")

# Load configuration from config.json
def load_config():
    default_config = {
        "bot_token": "your_bot_token",  # Create your bot using BotFather
        "admin_id": 123456789,  # Telegram user ID of the admin
        "channel_id": -123456789,  # Channel or group ID
        "forward_interval": 60,  # Interval in seconds
        "debug_mode": False,  # Debug mode
        "shuffle": False  # Enable/disable random message order
    }
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        with open(CONFIG_PATH, "w") as f:
            json.dump(default_config, f, indent=4)
        logging.info("Example config.json file created. Please update it with your credentials.")
        exit(1)

# Load message queue from file
def load_queue():
    try:
        with open(QUEUE_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Save message queue to file
def save_queue(queue):
    try:
        with open(QUEUE_PATH, "w") as f:
            json.dump(queue, f)
    except Exception as e:
        logging.error(f"Failed to save queue: {e}")

# Initialize Telegram bot
config = load_config()
message_queue = load_queue()
bot = telebot.TeleBot(config["bot_token"])

forced_message = None  # Stores a message that must be sent next

def copy_messages():
    global message_queue, forced_message
    while True:
        if not message_queue:
            time.sleep(25)
            continue
        if forced_message:
            message_id = forced_message
            forced_message = None  # Reset after sending
        else:
            message_id = random.choice(message_queue) if config["shuffle"] else message_queue.pop(0)
        try:
            if config["debug_mode"]:
                logging.info(f"Copying message ID {message_id} from admin {config['admin_id']} to {config['channel_id']}")
            bot.copy_message(config["channel_id"], config["admin_id"], message_id)
            message_queue.remove(message_id)
            save_queue(message_queue)
        except Exception as e:
            logging.error(f"Failed to copy message ID {message_id}: {e}")
            message_queue.insert(0, message_id)
        time.sleep(config["forward_interval"])

def start_forwarding():
    thread = threading.Thread(target=copy_messages, daemon=True)
    thread.start()

def is_admin(message: Message):
    if message.chat.id != config["admin_id"]:
        logging.warning(f"Unauthorized access attempt from {message.chat.id}")
        return False
    return True

@bot.message_handler(commands=["start", "ping", "kys", "remove", "dryrun", "postnow", "removeforced"])
def handle_commands(message: Message):
    if not is_admin(message):
        return
    if config["debug_mode"]:
        logging.info(f"Received command: {message.text} from {message.chat.id}")
    
    if message.text == "/ping":
        global forced_message
        queue_count = len(message_queue)
        if config["shuffle"] and forced_message:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("Post now", callback_data="postnow"))
            keyboard.add(InlineKeyboardButton("Delete this post", callback_data="delete"))
            bot.send_message(message.chat.id, f"beep boop, still alive. got {queue_count} posts in the queue. this is the next post, it was already selected as a forced message.", reply_markup=keyboard)
            bot.copy_message(config["admin_id"], config["admin_id"], forced_message)
        elif config["shuffle"] and message_queue:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("Post now", callback_data="postnow"))
            keyboard.add(InlineKeyboardButton("Delete this post", callback_data="delete"))
            forced_message = random.choice(message_queue)
            logging.info(f"Selected message ID {forced_message} for forced posting.")
            bot.send_message(message.chat.id, f"beep boop, still alive. got {queue_count} posts in the queue. this is now selected for forced posting:", reply_markup=keyboard)
            bot.copy_message(config["admin_id"], config["admin_id"], forced_message)
        elif message_queue:
            bot.send_message(message.chat.id, f"beep boop, still alive. got {queue_count} posts in the queue. this is the next post:")
            bot.copy_message(config["admin_id"], config["admin_id"], message_queue[0])
        elif not message_queue:
            bot.send_message(message.chat.id, "beep boop, still alive but out of them memes (╥‸╥)")
        else:
            bot.send_message(message.chat.id, "shits fucked :(")
            logging.info(f"Error in the /ping handler")


    elif message.text == "/removeforced":
        if not forced_message:
            bot.send_message(message.chat.id, "there are no forced messages")
            return
        else:
            message_queue.remove(forced_message)
            bot.send_message(message.chat.id, "( -_•)▄︻テحكـ━一💥 KABLAM! this message was taken out back and shot.")
            logging.info(f"Removed forced message ID {forced_message}.")
            forced_message = None

    elif message.text == "/kys":
        bot.send_message(message.chat.id, "okie dokie killing myself ✘_✘")
        bot.stop_polling()
        os._exit(1)
      
    elif message.text == "/dryrun":
        if not message.reply_to_message:
            bot.send_message(message.chat.id, "you gotta reply to a message to dry run it!(｡•́︿•̀｡)")
            return
        logging.info(f"Dry run initiated for message ID {message.reply_to_message.message_id}.")
        bot.copy_message(config["admin_id"], config["admin_id"], message.reply_to_message.message_id)

    elif message.text == "/postnow":
        if not message.reply_to_message:
            bot.send_message(message.chat.id, "𓀐𓂸. you gotta reply to a message to post it now!")
            return
        logging.info(f"Force posting message ID {message.reply_to_message.message_id} to the channel.")
        bot.copy_message(config["channel_id"], config["admin_id"], message.reply_to_message.message_id)
        message_queue.remove(message.reply_to_message.message_id)

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
        else:
            bot.send_message(message.chat.id, "uh oh, that message isnt in the queue!")

"""@bot.callback_query_handler(func=lambda call: call.data == "postnow")
def handle_callback(call: CallbackQuery):
    if forced_message:


@bot.callback_query_handler(func=lambda call: call.data == "delete")
def handle_callback(call: CallbackQuery):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "Test successful!"). """

@bot.message_handler(func=lambda message: True, content_types=["text", "photo", "video", "document", "animation"])
def handle_new_message(message: Message):
    if not is_admin(message):
        return
    if config["debug_mode"]:
        logging.info(f"Received message from {message.chat.id}: {message.content_type}. Added to the queue as ID {message.message_id}")
    message_queue.append(message.message_id)
    save_queue(message_queue)

if __name__ == "__main__":
    start_forwarding()
    while True:
        try:
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except requests.exceptions.ReadTimeout:
            logging.warning("Read timeout occurred, retrying polling...")
            time.sleep(5)
        except Exception as e:
            logging.error(f"Unexpected error: {e}, restarting polling...")
            time.sleep(5)
