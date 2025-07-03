import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
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
    await message.reply("👋 **User Forward Bot Active**\nUse /add_db /add_channel /duration /panel to configure.")

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

# Duration command
@app.on_message(filters.command("duration") & filters.user(OWNER_ID))
async def duration_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: `/duration <minutes>`", quote=True)
        return
    duration = int(message.command[1])
    update_data("duration", duration)
    await message.reply(f"✅ Duration set to {duration} minutes.")

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

# Status command
@app.on_message(filters.command("status") & filters.user(OWNER_ID))
async def status_cmd(client, message: Message):
    data = get_data()
    paused = data.get('paused', False)
    await message.reply(f"⏸️ Paused: {paused}")

# Inline Admin Panel command
@app.on_message(filters.command("panel") & filters.user(OWNER_ID))
async def admin_panel(client, message: Message):
    data = get_data()
    paused = data.get('paused', False)
    duration = data['duration']
    receivers = data['receiver_channels']
    db_channel = data['db_channel']

    text = (
        f"🔧 **Admin Control Panel**\n\n"
        f"**DB Channel:** {db_channel}\n"
        f"**Receivers:** {receivers}\n"
        f"**Duration:** {duration} mins\n"
        f"**Paused:** {paused}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏸️ Pause", callback_data="pause"),
         InlineKeyboardButton("▶️ Resume", callback_data="resume")],
        [InlineKeyboardButton("🗑️ Remove All Receivers", callback_data="remove_all")],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ])

    await message.reply(text, reply_markup=keyboard)

# Callback query handler
@app.on_callback_query()
async def callbacks(client, callback_query: CallbackQuery):
    data = callback_query.data

    if data == "pause":
        update_data("paused", True)
        await callback_query.edit_message_text("⏸️ Forwarding has been paused.")
    elif data == "resume":
        update_data("paused", False)
        await callback_query.edit_message_text("▶️ Forwarding has been resumed.")
    elif data == "remove_all":
        update_data("receiver_channels", [])
        await callback_query.edit_message_text("🗑️ All receiver channels removed.")
    elif data == "close":
        await callback_query.message.delete()
    else:
        await callback_query.answer("Unknown action.")

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

            msg_list.reverse()  # oldest to newest

            forwarded_count = 0
            for msg in msg_list:
                for r in receivers:
                    try:
                        await msg.copy(r)  # ✅ copy instead of forward to remove forward tag
                        forwarded_count += 1
                        print(f"✅ Copied message {msg.id} to {r}")
                    except FloodWait as fw:
                        print(f"⏳ FloodWait: Sleeping for {fw.value} seconds.")
                        await asyncio.sleep(fw.value)
                    except Exception as e:
                        print(f"❌ Failed to copy: {e}")
                update_data("last_forwarded_id", msg.id)
                await asyncio.sleep(duration * 60)

            if forwarded_count == 0:
                print("ℹ️ No new messages found.")

            await asyncio.sleep(30)

        except FloodWait as fw:
            print(f"⏳ FloodWait (global): Sleeping for {fw.value} seconds.")
            await asyncio.sleep(fw.value)
        except Exception as e:
            print(f"❌ Error in forward loop: {e}")
            await asyncio.sleep(60)

# Run
if __name__ == "__main__":
    print("🔵 Bot starting...")
    loop = asyncio.get_event_loop()
    loop.create_task(forward_loop())
    app.run()
