# obsidian_importer.py
"""
Утилита для импорта резюме аналитики из `analysis_summary.md`
в Obsidian‑vault.
Создаёт папку «Аналитика» (если её нет) и внутри — отдельные заметки
для каждого файла‑выписки. Каждая заметка получает заголовок H1 = имя исходного
TXT‑файла и включает весь текст раздела из `analysis_summary.md`.

Также копирует все вложения (CSV‑файлы) в подпапку `Вложения` внутри
папки «Аналитика», если они ещё не находятся там.

Запуск:
    python obsidian_importer.py
"""

import pathlib
import shutil
import re

# ------------------------------------------------------------
# Конфигурация путей (можно переопределить при необходимости)
# ------------------------------------------------------------
BASE_DIR = pathlib.Path(r"c:/Users/Zalina/Downloads/общая папка для антигравити и вс код/проект конечная кастомная платформа")
VAULT_DIR = pathlib.Path(r"c:/Users/Zalina/ObsidianVault/ProjectPlatform")
ANALYTICS_DIR = VAULT_DIR / "Аналитика"
ATTACHMENTS_SUBDIR = ANALYTICS_DIR / "Вложения"

# Файлы, генерируемые скриптом inventory_extract.py
ANALYSIS_MD = BASE_DIR / "analysis_summary.md"
SOURCE_ATTACH = BASE_DIR / "attachments"

# ------------------------------------------------------------
def ensure_dirs():
    """Создаёт необходимые каталоги в vault, если их ещё нет."""
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    ATTACHMENTS_SUBDIR.mkdir(parents=True, exist_ok=True)

def copy_attachments():
    """Копирует все файлы из `attachments` в подпапку `Вложения` в vault."""
    if not SOURCE_ATTACH.exists():
        print(f"[WARN] Папка вложений не найдена: {SOURCE_ATTACH}")
        return
    for item in SOURCE_ATTACH.iterdir():
        if item.is_file():
            dest = ATTACHMENTS_SUBDIR / item.name
            if not dest.exists():
                shutil.copy2(item, dest)
                print(f"[OK] Копировано вложение: {item.name}")

def parse_analysis_md() -> dict:
    """Разбивает `analysis_summary.md` на секции по каждому файлу.
    Возвращает словарь: {filename: markdown_section_text}.
    """
    if not ANALYSIS_MD.exists():
        raise FileNotFoundError(f"analysis_summary.md не найден: {ANALYSIS_MD}")
    content = ANALYSIS_MD.read_text(encoding="utf-8")
    sections = {}
    current_file = None
    buffer = []
    for line in content.splitlines():
        header_match = re.match(r"^## 📁 (.+)", line)
        if header_match:
            if current_file:
                sections[current_file] = "\n".join(buffer).strip()
            current_file = header_match.group(1).strip()
            buffer = []
        else:
            buffer.append(line)
    if current_file:
        sections[current_file] = "\n".join(buffer).strip()
    return sections

def write_notes(sections: dict):
    """Создаёт markdown‑заметки в папке «Аналитика».
    Каждый файл‑выписка получает отдельную заметку с H1‑заголовком.
    """
    for filename, body in sections.items():
        note_name = pathlib.Path(filename).stem + ".md"
        note_path = ANALYTICS_DIR / note_name
        md_content = f"# {pathlib.Path(filename).name}\n\n{body}\n"
        note_path.write_text(md_content, encoding="utf-8")
        print(f"[OK] Заметка создана: {note_path.relative_to(VAULT_DIR)}")

def main():
    ensure_dirs()
    copy_attachments()
    sections = parse_analysis_md()
    write_notes(sections)
    print("[DONE] Импорт завершён.")

if __name__ == "__main__":
    main()
