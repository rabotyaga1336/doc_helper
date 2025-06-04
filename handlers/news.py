import sqlite3
import os
from config import DB_NAME, IMAGE_DIR, ADMIN_ID
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def delete_news(update, context):
    """Удаление новости из БД"""
    query = update.callback_query
    news_id = query.data.split('_')[1]  # Извлекаем ID из callback_data "delete_123"

    if query.from_user.id != ADMIN_ID:
        query.answer("❌ Недостаточно прав!")
        return

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # 1. Получаем путь к изображению для удаления файла
        cursor.execute("SELECT image_path FROM news WHERE id = ?", (news_id,))
        result = cursor.fetchone()
        image_path = result[0] if result else None

        # 2. Удаляем запись из БД
        cursor.execute("DELETE FROM news WHERE id = ?", (news_id,))
        conn.commit()

        # 3. Удаляем файл изображения, если он существует
        if image_path:
            full_path = os.path.join(IMAGE_DIR, image_path)
            if os.path.exists(full_path):
                os.remove(full_path)

        query.answer("✅ Новость удалена!")
        # Возвращаем пользователя в меню новостей
        show_news_menu(update, context)

    except Exception as e:
        logger.error(f"Ошибка удаления новости: {e}")
        query.answer("❌ Ошибка при удалении")
    finally:
        if conn:
            conn.close()


def get_news(limit=5):
    """Получаем последние новости из БД."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, content, image_path, date FROM news ORDER BY date DESC LIMIT ?",
        (limit,)
    )
    news = cursor.fetchall()
    conn.close()
    return news


def show_news_detail(update, context, news_id):
    """Показываем полный текст новости с обработкой изображений"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT title, content, image_path, date FROM news WHERE id = ?",
            (news_id,)
        )
        result = cursor.fetchone()

        if not result:
            update.callback_query.answer("Новость не найдена!")
            return

        title, content, image_path, date = result

        # Форматируем текст
        try:
            formatted_date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
        except:
            formatted_date = "Дата не указана"

        text = f"<b>{title}</b>\n\n{content}\n\n<em>{formatted_date}</em>"

        # Формируем клавиатуру
        keyboard = []
        if update.callback_query.from_user.id == ADMIN_ID:
            keyboard.append(
                [InlineKeyboardButton(
                    "❌ Удалить новость",
                    callback_data=f"confirm_delete_{news_id}"
                )]
            )
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_news")])

        # Если есть изображение
        if image_path and os.path.exists(os.path.join(IMAGE_DIR, image_path)):
            # Отправляем новое сообщение с фото
            with open(os.path.join(IMAGE_DIR, image_path), 'rb') as img:
                sent_msg = context.bot.send_photo(
                    chat_id=update.callback_query.message.chat_id,
                    photo=img,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

            # Сохраняем ID нового сообщения для последующего удаления
            context.user_data['last_news_msg_id'] = sent_msg.message_id
        else:
            # Отправляем просто текст
            sent_msg = context.bot.send_message(
                chat_id=update.callback_query.message.chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            context.user_data['last_news_msg_id'] = sent_msg.message_id

        # Пытаемся удалить старое сообщение (не критично, если не получится)
        try:
            context.bot.delete_message(
                chat_id=update.callback_query.message.chat_id,
                message_id=update.callback_query.message.message_id
            )
        except:
            pass

    except Exception as e:
        logger.error(f"Ошибка при показе новости: {e}")
        update.callback_query.answer("❌ Ошибка загрузки новости")
    finally:
        conn.close()


def confirm_delete(update, context):
    """Подтверждение удаления новости с учетом типа сообщения"""
    query = update.callback_query
    news_id = query.data.split('_')[2]

    # Создаем новое сообщение для подтверждения
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Вы уверены, что хотите удалить эту новость?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да, удалить", callback_data=f"delete_{news_id}")],
            [InlineKeyboardButton("❌ Нет, отмена", callback_data=f"news_{news_id}")]
        ])
    )

    # Пытаемся удалить предыдущее сообщение
    try:
        context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
    except:
        pass


def show_news_menu(update, context):
    """Улучшенное меню новостей"""
    try:
        news = get_news()
        keyboard = []

        for news_item in news:
            btn_text = f"📰 {news_item[1]}"
            if update.callback_query.from_user.id == ADMIN_ID:
                btn_text += f" (ID: {news_item[0]})"
        if update.callback_query.from_user.id == ADMIN_ID:
            keyboard.append([InlineKeyboardButton("➕ Добавить новость", callback_data="add_news")])
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"news_{news_item[0]}")])


        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])

        # Всегда отправляем новое сообщение
        context.bot.send_message(
            chat_id=update.callback_query.message.chat_id,
            text="📢 Последние новости:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


        # Пытаемся удалить предыдущее сообщение
        try:
            context.bot.delete_message(
                chat_id=update.callback_query.message.chat_id,
                message_id=update.callback_query.message.message_id
            )
        except:
            pass

    except Exception as e:
        logger.error(f"Ошибка при показе меню новостей: {e}")
        update.callback_query.answer("❌ Ошибка загрузки новостей")