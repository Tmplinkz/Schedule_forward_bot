import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from pymongo import MongoClient
from config import API_ID, API_HASH, MONGO_URI, OWNER_ID, SESSION_STRING
import pyrogram.utils

pyrogram.utils.MIN_CHANNEL_ID = -1009147483647

# MongoDB setup
mongo = MongoClient(MONGO_URI)
db = mongo['ForwardBot']
col = db['Data']

# Pyrogram client
app = Client("bot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Helper: get & set database values
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

# Start command
@app.on_message(filters.command("start") & filters.user(OWNER_ID))
async def start_cmd(client, message: Message):
    await message.reply("👋 **User Forward Bot Active**\nUse /add_db /add_channel /duration /pause /resume /remove_channel /status to configure.")

# Other commands remain same as previous version

# Pause command
@app.on_message(filters.command("pause") & filters.user(OWNER_ID))
async def pause_cmd(client, message: Message):
    update_data("paused", True)
    await message.reply("⏸️ Forwarding paused.")

# Resume command
@app.on_message(filters.command("resume") & filters.user(OWNER_ID))
async def resume_cmd(client, message: Message):
    update_data("paused", False)
    await message.reply("▶️ Forwarding resumed.")

# Remove receiver channel command
@app.on_message(filters.command("remove_channel") & filters.user(OWNER_ID))
async def remove_channel_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: `/remove_channel <channel_id>`", quote=True)
        return
    receiver = int(message.command[1])
    data = get_data()
    receivers = data['receiver_channels']
    if receiver in receivers:
        receivers.remove(receiver)
        update_data("receiver_channels", receivers)
        await message.reply(f"✅ Removed receiver channel `{receiver}`")
    else:
        await message.reply(f"⚠️ Receiver channel `{receiver}` not found.")

# Status command
@app.on_message(filters.command("status") & filters.user(OWNER_ID))
async def status_cmd(client, message: Message):
    data = get_data()
    paused = data.get('paused', False)
    await message.reply(f"⏸️ Paused: {paused}")

# Main forwarding loop
async def forward_loop():
    print("🔵 Forward loop started.")
    while True:
        try:
            data = get_data()
            db_channel = data['db_channel']
            duration = data['duration']
            receivers = data['receiver_channels']
            last_id = data['last_forwarded_id']
            paused = data.get('paused', False)

            if paused:
                print("⏸️ Forwarding is paused. Waiting...")
                await asyncio.sleep(30)
                continue

            if db_channel is None or not receivers:
                print("⚠️ DB channel or receiver channels not configured yet. Waiting...")
                await asyncio.sleep(60)
                continue

            msg_list = []
            async for msg in app.get_chat_history(db_channel):
                if msg.id > last_id:
                    msg_list.append(msg)

            msg_list.reverse()

            for msg in msg_list:
                for r in receivers:
                    try:
                        await msg.copy(r)
                        print(f"✅ Copied message {msg.id} to {r}")
                    except FloodWait as fw:
                        print(f"⏳ FloodWait: Sleeping for {fw.value} seconds.")
                        await asyncio.sleep(fw.value)
                    except Exception as e:
                        print(f"❌ Failed to copy: {e}")
                update_data("last_forwarded_id", msg.id)
                await asyncio.sleep(duration * 60)

            await asyncio.sleep(30)

        except FloodWait as fw:
            print(f"⏳ FloodWait (global): Sleeping for {fw.value} seconds.")
            await asyncio.sleep(fw.value)
        except Exception as e:
            print(f"❌ Error in forward loop: {e}")
            await asyncio.sleep(60)

# Run
@app.on_startup()
async def startup(client):
    asyncio.create_task(forward_loop())

if __name__ == "__main__":
    print("🔵 Bot starting...")
    app.run()
                
