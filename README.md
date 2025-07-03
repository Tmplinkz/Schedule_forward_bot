# Telegram Forward Userbot

## ✅ Features
- /add_db CHANNEL_ID – Set DB channel
- /channel CHANNEL_ID – Add receiver channel/group
- /duration MINUTES – Set time gap
- /info – View current settings
- Uses **Pyrogram user account** with **string session**
- Owner-only restricted commands

## 🚀 Deploy on Koyeb

1. Fork or clone this repo to GitHub.
2. Generate your **Pyrogram string session**:

```python
from pyrogram import Client

api_id = int(input("API ID: "))
api_hash = input("API HASH: ")

with Client("sessiongen", api_id=api_id, api_hash=api_hash) as app:
    print(app.export_session_string())
```

3. Go to [Koyeb dashboard](https://app.koyeb.com):
   - Create new app > GitHub > select repo
   - Set build command:

   ```
   pip install -r requirements.txt
   ```

   - Set run command:

   ```
   python main.py
   ```

4. Add environment variables:
   - `API_ID`
   - `API_HASH`
   - `BOT_TOKEN`
   - `MONGO_URI`
   - `OWNER_ID`
   - `SESSION_STRING`

5. Deploy. Logs will show bot and user client running together.

## ⚠️ Notes
- Uses user account. Follow Telegram ToS strictly.
- Ideal for personal automation.
- 
