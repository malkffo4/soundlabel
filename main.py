import os
import sys
import re
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen import MutagenError

if len(sys.argv) < 2:
    print('Usage: python music_title.py /path/to/folder')
    sys.exit(1)

directory = os.path.abspath(os.path.expanduser(sys.argv[1]))

if not os.path.isdir(directory):
    print(f"Error: {directory} is not a directory")
    sys.exit(1)

def clean_name(text):
    """Очистка от номеров треков в начале (01, 01., 01 -)"""
    return re.sub(r'^\d+[\s._-]*', '', text).strip()

for root, dirs, files in os.walk(directory):
    for filename in files:
        if filename.lower().endswith(".mp3"):
            name_without_ext = os.path.splitext(filename)[0]
            
            # Пробуем разные варианты разделителей
            parts = []
            for sep in [" – ", " - ", " — "]:
                if sep in name_without_ext:
                    parts = name_without_ext.split(sep, 1)
                    break
            
            if len(parts) == 2:
                artist_from_file = clean_name(parts[0])
                title_from_file = parts[1].strip()
                path = os.path.join(root, filename)

                try:
                    try:
                        audio = EasyID3(path)
                    except Exception:
                        # Если ID3 тегов нет, создаем их принудительно
                        tags = ID3()
                        tags.save(path)
                        audio = EasyID3(path)
                    
                    # Проверяем, нужно ли обновление
                    curr_artist = audio.get('artist', [''])[0].strip()
                    curr_title = audio.get('title', [''])[0].strip()

                    changed = False

                    # Обновляем, если теги пустые или состоят только из цифр
                    if not curr_artist or curr_artist.isdigit():
                        audio['artist'] = artist_from_file
                        changed = True
                    
                    if not curr_title:
                        audio['title'] = title_from_file
                        changed = True

                    if changed:
                        # v2_version=3 — это ID3v2.3. Самый совместимый формат для кириллицы
                        # файловый менеджер GNOME его понимают
                        audio.save(v2_version=3)
                        print(f"Fixed: {filename}")
                    else:
                        # Если все ок, просто молча идем дальше (или выводим инфо)
                        pass

                except Exception as e:
                    print(f"Skip {filename}: {e}")
