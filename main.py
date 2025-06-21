import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import requests
import uuid
from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_ACCESS_TOKEN = os.getenv("TWITCH_ACCESS_TOKEN")
TWITCH_REFRESH_TOKEN = os.getenv("TWITCH_REFRESH_TOKEN")
TWITCH_CHANNEL_ID = os.getenv("TWITCH_CHANNEL_ID")
GIVEAWAY_LINK = "https://t.me/wickeddchannel/491"
TWITCH_CHANNEL_NAME = "wickeddwb"
PORT = int(os.getenv("PORT", 8443))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def get_twitch_token():
    global TWITCH_ACCESS_TOKEN
    if not TWITCH_ACCESS_TOKEN:
        logger.error("Токен доступа Twitch не найден")
        return None
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {TWITCH_ACCESS_TOKEN}",
    }
    response = requests.get("https://api.twitch.tv/helix/users?login=wickeddwb", headers=headers)
    if response.status_code == 401:
        logger.warning("Токен истек, обновляем")
        new_access_token, new_refresh_token = refresh_twitch_token(TWITCH_REFRESH_TOKEN)
        if new_access_token:
            TWITCH_ACCESS_TOKEN = new_access_token
            os.environ["TWITCH_ACCESS_TOKEN"] = new_access_token
            if new_refresh_token:
                os.environ["TWITCH_REFRESH_TOKEN"] = new_refresh_token
            return new_access_token
        return None
    return TWITCH_ACCESS_TOKEN

def refresh_twitch_token(refresh_token):
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    response = requests.post(url, params=params)
    if response.status_code == 200:
        data = response.json()
        logger.info(f"Токен обновлен: {data['access_token']}")
        return data["access_token"], data.get("refresh_token")
    logger.error(f"Ошибка обновления токена: {response.text}")
    return None, None

def check_twitch_follower(twitch_username):
    access_token = get_twitch_token()
    if not access_token:
        return False

    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}",
    }

    user_url = f"https://api.twitch.tv/helix/users?login={twitch_username}"
    user_response = requests.get(user_url, headers=headers)
    if user_response.status_code != 200 or not user_response.json().get("data"):
        logger.error(f"Ошибка получения user_id для {twitch_username}: {user_response.text}")
        return False
    user_id = user_response.json()["data"][0]["id"]
    logger.info(f"Получен user_id: {user_id} для {twitch_username}")

    follow_url = f"https://api.twitch.tv/helix/channels/followers?broadcaster_id={TWITCH_CHANNEL_ID}&user_id={user_id}"
    follow_response = requests.get(follow_url, headers=headers)
    if follow_response.status_code == 200 and follow_response.json().get("data"):
        logger.info(f"Пользователь {twitch_username} является фолловером")
        return True
    logger.warning(f"Пользователь {twitch_username} не является фолловером: {follow_response.text}")
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Отправьте свой Twitch-username для проверки, следите ли вы за twitch.tv/{TWITCH_CHANNEL_NAME}."
    )
    context.user_data["awaiting_twitch_username"] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_twitch_username"):
        twitch_username = update.message.text.strip()
        if check_twitch_follower(twitch_username):
            unique_id = str(uuid.uuid4())
            giveaway_url = f"{GIVEAWAY_LINK}&user_id={update.message.from_user.id}_{unique_id}"
            await update.message.reply_text(
                f"Вы следите за twitch.tv/{TWITCH_CHANNEL_NAME}! Перейдите по ссылке для участия в розыгрыше: {giveaway_url}"
            )
        else:
            await update.message.reply_text(
                f"Вы не следите за twitch.tv/{TWITCH_CHANNEL_NAME} или username неверный. Начните следить и попробуйте снова."
            )
        context.user_data["awaiting_twitch_username"] = False
    else:
        await update.message.reply_text("Отправьте /start, чтобы начать.")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен")
    if WEBHOOK_URL:
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
        )
    else:
        logger.warning("WEBHOOK_URL не указан, используется polling")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
