import sqlite3
import os
import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, MessageHandler, Filters, ConversationHandler
from config import DB_PATH, IMAGE_DIR, ADMIN_ID, WAIT_IMAGE, WAIT_TITLE, WAIT_CONTENT


logger = logging.getLogger(__name__)


def get_all_news():
    """Получаем все новости из БД"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, content, image_path, date FROM news ORDER BY date DESC"
            )
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка получения новостей: {str(e)}")
        return []

def get_news_by_id(news_id):
    """Получение конкретной новости"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT title, content, image_path, date FROM news WHERE id = ?", (news_id,))
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Ошибка получения новости {news_id}: {str(e)}")
        return None

def show_news_menu(update, context):
    """Отображает меню новостей"""
    query = update.callback_query
    query.answer()

    try:
        news_items = get_all_news()

        if not news_items:
            query.edit_message_text("📭 Новостей пока нет")
            return

        keyboard = []
        for news_id, title, _, _, date in news_items:
            formatted_date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y")
            btn_text = f"📰 {title} ({formatted_date})"

            keyboard.append([
                InlineKeyboardButton(
                btn_text,
                callback_data=f"news_{news_id}"  # Унифицированный префикс
            )])

        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])

        query.edit_message_text(
            "📢 Выберите новость:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Ошибка в show_news_menu: {str(e)}")
        query.edit_message_text("❌ Ошибка загрузки меню")


def show_news_detail(update, context, news_id):
    """Показ полной новости"""
    query = update.callback_query
    query.answer()

    try:
        logger.info(f"Пытаемся загрузить новость ID: {news_id}")  # Логируем

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            logger.info(f"Выполняем запрос для news_id={news_id}")
            cursor.execute(
                "SELECT title, content, image_path, date FROM news WHERE id = ?",
                (news_id,))
            news = cursor.fetchone()
            logger.info(f"Результат запроса: {news}")  # Логируем результат

            if not news:
                # Используем новое сообщение вместо редактирования
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="❌ Новость не найдена"
                )
                return

            title, content, image_path, date = news
            formatted_date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
            text = f"<b>{title}</b>\n\n{content}\n\n<em>{formatted_date}</em>"

            keyboard = [
                [InlineKeyboardButton("📰 К списку новостей", callback_data="news")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ]

            if query.from_user.id == ADMIN_ID:
                keyboard.append(
                    [InlineKeyboardButton("❌ Удалить", callback_data=f"confirm_delete_{news_id}")]
                )

            if image_path and os.path.exists(os.path.join(IMAGE_DIR, image_path)):
                with open(os.path.join(IMAGE_DIR, image_path), 'rb') as img:
                    context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=img,
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
            else:
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
           # Пытаемся удалить предыдущее сообщение (не обязательно)
            try:
                context.bot.delete_message(
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id
                )
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение: {e}")

    except Exception as e:
        logger.error(f"Ошибка в show_news_detail: {str(e)}")
        query.edit_message_text("❌ Ошибка загрузки новости")


def add_news(update, context):
    """Обработчик начала добавления новости"""
    try:
        # Получаем сообщение в зависимости от типа вызова
        if update.callback_query:
            message = update.callback_query.message
            update.callback_query.answer()
        else:
            message = update.message

        # Проверка прав администратора
        if update.effective_user.id != ADMIN_ID:
            context.bot.send_message(
                chat_id=message.chat_id,
                text="❌ У вас нет прав админа!"
            )
            return ConversationHandler.END

        # Очистка предыдущих данных
        context.user_data.clear()

        # Запрос изображения
        context.bot.send_message(
            chat_id=message.chat_id,
            text="Пришлите изображение для новости (или /skip чтобы пропустить)",
            reply_markup=ReplyKeyboardRemove()
        )
        return WAIT_IMAGE

    except Exception as e:
        logger.error(f"Ошибка в add_news: {e}")
        return ConversationHandler.END



def handle_image(update, context):
    """Обработка изображения"""
    try:
        if update.message.text == "/skip":
            context.user_data['news_image'] = None
            update.message.reply_text("📝 Введите заголовок новости:")
            return WAIT_TITLE

        if update.message.photo:
            photo = update.message.photo[-1]
            file = photo.get_file()
            filename = f"news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            os.makedirs(IMAGE_DIR, exist_ok=True)
            file.download(os.path.join(IMAGE_DIR, filename))
            context.user_data['news_image'] = filename
            update.message.reply_text("✅ Изображение сохранено! Введите заголовок:")
            return WAIT_TITLE

        update.message.reply_text("Пожалуйста, отправьте изображение или /skip")
        return WAIT_IMAGE

    except Exception as e:
        logger.error(f"Ошибка в handle_image: {e}")

    update.message.reply_text("Отправьте изображение или /skip")
    return WAIT_IMAGE


def save_news(update, context):
    """Сохранение заголовка"""
    try:
        context.user_data['news_title'] = update.message.text
        update.message.reply_text("📝 Теперь введите текст новости:")
        return WAIT_CONTENT
    except Exception as e:
        logger.error(f"Ошибка в save_news: {e}")
        return ConversationHandler.END


def finish_news(update, context):
    """Финальное сохранение"""
    conn = None
    try:
        if 'news_title' not in context.user_data:
            update.message.reply_text("❌ Ошибка: не указан заголовок")
            return ConversationHandler.END

        # Подключение к БД
        conn = sqlite3.connect("news_images/bot.db")
        cursor = conn.cursor()

        # Сохранение в БД
        cursor.execute(
            "INSERT INTO news (title, content, image_path, date) VALUES (?, ?, ?, ?)",
            (
                context.user_data['news_title'],
                update.message.text,
                context.user_data.get('news_image'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        conn.commit()
        update.message.reply_text("✅ Новость успешно добавлена!")

    except Exception as e:
        logger.error(f"Ошибка сохранения: {e}")
        update.message.reply_text("❌ Ошибка при сохранении")

    finally:
        if 'conn' in locals():
            conn.close()
        context.user_data.clear()

    return ConversationHandler.END


def cancel(update, context):
    """Отмена добавления новости"""
    update.message.reply_text("❌ Добавление новости отменено.")
    # Очищаем временные данные
    context.user_data.pop('news_image', None)
    context.user_data.pop('news_title', None)
    return ConversationHandler.END


def delete_news(update, context):
    """Удаление новости"""
    query = update.callback_query
    news_id = query.data.split('_')[1]

    if query.from_user.id != ADMIN_ID:
        query.answer("🚫 Недостаточно прав!")
        return

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Получаем путь к изображению
            cursor.execute("SELECT image_path FROM news WHERE id = ?", (news_id,))
            result = cursor.fetchone()

            if result and result[0]:
                image_path = os.path.join(IMAGE_DIR, result[0])
                if os.path.exists(image_path):
                    os.remove(image_path)

            # Удаляем запись из БД
            cursor.execute("DELETE FROM news WHERE id = ?", (news_id,))
            conn.commit()

        query.answer("✅ Новость удалена")
        show_news_menu(update, context)

    except Exception as e:
        logger.error(f"Ошибка удаления новости: {str(e)}")
        query.answer("❌ Ошибка при удалении")


def confirm_delete(update, context):
    """Подтверждение удаления новости"""
    query = update.callback_query
    news_id = query.data.split('_')[2]

    # Отправляем сообщение с подтверждением
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="⚠️ Вы уверены, что хотите удалить эту новость?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Да", callback_data=f"delete_{news_id}"),
                InlineKeyboardButton("❌ Нет", callback_data=f"show_news_{news_id}")
            ]
        ])
    )

    # Удаляем предыдущее сообщение
    try:
        context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
    except:
        pass


# --- Регистрация обработчиков ---
def setup_news_handlers(dp):
    """Регистрация всех обработчиков новостей"""
    try:
        # Обычные команды
        dp.add_handler(CommandHandler("news", show_news_menu))

        # Админ-панель
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('add_news', add_news)],
            states={
                WAIT_IMAGE: [MessageHandler(Filters.photo | (Filters.text & ~Filters.command), handle_image)],
                WAIT_TITLE: [MessageHandler(Filters.text & ~Filters.command, save_news)],
                WAIT_CONTENT: [MessageHandler(Filters.text & ~Filters.command, finish_news)]
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )
        dp.add_handler(conv_handler)

    except Exception as e:
        logger.error(f"Ошибка регистрации обработчиков: {e}")