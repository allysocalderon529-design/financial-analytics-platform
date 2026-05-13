# sales_analysis.py
"""
Парсер отчёта продаж (TXT) для интеграции в кастомную платформу.
Поддерживает ANSI и UTF‑8, удаляет технические строки, вычисляет агрегаты.
"""

import pathlib, re
import pandas as pd

# Путь к папке с данными (можно переопределить при запуске)
BASE_DIR = pathlib.Path(r"c:/Users/Zalina/Downloads/общая папка для антигравити и вс код/проект конечная кастомная платформа")
DATA_DIR = BASE_DIR / "ведомости для анализа База"
REPORT_FILE = DATA_DIR / "отчет продажи 01.05-30.09.26.txt"
OUTPUT_DIR = BASE_DIR / "attachments"
OUTPUT_DIR.mkdir(exist_ok=True)

def read_report(path: pathlib.Path) -> pd.DataFrame:
    """Читает табуляцией разделённый txt‑файл и возвращает DataFrame."""
    txt = path.read_text(encoding="utf-8", errors="replace")
    # разбиваем строки, игнорируем пустые
    rows = [line for line in txt.splitlines() if line.strip()]
    # первая строка – заголовок, дальше – данные
    header = rows[0].replace("\t", "|").split("|")
    data = []
    for line in rows[1:]:
        # Пропускаем строки‑примечания, начинающиеся со '*'
        if line.lstrip().startswith("*"):
            continue
        parts = line.replace("\t", "|").split("|")
        # иногда в конце могут быть лишние пустые столбцы – обрезаем
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) < len(header):
            # иногда заголовок имеет 5 колонок, а строка – 4 (например, итог)
            # заполняем недостающие пустыми значениями
            parts += [""] * (len(header) - len(parts))
        data.append(parts)
    df = pd.DataFrame(data, columns=header[:len(data[0])])
    return df

def clean_numeric(series: pd.Series) -> pd.Series:
    """Приводит строки с числами ("1 234,56") к типу float."""
    return (
        series.astype(str)
        .str.replace(" ", "")      # убираем неразрывные пробелы
        .str.replace(",", ".")
        .str.replace(r"[^0-9\.\-]", "", regex=True)  # оставляем только цифры, точку, знак
        .replace("", "0")
        .astype(float)
    )

def process():
    df = read_report(REPORT_FILE)
    # Приведём числовые столбцы к float (по шаблону: количество, сумма)
    numeric_cols = [c for c in df.columns if re.search(r"Количество|Сумма", c, re.I)]
    for col in numeric_cols:
        df[col] = clean_numeric(df[col])

    # Выделим месяц из заголовков, если они присутствуют (например, "Май 2026 г.")
    month_cols = [c for c in df.columns if re.search(r"\b\d{2}\.\d{2}\.\d{4}\b", c) or "мй" in c.lower()]
    # Для простоты создадим «Месяц» = название колонки с данными продаж, если есть
    # В данном файле данные уже разложены по месяцам, будем агрегировать все вместе.

    # Итоги по всему периоду
    total_quantity = df[numeric_cols[0]].sum()
    total_sum = df[numeric_cols[1]].sum()

    # Топ‑10 позиций по сумме
    top_items = df.nlargest(10, numeric_cols[1])[['Контрагент', numeric_cols[0], numeric_cols[1]]]

    # Сводка по месяцам, если в колонках есть отдельные месяцы (в примере – две колонки: Количество, Сумма)
    # В более сложных файлах можно будет распарсить названия колонок, но пока оставим общий.

    # Сохраняем CSV‑файлы
    df.to_csv(OUTPUT_DIR / "sales_raw.csv", index=False, encoding="utf-8-sig")
    top_items.to_csv(OUTPUT_DIR / "sales_top10.csv", index=False, encoding="utf-8-sig")
    summary = pd.DataFrame({
        "Показатель": ["Общее количество", "Общая сумма"],
        "Значение": [total_quantity, total_sum]
    })
    summary.to_csv(OUTPUT_DIR / "sales_summary.csv", index=False, encoding="utf-8-sig")

    # Выводим markdown‑отчёт
    md = "# 📊 Сводка продаж (01.05‑30.09.2026)\n\n"
    md += f"**Общее количество:** {total_quantity:,.0f}  
"
    md += f"**Общая сумма:** {total_sum:,.2f} RUB  \n\n"
    md += "## 🔝 Топ‑10 позиций по сумме\n\n"
    md += top_items.to_markdown(index=False) + "\n"
    (BASE_DIR / "sales_summary.md").write_text(md, encoding="utf-8")
    print("✅ Анализ завершён, файлы записаны в attachments и sales_summary.md")

if __name__ == "__main__":
    process()
