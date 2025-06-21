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
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_ACCESS_TOKEN = os.getenv("TWITCH_ACCESS_TOKEN")
TWITCH_REFRESH_TOKEN = os.getenv("TWITCH_REFRESH_TOKEN")
TWITCH_CHANNEL_ID = os.getenv("TWITCH_CHANNEL_ID")
PRIVATE_CHANNEL_ID = "-1002760888539"
TWITCH_CHANNEL_NAME = "wickeddwb"
PORT = int(os.getenv("PORT", 8443))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
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
    logger.debug(f"Проверка фолловера: {twitch_username}")
    access_token = get_twitch_token()
    if not access_token:
        logger.error("Токен доступа отсутствует")
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

async def create_invite_link(context: ContextTypes.DEFAULT_TYPE, chat_id: str):
    try:
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=chat_id,
            name=f"Invite for {uuid.uuid4().hex[:8]}",
            member_limit=1,
            expire_date=None 
        )
        return invite_link.invite_link
    except Exception as e:
        logger.error(f"Ошибка создания пригласительной ссылки: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug(f"Получена команда /start от пользователя {update.effective_user.id}")
    try:
        await update.message.reply_text(
            f"Отправьте свой Twitch-username для проверки подписки на twitch.tv/{TWITCH_CHANNEL_NAME}."
        )
        context.user_data["awaiting_twitch_username"] = True
        logger.info("Команда /start обработана успешно")
    except Exception as e:
        logger.error(f"Ошибка в обработчике start: {e}")
        raise

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug(f"Получено сообщение: {update.message.text} от пользователя {update.effective_user.id}")
    try:
        if context.user_data.get("awaiting_twitch_username"):
            twitch_username = update.message.text.strip()
            logger.info(f"Проверяем Twitch-username: {twitch_username}")
            if check_twitch_follower(twitch_username):
                await update.message.reply_text(
                    f"Проверка прошла успешно! Вы следите за twitch.tv/{TWITCH_CHANNEL_NAME}."
                )
                invite_link = await create_invite_link(context, PRIVATE_CHANNEL_ID)
                if invite_link:
                    await update.message.reply_text(
                        f"Вот ваша уникальная ссылка на приватный тг канал с розыгрышем: {invite_link}"
                    )
                    logger.info(f"Пользователь {twitch_username} получил пригласительную ссылку")
                else:
                    await update.message.reply_text(
                        "Ошибка при создании ссылки. Попробуйте позже."
                    )
                    logger.error(f"Не удалось создать ссылку для {twitch_username}")
            else:
                await update.message.reply_text(
                    f"Вы не следите за twitch.tv/{TWITCH_CHANNEL_NAME} или username неверный. "
                    f"Подпишитесь и попробуйте снова."
                )
            context.user_data["awaiting_twitch_username"] = False
        else:
            await update.message.reply_text("Отправьте /start, чтобы начать.")
            logger.info("Пользователь отправил сообщение без /start")
    except Exception as e:
        logger.error(f"Ошибка в обработчике сообщений: {e}")
        raise

def main():
    logger.debug("Инициализация приложения")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен")
    try:
        if WEBHOOK_URL:
            logger.debug(f"Запуск вебхука на {WEBHOOK_URL}:{PORT}/{TELEGRAM_TOKEN}")
            app.run_webhook(
                listen="0.0.0.0",
                port=PORT,
                url_path=TELEGRAM_TOKEN,
                webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
            )
        else:
            logger.warning("WEBHOOK_URL не указан, используется polling")
            app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise

if __name__ == "__main__":
    main()
