import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient
from config import API_ID, API_HASH, MONGO_URI, OWNER_ID, SESSION_STRING
import pyrogram.utils

pyrogram.utils.MIN_CHANNEL_ID = -1009147483647

# MongoDB setup
mongo = MongoClient(MONGO_URI)
db = mongo['ForwardBot']
col = db['Data']

# Pyrogram client
app = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Helper functions
def get_data():
    data = col.find_one({"_id": "config"})
    if data is None:
        col.insert_one({
            "_id": "config",
            "db_channel": None,
            "receiver_channels": [],
            "duration": 30,
            "last_forwarded_id": 0,
            "paused": False
        })
        data = col.find_one({"_id": "config"})
    return data

def update_data(key, value):
    col.update_one({"_id": "config"}, {"$set": {key: value}})

# Commands

@app.on_message(filters.command("start") & filters.user(OWNER_ID))
async def start_cmd(client, message: Message):
    await message.reply(
        "**✅ User Forward Bot Active**\n\n"
        "Use /panel to see controls."
    )

@app.on_message(filters.command("panel") & filters.user(OWNER_ID))
async def panel_cmd(client, message: Message):
    data = get_data()
    paused = data.get("paused", False)
    db_channel = data.get("db_channel")
    receivers = data.get("receiver_channels")
    duration = data.get("duration")
    await message.reply(
        f"**🔧 Control Panel**\n\n"
        f"DB Channel: `{db_channel}`\n"
        f"Receivers: `{receivers}`\n"
        f"Duration: `{duration}` minutes\n"
        f"Paused: `{paused}`\n\n"
        "🔹 Commands:\n"
        "/add_db <id>\n"
        "/add_channel <id>\n"
        "/remove_channel <id>\n"
        "/duration <minutes>\n"
        "/pause\n"
        "/resume\n"
        "/status"
    )

@app.on_message(filters.command("pause") & filters.user(OWNER_ID))
async def pause_cmd(client, message: Message):
    update_data("paused", True)
    await message.reply("⏸️ Forwarding paused.")

@app.on_message(filters.command("resume") & filters.user(OWNER_ID))
async def resume_cmd(client, message: Message):
    update_data("paused", False)
    await message.reply("▶️ Forwarding resumed.")

@app.on_message(filters.command("status") & filters.user(OWNER_ID))
async def status_cmd(client, message: Message):
    data = get_data()
    paused = data.get("paused", False)
    db_channel = data.get("db_channel")
    receivers = data.get("receiver_channels")
    duration = data.get("duration")
    await message.reply(
        f"**ℹ️ Status**\n"
        f"DB Channel: `{db_channel}`\n"
        f"Receivers: `{receivers}`\n"
        f"Duration: `{duration}` minutes\n"
        f"Paused: `{paused}`"
    )

@app.on_message(filters.command("add_db") & filters.user(OWNER_ID))
async def add_db_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: /add_db <channel_id>")
        return
    db_channel = int(message.command[1])
    update_data("db_channel", db_channel)
    await message.reply(f"✅ DB Channel set to `{db_channel}`.")

@app.on_message(filters.command("add_channel") & filters.user(OWNER_ID))
async def add_channel_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: /add_channel <channel_id>")
        return
    receiver = int(message.command[1])
    data = get_data()
    receivers = data['receiver_channels']
    if receiver not in receivers:
        receivers.append(receiver)
        update_data("receiver_channels", receivers)
        await message.reply(f"✅ Added receiver channel `{receiver}`.")
    else:
        await message.reply(f"⚠️ Receiver channel `{receiver}` already exists.")

@app.on_message(filters.command("remove_channel") & filters.user(OWNER_ID))
async def remove_channel_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: /remove_channel <channel_id>")
        return
    receiver = int(message.command[1])
    data = get_data()
    receivers = data['receiver_channels']
    if receiver in receivers:
        receivers.remove(receiver)
        update_data("receiver_channels", receivers)
        await message.reply(f"✅ Removed receiver channel `{receiver}`.")
    else:
        await message.reply(f"⚠️ Receiver channel `{receiver}` not found.")

@app.on_message(filters.command("duration") & filters.user(OWNER_ID))
async def duration_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: /duration <minutes>")
        return
    duration = int(message.command[1])
    update_data("duration", duration)
    await message.reply(f"✅ Duration set to {duration} minutes.")

# Forward loop

async def forward_loop():
    print("🔵 Forward loop started.")
    while True:
        data = get_data()
        if data.get("paused"):
            print("⏸️ Forwarding is paused.")
            await asyncio.sleep(30)
            continue

        db_channel = data['db_channel']
        receivers = data['receiver_channels']
        duration = data['duration']
        last_id = data['last_forwarded_id']

        if db_channel is None or not receivers:
            print("⚠️ DB channel or receivers not configured.")
            await asyncio.sleep(60)
            continue

        msgs = app.get_chat_history(db_channel, offset_id=last_id)
        msg_list = []
        async for msg in msgs:
            msg_list.append(msg)

        msg_list.reverse()

        for msg in msg_list:
            if not hasattr(msg, "id"):
                print("⚠️ msg has no id attribute, skipping...")
                continue
            for r in receivers:
                try:
                    await msg.copy(r)
                    print(f"✅ Copied message {msg.id} to {r}")
                except Exception as e:
                    print(f"❌ Failed to copy: {e}")
            update_data("last_forwarded_id", msg.id)
            await asyncio.sleep(duration * 60)

# Run

if __name__ == "__main__":
    print("🔵 Bot starting...")
    loop = asyncio.get_event_loop()
    loop.create_task(forward_loop())
    app.run()
    
