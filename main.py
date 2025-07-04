import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient
from config import API_ID, API_HASH, SESSION_STRING, MONGO_URI, OWNER_ID
import pyrogram.utils

pyrogram.utils.MIN_CHANNEL_ID = -1009147483647
# Initialize MongoDB
mongo = MongoClient(MONGO_URI)
db = mongo.ForwardBot
config = db.config

# Initialize userbot
app = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Helper functions
async def get_config():
    data = config.find_one({"_id": "config"})
    if not data:
        config.insert_one({
            "_id": "config",
            "db_channel": None,
            "receivers": [],
            "paused": False,
            "duration": 1800
        })
        return config.find_one({"_id": "config"})
    return data

async def update_config(update):
    config.update_one({"_id": "config"}, {"$set": update})

# Commands
@app.on_message(filters.command("start") & filters.user(OWNER_ID))
async def start(_, m: Message):
    await m.reply("👋 **Welcome to your Forward Bot Userbot!**\n\nUse /add_db, /add_channel, /duration, /pause, /resume as needed.")

@app.on_message(filters.command("add_db") & filters.user(OWNER_ID))
async def add_db(_, m: Message):
    if len(m.command) < 2:
        return await m.reply("❌ Usage: /add_db CHANNEL_ID")
    await update_config({"db_channel": int(m.command[1])})
    await m.reply(f"✅ Database channel set to `{m.command[1]}`.")

@app.on_message(filters.command("add_channel") & filters.user(OWNER_ID))
async def add_channel(_, m: Message):
    if len(m.command) < 2:
        return await m.reply("❌ Usage: /add_channel CHANNEL_ID")
    data = await get_config()
    receivers = data["receivers"]
    new_channel = int(m.command[1])
    if new_channel not in receivers:
        receivers.append(new_channel)
        await update_config({"receivers": receivers})
        await m.reply(f"✅ Added receiver channel `{new_channel}`.")
    else:
        await m.reply("⚠️ Channel already added.")

@app.on_message(filters.command("remove_channel") & filters.user(OWNER_ID))
async def remove_channel(_, m: Message):
    if len(m.command) < 2:
        return await m.reply("❌ Usage: /remove_channel CHANNEL_ID")
    data = await get_config()
    receivers = data["receivers"]
    rem_channel = int(m.command[1])
    if rem_channel in receivers:
        receivers.remove(rem_channel)
        await update_config({"receivers": receivers})
        await m.reply(f"✅ Removed channel `{rem_channel}`.")
    else:
        await m.reply("⚠️ Channel not found in list.")

@app.on_message(filters.command("pause") & filters.user(OWNER_ID))
async def pause(_, m: Message):
    await update_config({"paused": True})
    await m.reply("⏸️ Forwarding paused.")

@app.on_message(filters.command("resume") & filters.user(OWNER_ID))
async def resume(_, m: Message):
    await update_config({"paused": False})
    await m.reply("▶️ Forwarding resumed.")

@app.on_message(filters.command("info") & filters.user(OWNER_ID))
async def info(_, m: Message):
    data = await get_config()
    text = f"ℹ️ **Bot Info**\n\n"
    text += f"**DB Channel:** {data['db_channel']}\n"
    text += f"**Receivers:** {data['receivers']}\n"
    text += f"**Paused:** {data['paused']}\n"
    text += f"**Duration:** {data['duration']} sec"
    await m.reply(text)

@app.on_message(filters.command("duration") & filters.user(OWNER_ID))
async def duration(_, m: Message):
    if len(m.command) < 2:
        return await m.reply("❌ Usage: /duration SECONDS")
    await update_config({"duration": int(m.command[1])})
    await m.reply(f"✅ Duration updated to {m.command[1]} seconds.")

# Forward loop
async def forward_loop():
    print("🔵 Forward loop started.")

    while True:
        try:
            # Get db channel
            db_data = db.settings.find_one({"_id": "db_channel"})
            if not db_data:
                print("❌ No DB channel set. Sleeping...")
                await asyncio.sleep(30)
                continue
            db_channel = db_data["id"]

            # Get receivers
            receivers_data = db.settings.find_one({"_id": "receivers"})
            receivers = receivers_data["ids"] if receivers_data else []

            if not receivers:
                print("❌ No receiver channels added. Sleeping...")
                await asyncio.sleep(30)
                continue

            # Get duration
            duration_data = db.settings.find_one({"_id": "duration"})
            duration = duration_data["seconds"] if duration_data else 1800  # default 30 min

            # Get last forwarded ID
            forward_state = db.settings.find_one({"_id": "forwarding"})
            last_id = forward_state["last_id"] if forward_state else 0

            # Fetch messages after last forwarded ID
            msgs = app.get_chat_history(db_channel, offset_id=last_id)

            valid_found = False
            async for msg in msgs:
                if not msg or not hasattr(msg, "id"):
                    continue
                if msg.empty or (not msg.text and not msg.media):
                    continue

                valid_found = True

                # Forward to all receivers
                for r in receivers:
                    try:
                        await msg.copy(r)
                        print(f"✅ Forwarded {msg.id} to {r}")
                    except Exception as e:
                        print(f"❌ Failed to forward {msg.id} to {r}: {e}")

                # Update last forwarded ID
                db.settings.update_one(
                    {"_id": "forwarding"},
                    {"$set": {"last_id": msg.id}},
                    upsert=True
                )

                # Sleep between messages
                await asyncio.sleep(duration)

            if not valid_found:
                print("⏳ No new valid messages found. Sleeping...")
                await asyncio.sleep(duration)

        except Exception as e:
            print(f"❌ Error in forward loop: {e}")
            await asyncio.sleep(30)

# Run
if __name__ == "__main__":
    print("🔵 Bot starting...")
    loop = asyncio.get_event_loop()
    loop.create_task(forward_loop())
    app.run()
            
