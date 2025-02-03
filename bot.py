import telebot
import asyncio
import flask
from flask import Flask, request
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaDocument
import io
import os

# ✅ Environment Variables (Set these in Render)
BOT_TOKEN = os.getenv("8028216173:AAGpnMeiQaYTfbnp11gNG9NUcQXQcA-vsNk")
API_ID = int(os.getenv("API_ID", "28215280"))  # Replace with your API ID
API_HASH = os.getenv("API_HASH", "0ca7536ff612170e7662cee27597c104")  # Replace with your API Hash
CHANNEL_USERNAME = os.getenv("meraterab")  # Your public channel username (without @)
SESSION_STRING = os.getenv("SESSION_STRING", "")  # Leave empty or add a StringSession
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1002413516054"))  # Your log channel ID
PORT = int(os.getenv("PORT", 5000))  # Render auto-assigns a port

# ✅ Webhook URL for Render
WEBHOOK_URL = f"https://{os.getenv('RENDER_STATIC_URL')}/webhook"  # Render auto-generates this

# ✅ Initialize Telethon client with StringSession
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ✅ Flask App
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

async def start_telethon():
    """ Start Telethon client before webhook setup """
    await client.start()
    print("✅ Telethon client started!")

async def fetch_movie_message(movie_name):
    """ Fetch the movie message asynchronously from the public channel """
    async for message in client.iter_messages(CHANNEL_USERNAME, limit=100):
        if message.message and movie_name.lower() in message.message.lower():
            return message
    return None

async def download_media(message):
    """ Download media from the public channel without saving to disk """
    if message.media:
        file = await client.download_media(message, file=io.BytesIO())  # Download file in memory
        file.seek(0)  # Reset file pointer to the beginning
        mime_type = message.media.document.mime_type if isinstance(message.media, MessageMediaDocument) else None
        return file, mime_type
    return None, None

def send_log(log_message):
    """ Send logs to the log channel """
    try:
        bot.send_message(LOG_CHANNEL_ID, f"📜 **Log:**\n{log_message}", parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Error sending log: {e}")

@app.route("/", methods=["GET"])
def home():
    return "✅ Telegram Bot is Running on Render!"

@app.route("/webhook", methods=["POST"])
def webhook():
    """ Webhook to handle Telegram updates """
    if request.method == "POST":
        json_str = request.get_data().decode("UTF-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "OK", 200

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "Send me a movie name, and I'll find it for you!")

@bot.message_handler(func=lambda message: True)
def search_movie(message):
    """ Handle user requests synchronously by running async functions safely """
    movie_name = message.text.lower()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    future = asyncio.run_coroutine_threadsafe(fetch_movie_message(movie_name), loop)
    result = future.result()

    if result:
        if result.media:
            future_media = asyncio.run_coroutine_threadsafe(download_media(result), loop)
            media_file, mime_type = future_media.result()

            if mime_type == "video/mp4":
                bot.send_video(message.chat.id, media_file, caption=result.message)
                send_log(f"🎥 Movie Sent: {movie_name}\n👤 User: [{message.chat.first_name}](tg://user?id={message.chat.id})")
            else:
                bot.send_document(message.chat.id, media_file, caption=result.message)
                send_log(f"📄 Document Sent: {movie_name}\n👤 User: [{message.chat.first_name}](tg://user?id={message.chat.id})")
        else:
            bot.send_message(message.chat.id, result.message)
            send_log(f"📝 Text Sent: {result.message}\n👤 User: [{message.chat.first_name}](tg://user?id={message.chat.id})")
    else:
        bot.send_message(message.chat.id, "Movie not found!")
        send_log(f"❌ Movie Not Found: {movie_name}\n👤 User: [{message.chat.first_name}](tg://user?id={message.chat.id})")

async def main():
    """ Start Telethon and set up Webhook """
    await start_telethon()

    # ✅ Remove previous webhook (if any)
    bot.remove_webhook()

    # ✅ Set new webhook
    bot.set_webhook(url=WEBHOOK_URL)
    print(f"✅ Webhook set: {WEBHOOK_URL}")

    # ✅ Run Flask app
    app.run(host="0.0.0.0", port=PORT)

# ✅ Run the bot
if __name__ == "__main__":
    asyncio.run(main())