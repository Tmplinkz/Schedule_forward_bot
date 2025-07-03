import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import API_ID, API_HASH, BOT_TOKEN, MONGO_URI, OWNER_ID, SESSION_STRING

# MongoDB setup
mongo = MongoClient(MONGO_URI)
db = mongo["forwarder_db"]
config_col = db["config"]

# Pyrogram user client using string session
user = Client(SESSION_STRING, api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Telegram Bot app
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

# Helper functions
async def get_config(key, default=None):
    doc = config_col.find_one({"_id": key})
    if doc:
        return doc["value"]
    return default

async def set_config(key, value):
    config_col.update_one({"_id": key}, {"$set": {"value": value}}, upsert=True)

# Bot commands with OWNER check
async def add_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorised to use this bot.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Usage: /add_db CHANNEL_ID")
        return
    channel_id = int(context.args[0])
    await set_config("db_channel", channel_id)
    await update.message.reply_text(f"DB channel set to {channel_id}")

async def add_receiver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorised to use this bot.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Usage: /channel CHANNEL_ID")
        return
    channel_id = int(context.args[0])
    receivers = await get_config("receivers", [])
    if receivers is None:
        receivers = []
    if channel_id not in receivers:
        receivers.append(channel_id)
        await set_config("receivers", receivers)
        await update.message.reply_text(f"Added receiver: {channel_id}")
    else:
        await update.message.reply_text("Already exists.")

async def set_duration_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorised to use this bot.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Usage: /duration MINUTES")
        return
    minutes = int(context.args[0])
    await set_config("duration", minutes)
    await update.message.reply_text(f"Duration set to {minutes} minutes.")

# /info command
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorised to use this bot.")
        return

    db_channel = await get_config("db_channel")
    receivers = await get_config("receivers", [])
    duration = await get_config("duration", 30)
    await update.message.reply_text(
        f"✅ Current Settings:\n\n"
        f"DB Channel: {db_channel}\n"
        f"Receivers: {receivers}\n"
        f"Duration: {duration} minutes"
    )

# Add handlers
bot_app.add_handler(CommandHandler("add_db", add_db))
bot_app.add_handler(CommandHandler("channel", add_receiver))
bot_app.add_handler(CommandHandler("duration", set_duration_cmd))
bot_app.add_handler(CommandHandler("info", info))

# User client forwarding logic
@user.on_message(filters.channel)
async def forward_files(client, message: Message):
    db_channel = await get_config("db_channel")
    receivers = await get_config("receivers", [])
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

# Main runner
async def main():
    await user.start()
    bot_task = asyncio.create_task(bot_app.run_polling())
    await user.idle()
    await bot_task

if __name__ == "__main__":
    asyncio.run(main())
                       
