import os
import tempfile
import subprocess
from pathlib import Path
from pydub import AudioSegment

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
