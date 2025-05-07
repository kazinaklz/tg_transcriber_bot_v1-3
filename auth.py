import aiohttp    # для работы с асинхронным запросом к Airtable API
import os
from dotenv import load_dotenv     # для загрузки переменных окружения из файла .env

load_dotenv()

# Получение значений переменных окружения
BASE_ID = os.getenv("AIRTABLE_BASE_ID")
TABLE_MAIN = os.getenv("AIRTABLE_TABLE_MAIN")
TABLE_LOG = os.getenv("AIRTABLE_TABLE_LOG")
AIRTABLE_TOKEN = os.getenv("AIRTABLE_API_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}



# === Проверка, есть ли пользователь в таблице ===
async def check_user_registered(user_id: int) -> dict | None:
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_MAIN}" # Эндпоинт API Airtable
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp:
            data = await resp.json()

    for record in data.get("records", []):
        fields = record.get("fields", {})
        if fields.get("UserID") == str(user_id):
            return fields

    return None



# === Регистрация нового пользователя ===
async def register_user(user_id: int, username: str):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_MAIN}" # Эндпоинт API Airtable
    payload = {
        "records": [{
            "fields": {
                "UserID": str(user_id),
                "UserName": username or "no_username"
            }
        }]
    }

    async with aiohttp.ClientSession() as session:
        await session.post(url, json=payload, headers=HEADERS)



# === Логирование действий пользователя ===
async def log_action(user_id: int, username: str, action: str):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_LOG}" # Эндпоинт API Airtable
    payload = {
        "records": [{
            "fields": {
                "TelegramID": str(user_id),
                "ФИО": username or "no_username",
                "Действие": action
            }
        }]
    }

    async with aiohttp.ClientSession() as session:
        await session.post(url, json=payload, headers=HEADERS)
