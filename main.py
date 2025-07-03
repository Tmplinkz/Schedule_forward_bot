import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient
from config import API_ID, API_HASH, SESSION_STRING, MONGO_URI, OWNER_ID

# MongoDB setup
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["schedule_forward_userbot"]
config_col = db["config"]

app = Client("schedule_forward_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)


async def forward_worker():
    while True:
        config = config_col.find_one({"_id": 1})
        if not config:
            await asyncio.sleep(30)
            continue

        db_channel = config.get("db_channel")
        receiver_channels = config.get("receiver_channels", [])
        duration = config.get("duration", 30)

        if not db_channel or not receiver_channels:
            await asyncio.sleep(30)
            continue

        async for msg in app.get_chat_history(db_channel, reverse=True):
            if msg.forward_from_chat or msg.forward_from:
                continue  # skip already forwarded messages

            for rcvr in receiver_channels:
                try:
                    await msg.forward(rcvr)
                    print(f"Forwarded message {msg.id} to {rcvr}")
                except Exception as e:
                    print(f"Failed to forward {msg.id} to {rcvr}: {e}")

            await asyncio.sleep(duration * 60)  # duration in minutes


@app.on_message(filters.command("start") & filters.user(OWNER_ID))
async def start_cmd(client, message: Message):
    await message.reply("👋 Welcome! I am your scheduled forwarder userbot.")


@app.on_message(filters.command("add_db") & filters.user(OWNER_ID))
async def add_db(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("❌ Usage: /add_db [channel_id]")
    db_channel = int(message.command[1])
    config_col.update_one({"_id": 1}, {"$set": {"db_channel": db_channel}}, upsert=True)
    await message.reply(f"✅ Database channel set to `{db_channel}`.")


@app.on_message(filters.command("add_channel") & filters.user(OWNER_ID))
async def add_channel(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("❌ Usage: /add_channel [channel_id]")
    receiver = int(message.command[1])
    config = config_col.find_one({"_id": 1}) or {}
    receivers = config.get("receiver_channels", [])
    if receiver not in receivers:
        receivers.append(receiver)
        config_col.update_one({"_id": 1}, {"$set": {"receiver_channels": receivers}}, upsert=True)
    await message.reply(f"✅ Added receiver channel `{receiver}`.")


@app.on_message(filters.command("duration") & filters.user(OWNER_ID))
async def set_duration(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("❌ Usage: /duration [minutes]")
    duration = int(message.command[1])
    config_col.update_one({"_id": 1}, {"$set": {"duration": duration}}, upsert=True)
    await message.reply(f"✅ Duration set to {duration} minutes.")


@app.on_message(filters.command("show_config") & filters.user(OWNER_ID))
async def show_config(client, message: Message):
    config = config_col.find_one({"_id": 1}) or {}
    await message.reply(f"📊 Current Config:\n\n{config}")


async def main():
    await app.start()
    print("Bot started...")
    await forward_worker()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
            
