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
def get_data():
    data = col.find_one({"_id": "config"})
    if data is None:
        col.insert_one({
            "_id": "config",
            "db_channel": None,
            "receiver_channels": [],
            "duration": 30,
            "last_forwarded_id": 0
        })
        data = col.find_one({"_id": "config"})
    return data

def update_data(key, value):
    col.update_one({"_id": "config"}, {"$set": {key: value}})

# Start command
@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    user_id = message.from_user.id if message.from_user else message.sender_chat.id
    print(f"🔵 Received /start command from {user_id}")
    await message.reply("👋 **User Forward Bot Active**")

# Add db channel command
@app.on_message(filters.command("add_db") & filters.user(OWNER_ID))
async def add_db_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: `/add_db <channel_id>`", quote=True)
        return
    db_channel = int(message.command[1])
    update_data("db_channel", db_channel)
    await message.reply(f"✅ DB Channel set to `{db_channel}`")

# Add receiver channel command
@app.on_message(filters.command("add_channel") & filters.user(OWNER_ID))
async def add_channel_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: `/add_channel <channel_id>`", quote=True)
        return
    receiver = int(message.command[1])
    data = get_data()
    receivers = data['receiver_channels']
    if receiver not in receivers:
        receivers.append(receiver)
        update_data("receiver_channels", receivers)
        await message.reply(f"✅ Added receiver channel `{receiver}`")
    else:
        await message.reply(f"⚠️ Receiver channel `{receiver}` already exists.")

# Duration command
@app.on_message(filters.command("duration") & filters.user(OWNER_ID))
async def duration_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: `/duration <minutes>`", quote=True)
        return
    duration = int(message.command[1])
    update_data("duration", duration)
    await message.reply(f"✅ Duration set to {duration} minutes.")

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

            if db_channel is None or not receivers:
                print("⚠️ DB channel or receiver channels not configured yet. Waiting...")
                await asyncio.sleep(60)
                continue

            msgs = app.get_chat_history(db_channel, offset_id=last_id)
            msg_list = []
            async for msg in msgs:
                msg_list.append(msg)

            msg_list.reverse()  # ✅ oldest to newest

            for msg in msg_list:
                print(f"🔍 DEBUG: Processing msg {msg}")
                if hasattr(msg, "message_id"):
                    for r in receivers:
                        try:
                            await app.forward_messages(r, db_channel, msg.message_id)
                            print(f"✅ Forwarded message {msg.message_id} to {r}")
                        except Exception as e:
                            print(f"❌ Failed to forward: {e}")
                    update_data("last_forwarded_id", msg.message_id)
                    await asyncio.sleep(duration * 60)
                else:
                    print("⚠️ msg has no message_id attribute, skipping...")

        except Exception as e:
            print(f"❌ Error in forward loop: {e}")
            await asyncio.sleep(60)

# Run
if __name__ == "__main__":
    print("🔵 Bot starting...")
    loop = asyncio.get_event_loop()
    loop.create_task(forward_loop())
    app.run()
            
