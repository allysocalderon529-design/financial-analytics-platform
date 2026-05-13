# sales_parser.py
"""
Утилиты для чтения и предобработки файлов платформы.
Содержит функции чтения txt‑файлов в DataFrame, очистки числовых столбцов и
автоматического определения числовых колонок.
"""

import pathlib
import re
import pandas as pd

BASE_DIR = pathlib.Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "ведомости для анализа База"


def read_txt(path: pathlib.Path) -> pd.DataFrame:
    """Читает txt‑файл (ANSI или UTF‑8) и возвращает DataFrame.
    Строки, начинающиеся с "*" считаются примечаниями и игнорируются.
    Разделитель – табуляция, но в случае отсутствия заменяем её на "|".
    """
    # Попытка чтения в нескольких кодировках
    for enc in ("cp1251", "utf-8", "utf-8-sig"):
        try:
            txt = path.read_text(encoding=enc, errors="replace")
            break
        except Exception:
            continue
    else:
        txt = path.read_text(encoding="cp1251", errors="replace")

    rows = [line for line in txt.splitlines() if line.strip() and not line.lstrip().startswith("*")]
    if not rows:
        return pd.DataFrame()
    header = rows[0].replace("\t", "|").split("|")
    data = []
    for line in rows[1:]:
        parts = line.replace("\t", "|").split("|")
        parts = [p.strip() for p in parts if p.strip()]
        # выравниваем количество столбцов
        if len(parts) < len(header):
            parts += [""] * (len(header) - len(parts))
        data.append(parts)
    df = pd.DataFrame(data, columns=header[:len(data[0])])
    return df


def clean_numeric(series: pd.Series) -> pd.Series:
    """Приводит строки с числами (например "1 234,56") к типу float.
    Убирает неразрывные пробелы, меняет запятую на точку и оставляет только
    цифры, точку и знак.
    """
    return (
        series.astype(str)
        .str.replace(" ", "")        # убираем неразрывные пробелы
        .str.replace(",", ".")
        .str.replace(r"[^0-9\.\-]", "", regex=True)
        .replace("", "0")
        .astype(float)
    )


def detect_numeric_columns(df: pd.DataFrame) -> list:
    """Определяет числовые колонки: пытаемся очистить и проверяем, что сумма != 0.
    Возвращает список названий колонок, которые удалось преобразовать в числа.
    """
    numeric_cols = []
    for col in df.columns:
        try:
            cleaned = clean_numeric(df[col])
            if cleaned.abs().sum() > 0:
                numeric_cols.append(col)
        except Exception:
            continue
    return numeric_cols
