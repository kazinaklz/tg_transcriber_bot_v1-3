import os
import uuid
import aiohttp
from aiohttp import BasicAuth
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Получаем значения из окружения
CLIENT_ID = os.getenv("CLIENT_ID")
SECRET = os.getenv("SECRET")

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

 

# === Отправка промпта в GigaChat и получение ответа ===
async def send_prompt(prompt: str, access_token: str) -> str:
    headers = {
        "Authorization": f"Bearer {access_token}",       # Авторизация через токен
        "Content-Type": "application/json",              # Отправка JSON
        "Accept": "application/json"
    }
    data = {
        "model": "GigaChat",                             # Используемая модель
        "messages": [                                    # Сообщения чата
            {"role": "user", "content": prompt}
        ],
        "temperature": 1,                                # Творчество модели
        "top_p": 0.9,
        "n": 1,
        "stream": False                                  # Без потоковой передачи
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            GIGACHAT_API_URL,
            headers=headers,
            json=data,
            ssl=False                                    # отключение SSL-проверки
        ) as resp:
            if resp.status == 200:
                json_data = await resp.json()
                return json_data["choices"][0]["message"]["content"]
            else:
                text = await resp.text()
                raise Exception(f"Ошибка при запросе: {resp.status} — {text}")