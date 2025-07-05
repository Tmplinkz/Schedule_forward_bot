import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient
from pyrogram.errors import FloodWait
from config import API_ID, API_HASH, SESSION_STRING, MONGO_URI, OWNER_ID, DEFAULT_DURATION
import pyrogram.utils

pyrogram.utils.MIN_CHANNEL_ID = -1009147483647
# Initialize MongoDB
mongo = MongoClient(MONGO_URI)
db = mongo["ForwardBot1"]
config_col = db["config"]

# Initialize userbot
app = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Globals
pause_flag = False

# Helper functions
async def get_config():
    data = config_col.find_one({"_id": "config"})
    if not data:
        data = {"_id": "config", "db_channel": None, "receivers": [], "duration": DEFAULT_DURATION}
        config_col.insert_one(data)
    return data

async def update_config(key, value):
    config_col.update_one({"_id": "config"}, {"$set": {key: value}})

# Commands

@app.on_message(filters.command("start") & filters.user(OWNER_ID))
async def start_handler(client, message: Message):
    await message.reply("👋 **Welcome to the Forward Bot Userbot!**\nUse /add_db, /add_channel, /duration, /pause, /resume, /info as needed.")

@app.on_message(filters.command("add_db") & filters.user(OWNER_ID))
async def add_db_handler(client, message: Message):
    if len(message.command) < 2:
        await message.reply("⚠️ Provide DB channel ID.\nExample: /add_db -1001234567890")
        return
    db_channel = int(message.command[1])
    await update_config("db_channel", db_channel)
    await message.reply(f"✅ DB channel set to `{db_channel}`.")

@app.on_message(filters.command("add_channel") & filters.user(OWNER_ID))
async def add_channel_handler(client, message: Message):
    if len(message.command) < 2:
        await message.reply("⚠️ Provide receiver channel ID.\nExample: /add_channel -1009876543210")
        return
    channel_id = int(message.command[1])
    config = await get_config()
    receivers = config.get("receivers", [])
    if channel_id not in receivers:
        receivers.append(channel_id)
        await update_config("receivers", receivers)
        await message.reply(f"✅ Added receiver channel `{channel_id}`.")
    else:
        await message.reply("⚠️ This channel is already in the list.")

@app.on_message(filters.command("remove_channel") & filters.user(OWNER_ID))
async def remove_channel_handler(client, message: Message):
    if len(message.command) < 2:
        await message.reply("⚠️ Provide receiver channel ID to remove.\nExample: /remove_channel -1009876543210")
        return
    channel_id = int(message.command[1])
    config = await get_config()
    receivers = config.get("receivers", [])
    if channel_id in receivers:
        receivers.remove(channel_id)
        await update_config("receivers", receivers)
        await message.reply(f"✅ Removed channel `{channel_id}`.")
    else:
        await message.reply("⚠️ This channel was not in the list.")

@app.on_message(filters.command("pause") & filters.user(OWNER_ID))
async def pause_handler(client, message: Message):
    global pause_flag
    pause_flag = True
    await message.reply("⏸️ Forwarding paused.")

@app.on_message(filters.command("resume") & filters.user(OWNER_ID))
async def resume_handler(client, message: Message):
    global pause_flag
    pause_flag = False
    await message.reply("▶️ Forwarding resumed.")

@app.on_message(filters.command("duration") & filters.user(OWNER_ID))
async def duration_handler(client, message: Message):
    if len(message.command) < 2:
        await message.reply("⚠️ Provide duration in seconds.\nExample: /duration 1800")
        return
    duration = int(message.command[1])
    await update_config("duration", duration)
    await message.reply(f"✅ Duration set to {duration} seconds.")

@app.on_message(filters.command("info") & filters.user(OWNER_ID))
async def info_handler(client, message: Message):
    config = await get_config()
    txt = f"ℹ️ **Bot Status**:\n\n"
    txt += f"**DB Channel**: `{config.get('db_channel')}`\n"
    txt += f"**Receivers**: `{config.get('receivers')}`\n"
    txt += f"**Duration**: `{config.get('duration')}` seconds\n"
    txt += f"**Paused**: `{pause_flag}`"
    await message.reply(txt)

# Forwarding loop

async def forward_loop():
    print("🔵 Forward loop started.")

    last_processed_id = None

    while True:
        if pause_flag:
            await asyncio.sleep(5)
            continue

        config = await get_config()
        db_channel = config.get("db_channel")
        receivers = config.get("receivers")
        duration = config.get("duration", DEFAULT_DURATION)

        if not db_channel or not receivers:
            print("⚠️ DB channel or receivers not set. Sleeping.")
            await asyncio.sleep(10)
            continue

        try:
            async for msg in app.get_chat_history(db_channel, limit=5):
                if last_processed_id is None:
                    last_processed_id = msg.id
                    continue

                if msg.id <= last_processed_id:
                    continue

                if not msg or msg.empty or msg.pinned_message or (not msg.text and not msg.media):
                    print("⚠️ Skipping invalid/empty/pinned message.")
                    continue

                for r in receivers:
                    try:
                        await msg.copy(r)
                        print(f"✅ Forwarded message {msg.id} to {r}")
                    except Exception as e:
                        print(f"❌ Failed to forward {msg.id} to {r}: {e}")

                last_processed_id = msg.id
                await asyncio.sleep(duration)

        except Exception as e:
            print(f"❌ Error in forward loop: {e}")
            await asyncio.sleep(duration)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(forward_loop())
    app.run()
    
