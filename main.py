# main.py
import logging
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, CallbackQueryHandler,
                          ConversationHandler, MessageHandler, Filters)
from keyboards import main_menu, back_button
from config import BOT_TOKEN, ADMIN_ID, WAIT_IMAGE, WAIT_TITLE, WAIT_CONTENT
from handlers.docs import show_docs_menu, show_documents_list, send_document
from handlers.news import (show_news_menu, show_news_detail, confirm_delete, delete_news,
                           add_news, handle_image, save_news, finish_news, cancel)

# Включаем логирование для отладки
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)


def get_persistent_keyboard():
    """Возвращает постоянную Reply-клавиатуру с кнопкой Главного меню"""
    return ReplyKeyboardMarkup([['🏠 Главное меню']], resize_keyboard=True, persistent=True)


def start(update, context):
    """Обработчик команды /start"""
    # Сбрасываем любые состояния диалога
    if 'conversation' in context.user_data:
        del context.user_data['conversation']

    # Очищаем временные данные
    context.user_data.pop('news_image', None)
    context.user_data.pop('news_title', None)

    # Отправляем главное меню
    update.message.reply_text(
        "Приветствую! Выберите действие:",
        reply_markup=main_menu()
    )


def button_click(update, context):
    query = update.callback_query
    data = query.data

    if data == "start":
        start(update, context)
    elif data == "docs":
        show_docs_menu(update, context)
    elif data == "docs_application":
        show_documents_list(update, context, "application")
    elif data == "docs_template":
        show_documents_list(update, context, "template")
    elif data.startswith("file_"):
        file_path = data.replace("file_", "")
        send_document(update, context, file_path)
    elif data == "contacts":
        query.edit_message_text(
            "📞 Контакты предприятия:\n\n"
            "📱 Телефон: +375 (XX) XXX-XX-XX\n"
            "✉️ Email: info@prof.by",
            reply_markup=back_button()
        )
    elif data == "news":
        show_news_menu(update, context)
    elif data == "add_news":
        add_news(update, context)
    elif data.startswith("news_"):
        news_id = data.split('_')[1]
        show_news_detail(update, context, news_id)
    elif data.startswith("delete_"):
        delete_news(update, context)
    elif data.startswith("confirm_delete_"):
        confirm_delete(update, context)
    elif data == "back_to_news":
        show_news_menu(update, context)
    elif data == "back_to_main":
        query.edit_message_text(
            "🔹 Главное меню:",
            reply_markup=main_menu()
        )


def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Регистрируем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.regex('^🏠 Главное меню$'), start))
    dp.add_handler(CallbackQueryHandler(button_click))

    # --- АДМИН-ПАНЕЛЬ ---
    dp.add_handler(ConversationHandler(
        entry_points=[
            CommandHandler('add_news', add_news),  # Для команды /add_news
            CallbackQueryHandler(add_news, pattern='^add_news$')  # Для кнопки
        ],
        states={
            WAIT_IMAGE: [  # Ожидаем фото или команду /skip
                MessageHandler(Filters.photo, handle_image),
                CommandHandler('skip', handle_image)
            ],
            WAIT_TITLE: [  # Ожидаем текст заголовка
                MessageHandler(Filters.text & ~Filters.command, save_news)
            ],
            WAIT_CONTENT: [  # Ожидаем текст новости
                MessageHandler(Filters.text & ~Filters.command, finish_news)
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            MessageHandler(Filters.regex('^🏠 Главное меню$'), start)
        ],  # Точки выхода из диалога
    ))

    updater.start_polling()
    print("Бот запущен с базой данных!")
    updater.idle()


if __name__ == "__main__":
    main()