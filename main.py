import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient
from config import API_ID, API_HASH, BOT_TOKEN, MONGO_URI, OWNER_ID, SESSION_STRING

# MongoDB setup
mongo = MongoClient(MONGO_URI)
db = mongo["forwarder_db"]
config_col = db["config"]

def get_config(key, default=None):
    doc = config_col.find_one({"_id": key})
    return doc["value"] if doc else default

def set_config(key, value):
    config_col.update_one({"_id": key}, {"$set": {"value": value}}, upsert=True)

# Initialize Pyrogram client (bot)
app = Client("bot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Owner-only filter
def is_owner(_, message: Message):
    return message.from_user and message.from_user.id == OWNER_ID

@app.on_message(filters.command("add_db") & filters.private & filters.create(is_owner))
async def add_db(c: Client, m: Message):
    if not m.command or len(m.command) < 2:
        return await m.reply_text("Usage: /add_db CHANNEL_ID")
    set_config("db_channel", int(m.command[1]))
    await m.reply_text(f"DB channel set to {m.command[1]}")

@app.on_message(filters.command("channel") & filters.private & filters.create(is_owner))
async def add_receiver(c: Client, m: Message):
    if not m.command or len(m.command) < 2:
        return await m.reply_text("Usage: /channel CHANNEL_ID")
    recv = int(m.command[1])
    receivers = get_config("receivers", []) or []
    if recv not in receivers:
        receivers.append(recv)
        set_config("receivers", receivers)
        await m.reply_text(f"Added receiver: {recv}")
    else:
        await m.reply_text("Already exists.")

@app.on_message(filters.command("duration") & filters.private & filters.create(is_owner))
async def set_duration_cmd(c: Client, m: Message):
    if not m.command or len(m.command) < 2:
        return await m.reply_text("Usage: /duration MINUTES")
    minutes = int(m.command[1])
    set_config("duration", minutes)
    await m.reply_text(f"Duration set to {minutes} minutes.")

@app.on_message(filters.command("info") & filters.private & filters.create(is_owner))
async def info(c: Client, m: Message):
    db_channel = get_config("db_channel")
    receivers = get_config("receivers", []) or []
    duration = get_config("duration", 30)
    await m.reply_text(
        f"✅ Current Settings:\n"
        f"DB Channel: {db_channel}\n"
        f"Receivers: {receivers}\n"
        f"Duration: {duration} minutes"
    )

# Forwarding logic
@app.on_message(filters.channel)
async def forward_files(c: Client, m: Message):
    db_channel = get_config("db_channel")
    receivers = get_config("receivers", []) or []
    duration = get_config("duration", 30)
    if m.chat.id != db_channel:
        return
    for rcv in receivers:
        try:
            await m.forward(rcv)
        except Exception as e:
            print(f"Failed to forward to {rcv}: {e}")
        await asyncio.sleep(duration * 60)

if __name__ == "__main__":
    app.run()
        
