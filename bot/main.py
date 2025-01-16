import telebot
import requests
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Токен вашего бота
BOT_TOKEN = "ваш токен бота"
BASE_URL = "http://127.0.0.1:5000"  # Адрес вашего API

bot = telebot.TeleBot(BOT_TOKEN)

# Клавиатура для нового пользователя
def registration_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("📜 Регистрация"))
    return markup

# Клавиатура для зарегистрированного пользователя
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🔑 Сброс пароля"), KeyboardButton("👤 Моя информация"))
    markup.add(KeyboardButton("🏆 Таблица лидеров"))
    return markup

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    telegram_id = str(message.chat.id)
    response = requests.get(f"{BASE_URL}/check_user/{telegram_id}")

    if response.status_code == 200 and response.json().get('exists'):
        bot.send_message(
            message.chat.id,
            "👋 Привет! Добро пожаловать обратно! Выберите действие:",
            reply_markup=main_menu(),
        )
    else:
        bot.send_message(
            message.chat.id,
            "👋 Привет! Похоже, вы здесь впервые. Зарегистрируйтесь, чтобы начать!",
            reply_markup=registration_menu(),
        )

# Регистрация
@bot.message_handler(func=lambda msg: msg.text == "📜 Регистрация")
def register_user(message):
    bot.send_message(message.chat.id, "Введите свой никнейм (например, user123):")
    bot.register_next_step_handler(message, get_nickname)

def get_nickname(message):
    nickname = message.text
    bot.send_message(message.chat.id, "Введите пароль:")
    bot.register_next_step_handler(message, lambda msg: confirm_registration(msg, nickname))

def confirm_registration(message, nickname):
    password = message.text
    data = {
        "telegram_id": str(message.chat.id),
        "tg_nickname": nickname,
        "password": password
    }
    response = requests.post(f"{BASE_URL}/register_user", json=data)
    if response.status_code == 201:
        bot.send_message(
            message.chat.id,
            "✅ Регистрация прошла успешно! Теперь вы можете пользоваться ботом.",
            reply_markup=main_menu(),
        )
    elif response.status_code == 400:
        bot.send_message(message.chat.id, "⚠ Пользователь с таким ником уже существует.", reply_markup=registration_menu())
    else:
        bot.send_message(message.chat.id, "❌ Ошибка регистрации. Попробуйте позже.", reply_markup=registration_menu())

# Сброс пароля
@bot.message_handler(func=lambda msg: msg.text == "🔑 Сброс пароля")
def reset_password(message):
    data = {
        "telegram_id": str(message.chat.id)
    }
    reset_token = requests.post(f"{BASE_URL}/reset_password", json=data).json()['reset_token']
    bot.send_message(message.chat.id, "Введите новый пароль:")
    bot.register_next_step_handler(message, process_reset_password, reset_token)

def process_reset_password(message, reset_token):
    new_password = message.text
    data = {
        "telegram_id": str(message.chat.id),
        "new_password": new_password,
        "reset_token": reset_token
    }
    response = requests.post(f"{BASE_URL}/set_new_password", json=data)
    if response.status_code == 200:
        bot.send_message(message.chat.id, "✅ Пароль успешно сброшен!", reply_markup=main_menu())
    elif response.status_code == 400:
        bot.send_message(message.chat.id, "⚠ Токен недействителен или истёк.", reply_markup=main_menu())
    else:
        bot.send_message(message.chat.id, "❌ Ошибка сброса пароля. Попробуйте позже.", reply_markup=main_menu())

# Показать информацию о пользователе
@bot.message_handler(func=lambda msg: msg.text == "👤 Моя информация")
def show_user_info(message):
    telegram_id = message.chat.id
    response = requests.get(f"{BASE_URL}/show_user_info/{telegram_id}")
    if response.status_code == 200:
        user_data = response.json()
        bot.send_message(
            message.chat.id,
            f"👤 *Информация о пользователе:*\n"
            f"🆔 Telegram ID: {user_data['telegram_id']}\n"
            f"📛 Никнейм: {user_data['tg_nickname']}\n"
            f"💥 Количество кликов: {user_data['clicks']}\n"
            f"📅 Дата регистрации: {user_data['register_date']}",
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )
    else:
        bot.send_message(message.chat.id, "❌ Пользователь не найден.", reply_markup=main_menu())

# Таблица лидеров
@bot.message_handler(func=lambda msg: msg.text == "🏆 Таблица лидеров")
def get_leaders(message):
    response = requests.get(f"{BASE_URL}/get_leaders")
    if response.status_code == 200:
        leaders = response.json()
        leaderboard = "🏆 *Таблица лидеров:*\n\n"
        for i, user in enumerate(leaders, 1):
            leaderboard += f"{i}. {user['tg_nickname']} — {user['clicks']} кликов\n"
        bot.send_message(message.chat.id, leaderboard, parse_mode="Markdown", reply_markup=main_menu())
    else:
        bot.send_message(message.chat.id, "❌ Ошибка получения таблицы лидеров.", reply_markup=main_menu())

# Обработка ошибок
@bot.message_handler(func=lambda message: True)
def fallback(message):
    bot.send_message(message.chat.id, "❓ Я не понимаю эту команду. Выберите действие из меню.", reply_markup=main_menu())

# Запуск бота
if __name__ == '__main__':
    bot.infinity_polling()