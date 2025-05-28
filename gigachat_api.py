import os
import uuid
import aiohttp
from aiohttp import BasicAuth
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Получаем значения из окружения
CLIENT_ID = os.getenv("CLIENT_ID")
SECRET = os.getenv("SECRET")
MODEL = os.getenv("GIGACHAT_MODEL", "GigaChat-Max")


# URL для получения токена и отправки сообщений
GIGACHAT_TOKEN_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"



# === Получение токена доступа GigaChat ===
async def get_access_token():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",  # Формат отправляемых данных
        "Accept": "application/json",                         # Ожидаемый формат ответа
        "RqUID": str(uuid.uuid4())                            # Уникальный идентификатор запроса
    }
    data = {
        "scope": "GIGACHAT_API_PERS"  # Область действия токена
    }

    # Создаём сессию и отправляем POST-запрос
    async with aiohttp.ClientSession() as session:
        async with session.post(
            GIGACHAT_TOKEN_URL,
            headers=headers,
            data=data,
            auth=BasicAuth(CLIENT_ID, SECRET),  # Basic Auth с ID и секретом
            ssl=False                           # отключение SSL-проверки
        ) as resp:
            if resp.status == 200:
                json_data = await resp.json()
                return json_data.get("access_token")
            else:
                text = await resp.text()
                raise Exception(f"Ошибка получения токена: {resp.status} — {text}")

 

# === Загрузка файла в GigaChat ===
async def upload_file_to_gigachat(file_path: Path, access_token: str) -> str:
    """
    Загружает файл в GigaChat и возвращает file_id.
    """
    url = "https://gigachat.devices.sberbank.ru/api/v1/files"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    data = aiohttp.FormData()
    data.add_field("file", file_bytes, filename=file_path.name, content_type="application/pdf")
    data.add_field("purpose", "general")

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=data, ssl=False) as resp:
            if resp.status == 200:
                json_data = await resp.json()
                return json_data.get("id")
            else:
                text = await resp.text()
                raise Exception(f"Ошибка загрузки файла в GigaChat: {resp.status} — {text}")




# === Отправка промпта в GigaChat и получение ответа ===
async def send_prompt(prompt: str, access_token: str, attachment_ids: list[str] = None) -> dict:
    headers = {
        "Authorization": f"Bearer {access_token}",       # Авторизация через токен
        "Content-Type": "application/json",              # Отправка JSON
        "Accept": "application/json"
    }
    data = {
        "model": MODEL,                                  # Используемая модель
        "messages": [                                    # Сообщения чата
            {"role": "user", "content": prompt}
        ],
        "temperature": 1,                                # Творчество модели
        "top_p": 0.9,
        "n": 1,
        "stream": False                                  # Без потоковой передачи
    }

    # Добавим PDF
    if attachment_ids:
        data["attachments"] = attachment_ids

    # Отправляем POST-запрос
    async with aiohttp.ClientSession() as session:
        async with session.post(
            GIGACHAT_API_URL,
            headers=headers,
            json=data,
            ssl=False                                    # отключение SSL-проверки
        ) as resp:
            if resp.status == 200:
                json_data = await resp.json()

                # Возвращаем как текст ответа, так и usage с токенами
                return {
                    "content": json_data["choices"][0]["message"]["content"],
                    "usage": json_data.get("usage", {})  # {'prompt_tokens': X, 'completion_tokens': Y, ...}
                }
            else:
                text = await resp.text()
                raise Exception(f"Ошибка при запросе: {resp.status} — {text}")