# 📢 Telegram-бот для расшифровки и анализа аудио

Бот принимает аудиосообщения, расшифровывает их с помощью SaluteSpeech API и анализирует результат через GigaChat API.  
Подходит для обработки стенограмм совещаний, интервью, заметок и других голосовых данных.

---

## ⚙️ Функциональность

- ✅ Авторизация пользователей (Airtable)
- 🎤 Приём голосовых и аудиофайлов
- 🎧 Расшифровка через SaluteSpeech API
- 🤖 Анализ текста через GigaChat с выбором промпта
- 📋 Вывод структурированного результата пользователю
- ⏱ Логирование времени обработки

---

## 🚀 Установка

```bash
git clone https://github.com/kazinaklz/tg_transcriber_bot_v1-3
cd tg_transcriber_bot_v1-3
python3 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python bot.py
Ctrl + C   # остановить бота
```
---

## ⚙️ Переменные окружения (.env)

Перед запуском необходимо создать файл `.env` в корне проекта и указать следующие значения:

```env
# === Telegram Bot ===
TG_BOT_TOKEN=ваш_токен_от_BotFather

# === GigaChat API ===
CLIENT_ID=ваш_client_id
SECRET=ваш_client_secret

# === SaluteSpeech API ===
SALUTE_AUTHORIZATION_KEY=ваш_ключ
SALUTE_CLIENT_ID=ваш_salute_client_id
SALUTE_SECRET=ваш_salute_secret

# === Airtable (авторизация пользователей) ===
AIRTABLE_API_TOKEN=токен_доступа
AIRTABLE_BASE_ID=идентификатор_базы
AIRTABLE_TABLE_MAIN=название_таблицы_основной
AIRTABLE_TABLE_LOG=название_таблицы_логов
```
---

## 🛠 Стек

- Python 3.10+
- aiogram 3.x
- aiohttp
- pydub + ffmpeg
- GigaChat API (Sber)
- SaluteSpeech API (Sber)
- Airtable API