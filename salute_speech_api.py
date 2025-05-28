import os
import uuid
import base64
import aiohttp
from aiohttp import BasicAuth
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Переменные авторизации
SALUTE_CLIENT_ID = os.getenv("SALUTE_CLIENT_ID")
SALUTE_SECRET = os.getenv("SALUTE_SECRET")

# URL для токена и распознавания
SALUTE_TOKEN_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
SALUTE_RECOGNIZE_URL = "https://smartspeech.sber.ru/rest/v1/speech:recognize"



# === Получение токена доступа к Salute Speech API ===
async def get_salute_token():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",  # Формат тела запроса
        "Accept": "application/json",                         # Формат ответа
        "RqUID": str(uuid.uuid4())                            # Уникальный ID запроса
    }
    data = {
        "scope": "SALUTE_SPEECH_PERS"  # Область применения токена
    }

    # Отправка POST-запроса на получение токена
    async with aiohttp.ClientSession() as session:
        async with session.post(
            SALUTE_TOKEN_URL,
            headers=headers,
            data=data,
            auth=BasicAuth(SALUTE_CLIENT_ID, SALUTE_SECRET),
            ssl=False                          # отключаем проверку сертификата
        ) as resp:
            if resp.status == 200:
                json_data = await resp.json()
                return json_data.get("access_token")
            else:
                text = await resp.text()
                raise Exception(f"Ошибка получения токена: {resp.status} — {text}")



# === Распознавание аудио SaluteSpeech API: отправка raw-байтов ===
async def transcribe_audio(file_path: Path) -> str:
    access_token = await get_salute_token()

    # Определяем тип контента по расширению файла
    suffix = file_path.suffix.lower()
    if suffix == ".ogg":
        content_type = "audio/ogg"
    elif suffix in [".mp3", ".mpeg"]:
        content_type = "audio/mpeg"
    elif suffix in [".wav"]:
        content_type = "audio/wav"
    else:
        raise ValueError(f"Неподдерживаемый тип файла для Salute: {suffix}")

    print(f"Распознаю файл: {file_path.name}, тип: {content_type}")


    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": content_type
    }

    # Создаём асинхронную сессию для HTTP-запросов
    async with aiohttp.ClientSession() as session:
        # Открываем аудиофайл в бинарном режиме
        with open(file_path, "rb") as audio_file:
            async with session.post(
                SALUTE_RECOGNIZE_URL,  # URL сервиса распознавания
                headers=headers,       # Заголовки
                data=audio_file,       # Сырые байты аудиофайла
                ssl=False              # Отключаем проверку SSL
            ) as resp:
                if resp.status == 200:
                    result = await resp.json() 
                    raw_result = result.get("result", "")
                    if isinstance(raw_result, list):
                        return " ".join(raw_result)  # Склеиваем список в строку
                    return raw_result or ""
                else:
                    text = await resp.text()
                    raise Exception(f"Ошибка распознавания: {resp.status} — {text}")

