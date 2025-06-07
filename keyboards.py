# keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from config import ADMIN_ID

def main_menu(user_id=False):
    keyboard = [
        [InlineKeyboardButton("📄 Документы", callback_data="docs")],
        [InlineKeyboardButton("📞 Контакты", callback_data="contacts")],
        [InlineKeyboardButton("📢 Новости", callback_data="news")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]

    return InlineKeyboardMarkup(keyboard)

def get_main_reply_keyboard():
    """Возвращает только одну кнопку 'Главное меню' в Reply-клавиатуре"""
    return ReplyKeyboardMarkup([["🏠 Главное меню"]], resize_keyboard=True, persistent=True)

# keyboards.py
def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton
                                  ("🔙 Назад", callback_data="back_to_main")]])