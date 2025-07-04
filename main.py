import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient
import os
import pyrogram.utils

pyrogram.utils.MIN_CHANNEL_ID = -1009147483647

# Configurations
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
MONGO_URI = os.getenv("MONGO_URI")
OWNER_ID = int(os.getenv("OWNER_ID"))

# Initialize userbot client
app = Client(name="userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Initialize MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["forward_bot"]
config_col = db["config"]

# Helper functions
async def get_config():
    cfg = config_col.find_one({"_id": 1})
    if not cfg:
        config_col.insert_one({"_id": 1, "db_channel": None, "receivers": [], "paused": False, "duration": 1800})
        cfg = config_col.find_one({"_id": 1})
    return cfg

async def update_config(updates: dict):
    config_col.update_one({"_id": 1}, {"$set": updates})

# /start
@app.on_message(filters.command("start") & filters.user(OWNER_ID))
async def start_cmd(client, message: Message):
    await message.reply("✅ Userbot is running and ready to forward your files.\nUse /info to check current setup.")

# /add_db
@app.on_message(filters.command("add_db") & filters.user(OWNER_ID))
async def add_db_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply("❌ Usage: /add_db [channel_id]")
        return
    db_channel = int(message.command[1])
    await update_config({"db_channel": db_channel})
    await message.reply(f"✅ DB channel set to `{db_channel}`.")

# /add_channel
@app.on_message(filters.command("add_channel") & filters.user(OWNER_ID))
async def add_channel_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply("❌ Usage: /add_channel [channel_id]")
        return
    cfg = await get_config()
    receivers = cfg["receivers"]
    channel_id = int(message.command[1])
    if channel_id not in receivers:
        receivers.append(channel_id)
        await update_config({"receivers": receivers})
        await message.reply(f"✅ Added receiver channel `{channel_id}`.")
    else:
        await message.reply("⚠️ Channel already in receivers list.")

# /remove_channel
@app.on_message(filters.command("remove_channel") & filters.user(OWNER_ID))
async def remove_channel_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply("❌ Usage: /remove_channel [channel_id]")
        return
    cfg = await get_config()
    receivers = cfg["receivers"]
    channel_id = int(message.command[1])
    if channel_id in receivers:
        receivers.remove(channel_id)
        await update_config({"receivers": receivers})
        await message.reply(f"✅ Removed receiver channel `{channel_id}`.")
    else:
        await message.reply("⚠️ Channel ID not found in receivers.")

# /pause
@app.on_message(filters.command("pause") & filters.user(OWNER_ID))
async def pause_cmd(client, message: Message):
    await update_config({"paused": True})
    await message.reply("⏸️ Forwarding paused.")

# /resume
@app.on_message(filters.command("resume") & filters.user(OWNER_ID))
async def resume_cmd(client, message: Message):
    await update_config({"paused": False})
    await message.reply("▶️ Forwarding resumed.")

# /duration
@app.on_message(filters.command("duration") & filters.user(OWNER_ID))
async def duration_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply("❌ Usage: /duration [seconds]")
        return
    duration = int(message.command[1])
    await update_config({"duration": duration})
    await message.reply(f"⏱️ Duration updated to {duration} seconds.")

# /info
@app.on_message(filters.command("info") & filters.user(OWNER_ID))
async def info_cmd(client, message: Message):
    cfg = await get_config()
    text = f"📊 **Bot Status**\n\nDB Channel: `{cfg['db_channel']}`\nReceivers: `{cfg['receivers']}`\nPaused: `{cfg['paused']}`\nDuration: `{cfg['duration']} seconds`"
    await message.reply(text)

# Forward loop
async def forward_loop():
    await app.start()
    while True:
        cfg = await get_config()
        if cfg["paused"]:
            print("⏸️ Forwarding is paused.")
            await asyncio.sleep(10)
            continue

        db_channel = cfg["db_channel"]
        receivers = cfg["receivers"]
        duration = cfg["duration"]

        if not db_channel or not receivers:
            print("⚠️ DB channel or receivers not set.")
            await asyncio.sleep(30)
            continue

        try:
            async for msg in app.get_chat_history(db_channel, limit=1, reverse=True):
                if not msg or (not msg.text and not msg.media):
                    print("⚠️ Skipping empty/service message.")
                    continue
                for r in receivers:
                    try:
                        await msg.copy(r)
                        print(f"✅ Forwarded {msg.id} to {r}")
                    except Exception as e:
                        print(f"❌ Failed to forward {msg.id} to {r}: {e}")
                await asyncio.sleep(duration)
        except Exception as e:
            print(f"❌ Error in forward loop: {e}")
            await asyncio.sleep(30)

# Run
if __name__ == "__main__":
    print("🔵 Userbot starting...")
    loop = asyncio.get_event_loop()
    loop.create_task(forward_loop())
    app.run()
                
