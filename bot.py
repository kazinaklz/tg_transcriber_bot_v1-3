import os
import tempfile
import asyncio
import aiohttp
import time
import logging
import re

from pathlib import Path
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.enums import ParseMode, ContentType
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from html import escape
from dotenv import load_dotenv

from auth import check_user_registered, register_user, log_action
from audio_utils import handle_audio_file, split_audio, create_transcript_pdf, create_transcript_txt 
from salute_speech_api import transcribe_audio
from gigachat_api import get_access_token, send_prompt, upload_file_to_gigachat 



# === Настройка окружения и бота ===
load_dotenv()
bot = Bot(
    token=os.getenv("TG_BOT_TOKEN"),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# === Настройка логирования ===
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO))


# === Хранилище последних расшифровок пользователей ===
last_transcriptions = {}

# === Стандартный системный промпт ===
SYSTEM_PROMPT = (
    "Во вложенном .txt-файле содержится транскрипция совещания. Используй именно этот файл как основной источник информации для анализа.\n\n"
    "На его основе составь структурированный отчёт в строго деловом или нейтральном стиле. Отчёт должен включать:\n\n"
    "1. Тема совещания — кратко определи основную тему обсуждения.\n\n"
    "2. Основные итоги — изложи ключевые пункты повестки дня и важные выводы, сделанные участниками.\n\n"
    "3. Договорённости — перечисли достигнутые соглашения, конкретные поручения с указанием ответственных и сроков выполнения.\n\n"
    "4. Оценка совещания — дай объективную оценку подготовки, хода и результатов совещания.\n\n"
    "5. Резюме — подведи общий итог.\n\n"
    "Допускается использование прямых цитат участников для подтверждения ключевых выводов. Отчёт должен быть средней длины — достаточно подробным, но без избыточной информации. Оформление — в виде структурированного текста или списка."
)



# === Преобразование Markdown → HTML (только жирный и курсив) ===
def markdown_to_html(text: str) -> str:
    # жирный **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # курсив *text*
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    return text



# === Клавиатура с кнопкой старта ===
start_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/start")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True  # клавиатура скроется после нажатия
)



# === Декоратор для логирования времени выполнения ===
# фабрика декораторов
def log_timing(name: str):
    # декоратор
    def decorator(func):
        # сама функция - выполняется для каждой асинхронной функции, обернутой в декоратор
        async def wrapper(*args, **kwargs):
            # Засекаем время начала выполнения
            start = time.time()
            # Выполняем асинхронную функцию и получаем результат
            result = await func(*args, **kwargs)
            # Вычисляем, сколько времени заняло выполнение
            elapsed = time.time() - start
            # Логируем в консоль
            logging.info(f"[⏱] {name} заняло {elapsed:.2f} сек.")

            # Если передан message и username, логируем в Airtable
            for arg in args:
                if isinstance(arg, Message):
                    user_id = arg.from_user.id
                    username = arg.from_user.username

                    asyncio.create_task(log_action(user_id, username, f"{name} заняло {elapsed:.2f} сек."))
                    break

            return result
        return wrapper
    return decorator



# === Скачивание файла из Telegram ===
@log_timing("Скачивание файла с Telegram") # -- Консольный вывод времени выполнения
async def download_telegram_file(file_id: str, temp_paths: list[str]) -> str:
    # Получаем информацию о файле по его ID через Telegram API
    try:
        # Получаем информацию о файле
        file_info = await bot.get_file(file_id)
        print(f"[DEBUG] file_id: {file_id}")
        print(f"[DEBUG] file_path: {file_info.file_path}")
        print(f"[DEBUG] file_size: {file_info.file_size}")
        print(f"[DEBUG] file_info: {file_info}")

    except Exception as e:
        # Telegram не дал скачать файл — возможно, он слишком большой
        raise Exception(f"❌ Ошибка при получении файла из Telegram: {e}")



    # Формируем прямую ссылку для скачивания файла
    file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"

    # Создаем временный файл заранее, чтобы сохранить в него содержимое
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_paths.append(temp_file.name)

    # Асинхронно загружаем файл
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as response:
            if response.status == 200:
                # Считываем контент и записываем во временный файл
                content = await response.read()
                temp_file.write(content)
            else:
                raise Exception(f"Ошибка загрузки файла: {response.status}")

    temp_file.close()
    return temp_file.name  # Возвращаем путь к временному файлу



# === Разбивает длинный текст на части ===
def split_text(text: str, max_length: int = 4096) -> list[str]:
    """
    Разбивает длинный текст на части длиной не более max_length символов.

    По возможности старается делить текст по логическим границам: абзацы, 
    предложения, запятые, тире. Это делает результат читаемым и 
    пригодным для отправки в мессенджеры или API с ограничениями.
    """
    chunks = []
    while len(text) > max_length:
        # Пытаемся найти наилучшую точку разрыва
        for sep in ["\n", ". ", ", ", " — ", " – ", " - "]:
            split_at = text.rfind(sep, 0, max_length)
            if split_at != -1:
                split_at += len(sep)  # включаем разделитель в кусок
                break
        else:
            # Если ни один разделитель не найден — жёсткое разбиение
            split_at = max_length

        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()

    # Добавляем остаток
    if text:
        chunks.append(text)
    return chunks



# === Обработка и транскрипция аудиофайла ===
@log_timing("Распознавание аудио") # -- Консольный и Airtable вывод времени выполнения
async def process_audio_file(file_path: str, message: Message) -> str:
    # Обрабатываем аудиофайл
    processed_path = handle_audio_file(file_path)
    # Разбиваем обработанный файл на части
    parts = split_audio(processed_path)
    
    # Инициализируем строку для финального текста
    transcript = ""
    # Уведомляем пользователя о начале распознавания
    await message.answer(f"🎧 Распознаю речь ({len(parts)} фрагментов)...")

    # Отправляем одно сообщение, которое будем обновлять в процессе
    status_msg = await message.answer("▶️ Обработка части 1...")

    for idx, part_path in enumerate(parts):
        # Обновляем текст в одном сообщении, вместо спама
        await status_msg.edit_text(f"▶️ Обработка части {idx + 1} из {len(parts)}...")

        try:
            part_text = await transcribe_audio(part_path)
            transcript += part_text + "\n"
        except Exception as e:
            await message.answer(f"⚠️ Ошибка в части {idx + 1}. Распознавание остановлено.\n\n{e}")
            break
        finally:
            try:
                os.remove(part_path)
            except Exception:
                pass

        await asyncio.sleep(0.1)

    return transcript.strip()


# === Анализ текста с использованием GigaChat ===
@log_timing("Анализ текста через GigaChat") # -- Консольный и Airtable вывод времени выполнения
async def analyze_text(transcript: str, system_prompt: str, message: Message, date_str: Path) -> str:
    # Используем системный промпт, переданный пользователем
    prompt = f"{system_prompt.strip()}"
    token = await get_access_token()
    # Создаём TXT-файл
    txt_path = create_transcript_txt(transcript, date_str)
    
    # Загружаем файл в GigaChat
    file_id = await upload_file_to_gigachat(txt_path, token)

    # Отправляем промпт и получаем ответ вместе с информацией об использовании токенов
    response = await send_prompt(prompt, token, attachment_ids=[file_id])

    result_text = response["content"]
    usage = response.get("usage", {})

    # Извлекаем количество использованных токенов
    used_prompt = usage.get("prompt_tokens", "?")
    used_completion = usage.get("completion_tokens", "?")
    total = usage.get("total_tokens", "?")

    # Лог в консоль
    logging.info(f"Токены: prompt = {used_prompt}, completion = {used_completion}, total = {total}")

    # Лог в Airtable
    user_id = message.from_user.id
    username = message.from_user.username
    await log_action(
        user_id, 
        username, 
        f"[📊] Токены: prompt = {used_prompt}, completion = {used_completion}, total = {total}"
        )

    # Возвращаем только содержимое ответа от GigaChat
    return result_text



# === Команда /start ===
@router.message(Command("start"))
async def cmd_start(message: Message):
    # Извлекаем ID и username пользователя Telegram
    user_id = message.from_user.id
    username = message.from_user.username

    # Проверяем, зарегистрирован ли пользователь в системе
    user = await check_user_registered(user_id)
    if user:
        await message.answer(
            f"Здравствуйте, <b>{user.get('ИО', ['Пользователь'])[0]}</b>! Вы авторизованы.",
            reply_markup=start_keyboard
        )
        await message.answer("📤 Отправьте аудиофайл для расшифровки.")
    else:
        await register_user(user_id, username)
        await message.answer("Вы зарегистрированы. Обратитесь к администратору для авторизации.")
    # Логируем запуск команды
    await log_action(user_id, username, "/start")



# === Обработка входящих аудиофайлов ===
@router.message(F.content_type.in_({"voice", "audio", "document"}))
async def handle_audio(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    await log_action(user_id, username, "Загрузка аудио")

    file = message.voice or message.audio or message.document
    temp_paths = []     # Храним пути к временным файлам для последующего удаления
    
    try:
        await message.answer("📥 Загружаю аудиофайл...")
        # Скачиваем файл с Telegram-серверов
        downloaded_path = await download_telegram_file(file.file_id, temp_paths)
        # Добавляем путь к временному файлу для последующей очистки
        temp_paths.append(downloaded_path)

        await message.answer("🛠 Обрабатываю аудио...")
        # Транскрибируем аудиофайл и получаем расшифровку
        transcript = await process_audio_file(downloaded_path, message)
        if not transcript:
            await message.answer("❌ Не удалось распознать речь.")
            return
        
        # Генерация PDF-файла с расшифровкой
        # Текущая дата в формате ДДММГГГГ
        date_str = datetime.now().strftime("%d%m%Y")
        # Сохраняем дату расшифровки для анализа
        last_transcriptions[f"{user_id}_date"] = date_str

        # Создаём PDF-файл и txt-файл с расшифровкой
        pdf_path = create_transcript_pdf(transcript, date_str)
        txt_path = create_transcript_txt(transcript, date_str)


        # Отправляем файлы с расшифровкой пользователю
        await message.answer_document(types.FSInputFile(str(pdf_path)))
        await message.answer_document(types.FSInputFile(str(txt_path)))

        # Сохраняем текст расшифровки
        last_transcriptions[user_id] = transcript

        # Отправляем промпт для анализа и кнопки выбора--------------------
        await message.answer(
            f"🧠 Вот стандартный промпт для анализа расшифровки:\n\n{escape(SYSTEM_PROMPT)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Использовать стандартный", callback_data="use_system_prompt")],
                [InlineKeyboardButton(text="✍️ Ввести свой", callback_data="custom_prompt")]
            ])
        )

    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}")
        await log_action(user_id, username, f"Ошибка: {e}")
    finally:
        # Удаляем все временные файлы
        for path in temp_paths:
            try:
                os.remove(path)
            except Exception:
                pass



# === Выбрали это: Обработка системного промпта ===
@router.callback_query(F.data == "use_system_prompt")
async def handle_system_prompt_choice(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username
    
    # Получаем последнюю расшифровку
    transcript = last_transcriptions.get(user_id)
    if not transcript:
        await callback.message.answer("❗ Нет текста для анализа. Отправьте аудио.")
        return
    # Удаляем inline-клавиатуру под предыдущим сообщением
    await callback.message.edit_reply_markup()
    await callback.message.answer("📨 Отправляю в GigaChat...")
    try:
        # Отправляем транскрипт и системный промпт на анализ
        date_str = last_transcriptions.get(f"{user_id}_date")  # получаем дату из кэша
        result = await analyze_text(transcript, SYSTEM_PROMPT, callback.message, date_str) # передаём её в анализ
        await callback.message.answer("📋 Результат анализа:")
        for chunk in split_text(markdown_to_html(result)):
            await callback.message.answer(chunk)
        await log_action(user_id, username, "Анализ по системному промпту")
    except Exception as e:
        await callback.message.answer(f"⚠️ Ошибка: {e}")



# === Или это: Пользователь выбирает ввод собственного промпта ===
@router.callback_query(F.data == "custom_prompt")
async def handle_custom_prompt_choice(callback: CallbackQuery):
    user_id = callback.from_user.id

    # Достаём последнюю транскрипцию для пользователя
    transcript = last_transcriptions.get(user_id)
    if not transcript:
        await callback.message.answer("❗ Нет текста для анализа. Отправьте аудио.")
        return
    # Удаляем inline-клавиатуру из сообщения
    await callback.message.edit_reply_markup()
    await callback.message.answer("✍️ Введите ваш промпт:")



# === Прицепляем творчество пользователя: Обработка пользовательского промпта ===
@router.message(F.text)
async def receive_custom_prompt(msg: Message):
    user_id = msg.from_user.id
    username = msg.from_user.username

    # Проверяем, есть ли последняя транскрипция для пользователя
    if user_id not in last_transcriptions:
        return
    # Получаем текст промпта от пользователя и отправляем его на анализ
    prompt = msg.text
    await msg.answer("📨 Отправляю в GigaChat...")
    try:
        transcript = last_transcriptions[user_id]
        
        date_str = last_transcriptions.get(f"{user_id}_date")  # получаем дату из кэша
        result = await analyze_text(transcript, prompt, msg, date_str)  # передаём её в анализ

        await msg.answer("📋 Результат анализа:")
        for chunk in split_text(markdown_to_html(result)):
            await msg.answer(chunk)
        await log_action(user_id, username, f"Custom prompt: {prompt}")
    except Exception as e:
        await msg.answer(f"⚠️ Ошибка: {e}")




# === Точка входа ===
async def main():
    print("✅ Бот запущен")
     # Удаляем вебхук и очищаем очередь необработанных обновлений
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
