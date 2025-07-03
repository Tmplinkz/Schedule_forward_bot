import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient
from config import API_ID, API_HASH, MONGO_URI, OWNER_ID, SESSION_STRING

# MongoDB setup
mongo = MongoClient(MONGO_URI)
db = mongo['ForwardBot']
col = db['Data']

# Pyrogram client
app = Client("bot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Helper: get & set database values
async def get_data():
    data = await col.find_one({"_id": "config"})
    if data is None:
        await col.insert_one({"_id": "config", "db_channel": None, "receiver_channels": [], "duration": 30})
        data = await col.find_one({"_id": "config"})
    return data

async def update_data(key, value):
    await col.update_one({"_id": "config"}, {"$set": {key: value}})

# Start command
@app.on_message(filters.command("start") & filters.user(OWNER_ID))
async def start_cmd(client, message: Message):
    await message.reply("👋 **User Forward Bot Active**\n\nUse /add_db /add_channel /duration to configure.")

# Add db channel command
@app.on_message(filters.command("add_db") & filters.user(OWNER_ID))
async def add_db_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: `/add_db <channel_id>`", quote=True)
        return
    db_channel = int(message.command[1])
    await update_data("db_channel", db_channel)
    await message.reply(f"✅ DB Channel set to `{db_channel}`")

# Add receiver channel command
@app.on_message(filters.command("add_channel") & filters.user(OWNER_ID))
async def add_channel_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: `/add_channel <channel_id>`", quote=True)
        return
    receiver = int(message.command[1])
    data = await get_data()
    receivers = data['receiver_channels']
    receivers.append(receiver)
    await update_data("receiver_channels", receivers)
    await message.reply(f"✅ Added receiver channel `{receiver}`")

# Duration command
@app.on_message(filters.command("duration") & filters.user(OWNER_ID))
async def duration_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: `/duration <minutes>`", quote=True)
        return
    duration = int(message.command[1])
    await update_data("duration", duration)
    await message.reply(f"✅ Duration set to {duration} minutes.")

# Main forwarding loop
async def forward_loop():
    data = await get_data()
    db_channel = data['db_channel']
    duration = data['duration']
    receivers = data['receiver_channels']

    if db_channel is None or not receivers:
        print("DB channel or receiver channels not configured yet.")
        return

    async for msg in app.get_chat_history(db_channel, reverse=True):
        for r in receivers:
            try:
                await msg.copy(r)
                print(f"Forwarded message {msg.message_id} to {r}")
            except Exception as e:
                print(f"Failed to forward: {e}")
        await asyncio.sleep(duration * 60)

# Run
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(forward_loop())
    app.run()
    
