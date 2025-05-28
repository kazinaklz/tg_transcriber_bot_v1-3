import os
import tempfile
import subprocess
from pathlib import Path
from pydub import AudioSegment

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from pathlib import Path
import tempfile


SUPPORTED_FORMATS = ['.mp3', '.flac', '.ogg', '.wav']
NEED_CONVERT_FORMATS = ['.mp4', '.m4a']   # Конвертировать в mp3 (ffmpeg)

# === Проверка на соответствие 16 кГц и 1 каналу ===
def is_valid_for_salute(audio: AudioSegment) -> bool:
    return audio.frame_rate == 16000 and audio.channels == 1



# === Конвертация в MP3 (16 кГц, моно) через ffmpeg === 
def convert_to_mp3(input_file_path: Path | str) -> Path:
    input_path = Path(input_file_path)
    output_path = input_path.with_suffix('.converted.mp3')

    subprocess.run([
        'ffmpeg', '-y',
        '-i', str(input_path),
        '-vn', '-ac', '1', '-ar', '16000',
        '-f', 'mp3', str(output_path)
    ], check=True)

    return output_path



# === Обработка загруженного аудио ===
def handle_audio_file(file_path: str) -> Path:
    suffix = Path(file_path).suffix.lower()  # Получаем расширение файла

    if suffix in SUPPORTED_FORMATS:
        return Path(file_path)
    elif suffix in NEED_CONVERT_FORMATS:
        return convert_to_mp3(file_path)
    else:
        raise ValueError(f"Формат {suffix} не поддерживается.")



# === Разделение аудиофайла на части по 60 секунд ===
def split_audio(file_path: Path, chunk_ms: int = 58000) -> list[Path]:
    """
    Делит аудиофайл на фрагменты не длиннее 58 секунд (58000 мс).
    Все части экспортируются в mp3.
    Возвращает список путей к фрагментам.
    """
    audio = AudioSegment.from_file(file_path)
    output_paths = []

    total_length = len(audio)

    for i in range(0, total_length, chunk_ms):
        chunk = audio[i:i + chunk_ms]

        # Страхуемся: даже если по какой-то причине кусок оказался длиннее — обрезаем
        if len(chunk) > chunk_ms:
            chunk = chunk[:chunk_ms]

        chunk_path = file_path.with_name(f"{file_path.stem}_part{i // chunk_ms}.mp3")
        chunk.export(chunk_path, format="mp3")
        output_paths.append(chunk_path)

    return output_paths



# === Регистрация шрифта с поддержкой кириллицы ===
font_path = os.path.join("fonts", "DejaVuSans.ttf")
pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))

# === Генерация PDF-файла из текста транскрипции ===
def create_transcript_pdf(text: str, date_str: str) -> Path:
    """
    Создаёт PDF-файл с текстом транскрипта.

    :param text: Расшифрованный текст совещания.
    :param date_str: Дата в формате 'ДДММГГГГ' для включения в имя файла.
    :return: Путь к созданному PDF-файлу.
    """
    filename = f"Совещание_расшифровка_{date_str}.pdf"
    # Используем временную директорию
    path = Path(tempfile.gettempdir()) / filename

    # Настройки страницы и форматирования
    page_width, page_height = A4                   # размеры страницы A4
    margin_x = 15 * mm                             # отступы слева и справа
    margin_y = 15 * mm                             # отступы сверху и снизу
    usable_width = page_width - 2 * margin_x       # ширина, доступная для текста
    usable_height = page_height - 2 * margin_y     # высота, доступная для текста
    line_height = 12                               # высота строки в пикселях

    # Создаём PDF-объект и задаём шрифт
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("DejaVuSans", 12)

    # Начальные координаты (левый верхний угол, с учётом отступов)
    x = margin_x
    y = page_height - margin_y  # старт сверху

    # Разбивка текста по строкам и страницам
    for paragraph in text.split("\n"):               # разбиваем на абзацы
        words = paragraph.split(" ")                 # разбиваем абзац на слова
        line = ""                                    # буфер текущей строки
        for word in words:
            test_line = line + word + " "
            # Проверяем, помещается ли строка в доступную ширину
            if pdfmetrics.stringWidth(test_line, "DejaVuSans", 12) < usable_width:
                line = test_line
            else:
                # Если строка не помещается, печатаем текущую строку
                if y - line_height < margin_y:
                    c.showPage()                     # создаём новую страницу
                    c.setFont("DejaVuSans", 12)
                    y = page_height - margin_y
                c.drawString(x, y, line)
                y -= line_height
                line = word + " "

        # Печатаем последнюю строку в абзаце
        if line:
            if y - line_height < margin_y:
                c.showPage()
                c.setFont("DejaVuSans", 12)
                y = page_height - margin_y
            c.drawString(x, y, line)
            y -= line_height

    c.save()
    return path