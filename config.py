import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
AUTHORIZED_USERS = [
    7080662182,  # Telegram ID авторизованных пользователей
    6439176819
]
if not API_TOKEN or not MONGO_URI:
    raise ValueError("Необходимо указать API_TOKEN и MONGO_URI в файле .env!")
