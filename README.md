# 📢 Telegram-бот для расшифровки и анализа аудио

Бот принимает аудиосообщения, расшифровывает их с помощью SaluteSpeech API и анализирует результат через GigaChat API.  
Подходит для обработки стенограмм совещаний, интервью, заметок и других голосовых данных.

---

## ⚙️ Функциональность

- ✅ **Авторизация пользователей** — через Airtable (ID и ФИО сверяются с таблицей).
- 🎙️ **Приём аудиофайлов** — поддерживаются `voice`, `audio`, `document`; форматы `.mp3`, `.wav`, `.ogg`, `.flac`, `.m4a`, `.mp4`.
- 🛠 **Автоматическая конвертация** — если формат требует (например, `.m4a`, `.mp4`), преобразуется в `.mp3` (16 кГц, моно) через `ffmpeg`.
- ✂️ **Разбиение аудио** — исходный файл делится на отрывки по 58 секунд.
- 🔊 **Распознавание речи** — каждый отрывок отправляется в `SaluteSpeech API` для транскрибации. Работает с файлами любой длительности.
- 📄 **Формирование файлов с транскрипцией**:
  - `.pdf` — создаётся и отправляется пользователю.
  - `.txt` — используется как вложение для анализа.
- 🧠 **Анализ текста через GigaChat API**:
  - Поддержка **системного промпта** (по умолчанию — отчёт по совещанию).
  - Возможность **ввода пользовательского промпта**.
  - Запрос отправляется с вложением `.txt` в GigaChat и возвращается результат.
- 📤 **Вывод результата** — ответ GigaChat разбивается и отправляется в Telegram.
- 📊 **Логирование** — фиксируются действия, токены, время обработки (в консоль и Airtable).
- 🧾 **Кэширование** — последние расшифровки и дата сохраняются для каждого пользователя.


---

## 🚀 Установка

```bash
git clone https://github.com/kazinaklz/tg_transcriber_bot_v1-3
cd tg_transcriber_bot_v1-3
python3 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python bot.py

Ctrl + C   
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

# === GIGACHAT MODEL ===
GIGACHAT_MODEL=GigaChat-Max

# === Управление уровнем логирования ===
LOG_LEVEL=INFO

```
---

## 🛠 Стек

- **Python 3.10+**
- **aiogram 3.x** — для Telegram-бота (bot.py).
- **aiohttp** — для асинхронных HTTP-запросов (auth.py, gigachat_api.py, salute_speech_api.py).
- **python-dotenv** — для загрузки переменных окружения (load_dotenv()).
- **pydub + ffmpeg** — для обработки аудио и разбиения на отрывки (audio_utils.py) и для конвертации аудио в .mp3 (через subprocess).
- **reportlab** — для генерации .pdf файлов (audio_utils.py).
- **GigaChat API (Sber)** — используется через aiohttp (gigachat_api.py).
- **SaluteSpeech API (Sber)** — используется через aiohttp (salute_speech_api.py).
- **Airtable API** — для авторизации и логирования пользователей (auth.py).

---