# handlers/docs.py
import sqlite3
from config import DB_PATH
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_documents(doc_type: str) -> list:
    """Получаем документы из БД по типу."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, file_path FROM documents WHERE type = ?",
        (doc_type,)
    )
    docs = cursor.fetchall()
    conn.close()
    return docs


def show_docs_menu(update, context):
    """Показываем меню типов документов."""
    keyboard = [
        [InlineKeyboardButton("📝 Заявления", callback_data="docs_application")],
        [InlineKeyboardButton("📑 Шаблоны", callback_data="docs_template")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    update.callback_query.edit_message_text(
        "📄 Выберите тип документа:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def show_documents_list(update, context, doc_type: str):
    """Показываем список документов."""
    docs = get_documents(doc_type)
    keyboard = []
    for doc in docs:
        # Формируем кнопки: название -> file_path
        keyboard.append([InlineKeyboardButton(doc[0], callback_data=f"file_{doc[1]}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="docs")])

    update.callback_query.edit_message_text(
        "📂 Доступные документы:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def send_document(update, context, file_path: str):
    """Отправляем файл пользователю."""
    chat_id = update.callback_query.message.chat_id
    try:
        with open(file_path, 'rb') as file:
            context.bot.send_document(chat_id, document=file)
    except FileNotFoundError:
        context.bot.send_message(chat_id, "❌ Файл не найден.")