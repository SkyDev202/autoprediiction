# Railway Deployment

1. Push this folder to a GitHub repository.
2. Create a Railway project from that repository.
3. Railway will install `requirements.txt` and start the worker with `python bot.py`.
4. Add a Railway Volume mounted at `/app` so `config.json`, `userbot.session`, stickers, and prediction images survive restarts.
5. Do not run another copy of the bot locally while Railway is running. Telegram polling permits only one active instance per bot token.

The required bot token, Telegram API credentials, phone, and primary admin ID are currently configured inside `bot.py`.
