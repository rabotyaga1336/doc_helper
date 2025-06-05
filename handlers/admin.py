from telegram.ext import (CommandHandler, MessageHandler,
                          filters, ConversationHandler)
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
import sqlite3
from config import (DB_PATH, IMAGE_DIR, ADMIN_ID,
                    WAIT_IMAGE, WAIT_TITLE, WAIT_CONTENT)
import os
import logging
from datetime import datetime
from keyboards import main_menu, get_main_reply_keyboard

logger = logging.getLogger(__name__)


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


def cancel(update, context):
    """Отмена добавления новости"""
    try:
        update.message.reply_text("❌ Добавление новости отменено.")
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Ошибка в cancel: {e}")
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


def delete_news(update, context):
    """Удаление новости"""
    query = update.callback_query
    news_id = query.data.split('_')[1]

    if query.from_user.id != ADMIN_ID:
        query.answer("❌ Недостаточно прав!")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Получаем данные новости перед удалением
        cursor.execute("SELECT image_path FROM news WHERE id = ?", (news_id,))
        result = cursor.fetchone()

        if not result:
            query.answer("Новость не найдена!")
            return

        image_path = result[0]

        # Удаляем запись
        cursor.execute("DELETE FROM news WHERE id = ?", (news_id,))
        conn.commit()

        # Удаляем изображение если есть
        if image_path:
            full_path = os.path.join(IMAGE_DIR, image_path)
            if os.path.exists(full_path):
                os.remove(full_path)

        query.answer("✅ Новость удалена!")

        # Всегда отправляем новое сообщение с меню
        show_news_menu(update, context, force_new_message=True)

    except Exception as e:
        logger.error(f"Ошибка удаления новости: {e}")
        query.answer("❌ Ошибка при удалении")
    finally:
        conn.close()


def cancel(update, context):
    """Отмена добавления новости"""
    update.message.reply_text("❌ Добавление новости отменено.")
    # Очищаем временные данные
    context.user_data.pop('news_image', None)
    context.user_data.pop('news_title', None)
    return ConversationHandler.END


def show_news_menu(update, context, force_new_message=False):
    """Улучшенное меню новостей"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title FROM news ORDER BY date DESC LIMIT 10"
        )
        news = cursor.fetchall()

        keyboard = [
            [InlineKeyboardButton(f"📰 {title}", callback_data=f"news_{id_}")]
            for id_, title in news
        ]


        if force_new_message or not hasattr(update.callback_query.message, 'text'):
            # Всегда отправляем новое сообщение при принудительном запросе или если нет текста
            context.bot.send_message(
                chat_id=update.callback_query.message.chat_id,
                text="📢 Последние новости:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            try:
                # Пытаемся отредактировать существующее сообщение
                update.callback_query.edit_message_text(
                    text="📢 Последние новости:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except:
                # Если не получилось редактировать - отправляем новое
                context.bot.send_message(
                    chat_id=update.callback_query.message.chat_id,
                    text="📢 Последние новости:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

    except Exception as e:
        logger.error(f"Ошибка показа меню новостей: {e}")
        update.callback_query.answer("❌ Ошибка загрузки новостей")
    finally:
        conn.close()


def show_news_detail(update, context, news_id):
    """Показ полной новости с обработкой изображений"""
    try:
        conn = sqlite3.connect(DB_PATH)
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
        keyboard = [
        [InlineKeyboardButton("🏠 Старт", callback_data="start")],
        [InlineKeyboardButton("🔙 Назад", callback_data="news")]
        ]
        if update.callback_query.from_user.id == ADMIN_ID:
            keyboard.append(
                [InlineKeyboardButton(
                    "❌ Удалить новость",
                    callback_data=f"confirm_delete_{news_id}"
                )]
            )

        # Всегда отправляем новое сообщение
        if image_path and os.path.exists(os.path.join(IMAGE_DIR, image_path)):
            with open(os.path.join(IMAGE_DIR, image_path), 'rb') as img:
                context.bot.send_photo(
                    chat_id=update.callback_query.message.chat_id,
                    photo=img,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            context.bot.send_message(
                chat_id=update.callback_query.message.chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        # Пытаемся удалить предыдущее сообщение (не обязательно)
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
    """Подтверждение удаления новости"""
    query = update.callback_query
    news_id = query.data.split('_')[2]

    # Всегда отправляем новое сообщение для подтверждения
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Вы уверены, что хотите удалить эту новость?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да, удалить", callback_data=f"delete_{news_id}")],
            [InlineKeyboardButton("❌ Нет, отмена", callback_data=f"news_{news_id}")]
        ])
    )

    # Пытаемся удалить предыдущее сообщение (не обязательно)
    try:
        context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
    except:
        pass


def start(update, context):
    """Обработчик команды /start и кнопки 'Главное меню'"""
    # Очищаем временные данные
    context.user_data.clear()

    # Отправляем сообщение с inline-кнопками
    update.message.reply_text(
        "Выберите раздел:",
        reply_markup=main_menu()  # Основное меню как inline-кнопки
    )

    # Устанавливаем Reply-клавиатуру с одной кнопкой
    update.message.reply_text(
        "Используйте кнопку ниже для возврата:",
        reply_markup=get_main_reply_keyboard()  # Только "Главное меню"
    )
    return ConversationHandler.END