# Getting Started: API Tokens & IDs

To run the Avionyx bot, you need two pieces of information:

## 1. Telegram Bot Token (`TELEGRAM_TOKEN`)

This identifies your bot to Telegram.

1. Open Telegram and search for **@BotFather**.
2. Send the command `/newbot`.
3. Follow the instructions to name your bot (e.g., "My Farm Bot") and give it a username (e.g., "my_farm_bot").
4. BotFather will send you a message with your **HTTP API Token**.
   - It looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
   - Copy this token.

## 2. Admin IDs (`ADMIN_IDS`)

This restricts access to the bot so only you (and people you trust) can control it.

1. Open Telegram and search for **@userinfobot**.
2. Start the bot.
3. It will reply with your user details. Look for **Id**.
   - Example: `123456789`
4. If you have multiple admins, separate their IDs with commas (no spaces).
   - Example: `123456789,987654321`

---
**Note:** Enter these values when prompted by the `deploy.sh` script, or manually add them to your `.env` file.
