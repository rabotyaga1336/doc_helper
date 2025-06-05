import sqlite3
import os
import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import DB_PATH, IMAGE_DIR, ADMIN_ID

logger = logging.getLogger(__name__)


def show_news_detail():
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


def show_news_menu(update, context):
    """Отображает меню новостей в виде кнопок"""
    try:
        news_items = show_news_detail()

        if not news_items:
            update.callback_query.answer("📭 Новостей пока нет")
            return

        # Создаем кнопки для каждой новости
        keyboard = []
        for news in news_items:
            news_id, title, _, _, date = news
            formatted_date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y")

            # Добавляем иконку изображения если оно есть
            btn_text = f"📰 {title}" if not news[3] else f"🖼 {title}"
            btn_text += f" ({formatted_date})"

            keyboard.append([InlineKeyboardButton(
                text=btn_text,
                callback_data=f"show_news_{news_id}"
            )])

        # Добавляем кнопку возврата
        keyboard.append([InlineKeyboardButton(
            "🔙 Назад",
            callback_data="back_to_main"
        )])

        # Отправляем меню
        update.callback_query.edit_message_text(
            text="📢 Выберите новость для просмотра:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Ошибка показа меню новостей: {str(e)}")
        update.callback_query.answer("❌ Ошибка загрузки меню")


def show_news(update, context, news_id):
    """Отображает полную новость с изображением"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT title, content, image_path, date FROM news WHERE id = ?",
                (news_id,)
            )
            news = cursor.fetchone()

            if not news:
                update.callback_query.answer("❌ Новость не найдена")
                return

            title, content, image_path, date = news
            formatted_date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")

            # Форматируем текст новости
            news_text = f"<b>{title}</b>\n\n{content}\n\n<em>{formatted_date}</em>"

            # Создаем кнопки для управления
            keyboard = [
                [InlineKeyboardButton("📰 К списку новостей", callback_data="back_to_news")]
            ]

            # Отправляем новость с изображением или без
            if image_path and os.path.exists(os.path.join(IMAGE_DIR, image_path)):
                with open(os.path.join(IMAGE_DIR, image_path), 'rb') as img:
                    context.bot.send_photo(
                        chat_id=update.callback_query.message.chat_id,
                        photo=img,
                        caption=news_text,
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
            else:
                context.bot.send_message(
                    chat_id=update.callback_query.message.chat_id,
                    text=news_text,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

            # Удаляем предыдущее сообщение с меню
            try:
                context.bot.delete_message(
                    chat_id=update.callback_query.message.chat_id,
                    message_id=update.callback_query.message.message_id
                )
            except:
                pass

    except Exception as e:
        logger.error(f"Ошибка показа новости: {str(e)}")
        update.callback_query.answer("❌ Ошибка загрузки новости")


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