# config.py
import os

BOT_TOKEN = "7879409153:AAE4ShIxUqXIqZ2dO7bnWIBKQbIFIJnAzL8"
DB_PATH = os.path.join("news_images", "bot.db")  # Имя файла базы данных
IMAGE_DIR = "news_images"  # Папка для хранения изображений
ADMIN_ID = 774229520

# States для ConversationHandler
WAIT_IMAGE, WAIT_TITLE, WAIT_CONTENT = range(3)