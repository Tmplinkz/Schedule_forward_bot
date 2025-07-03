import asyncio
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pymongo import MongoClient
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from config import API_ID, API_HASH, BOT_TOKEN, MONGO_URI, OWNER_ID, SESSION_STRING

# MongoDB setup
mongo = MongoClient(MONGO_URI)
db = mongo["forwarder_db"]
config_col = db["config"]

# Database helper functions
async def get_config(key, default=None):
    doc = config_col.find_one({"_id": key})
    return doc["value"] if doc else default

async def set_config(key, value):
    config_col.update_one({"_id": key}, {"$set": {"value": value}}, upsert=True)

# Pyrogram user client
user = Client(
    name="user_session",
    session_string=SESSION_STRING,
    api_id=API_ID,
    api_hash=API_HASH
)

# Telegram Bot client
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

# Owner‑only command handlers
async def add_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("You are not authorised to use this bot.")
    if not context.args:
        return await update.message.reply_text("Usage: /add_db CHANNEL_ID")
    channel_id = int(context.args[0])
    await set_config("db_channel", channel_id)
    await update.message.reply_text(f"DB channel set to {channel_id}")

async def add_receiver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("You are not authorised to use this bot.")
    if not context.args:
        return await update.message.reply_text("Usage: /channel CHANNEL_ID")
    channel_id = int(context.args[0])
    receivers = await get_config("receivers", []) or []
    if channel_id not in receivers:
        receivers.append(channel_id)
        await set_config("receivers", receivers)
        await update.message.reply_text(f"Added receiver: {channel_id}")
    else:
        await update.message.reply_text("Already exists.")

async def set_duration_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("You are not authorised to use this bot.")
    if not context.args:
        return await update.message.reply_text("Usage: /duration MINUTES")
    minutes = int(context.args[0])
    await set_config("duration", minutes)
    await update.message.reply_text(f"Duration set to {minutes} minutes.")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("You are not authorised to use this bot.")
    db_channel = await get_config("db_channel")
    receivers = await get_config("receivers", []) or []
    duration = await get_config("duration", 30)
    await update.message.reply_text(
        f"✅ Current Settings:\n\n"
        f"DB Channel: {db_channel}\n"
        f"Receivers: {receivers}\n"
        f"Duration: {duration} minutes"
    )

# Register handlers with bot_app
bot_app.add_handler(CommandHandler("add_db", add_db))
bot_app.add_handler(CommandHandler("channel", add_receiver))
bot_app.add_handler(CommandHandler("duration", set_duration_cmd))
bot_app.add_handler(CommandHandler("info", info))

# Pyrogram channel‑forward handler
@user.on_message(filters.channel)
async def forward_files(client: Client, message: Message):
    db_channel = await get_config("db_channel")
    receivers = await get_config("receivers", []) or []
    duration = await get_config("duration", 30)
    if message.chat.id != db_channel:
        return
    for rcv in receivers:
        try:
            await message.forward(rcv)
            print(f"Forwarded {message.message_id} to {rcv}")
        except Exception as e:
            print(f"Failed to forward to {rcv}: {e}")
        await asyncio.sleep(duration * 60)

async def main():
    # Start both clients
    await user.start()
    await bot_app.initialize()
    bot_app.start()

    # Launch polling loop
    bot_task = asyncio.create_task(bot_app.run_polling())

    # Keep the program running
    await idle()

    # Graceful shutdown
    bot_task.cancel()
    await asyncio.gather(bot_task, return_exceptions=True)
    await bot_app.stop()
    await user.stop()

if __name__ == "__main__":
    asyncio.run(main())
    
