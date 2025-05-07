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
git clone #https://github.com/your_username/your_project.git
cd #your_project
python3 -m venv ven
venv\Scripts\activate
pip install -r requirements.txt
python bot.py
Ctrl + C   # остановить бота
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