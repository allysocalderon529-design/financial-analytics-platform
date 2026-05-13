# sales_analysis_v2.py
"""
Парсер отчёта продаж (TXT) и генерация отчётов для платформы.
Поддержка ANSI/UTF‑8, удаление строк‑примечаний, вычисление итогов, топ‑10 и markdown‑отчёта.
"""

import pathlib, re
import pandas as pd

BASE_DIR = pathlib.Path(r"c:/Users/Zalina/Downloads/общая папка для антигравити и вс код/проект конечная кастомная платформа")
DATA_DIR = BASE_DIR / "ведомости для анализа База"
REPORT_FILE = DATA_DIR / "отчет продажи 01.05-30.09.26.txt"
OUTPUT_DIR = BASE_DIR / "attachments"
OUTPUT_DIR.mkdir(exist_ok=True)

def read_report(path: pathlib.Path) -> pd.DataFrame:
    txt = path.read_text(encoding="utf-8", errors="replace")
    rows = [line for line in txt.splitlines() if line.strip()]
    header = rows[0].replace("\t", "|").split("|")
    data = []
    for line in rows[1:]:
        if line.lstrip().startswith("*"):
            continue
        parts = line.replace("\t", "|").split("|")
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) < len(header):
            parts += [""] * (len(header) - len(parts))
        data.append(parts)
    df = pd.DataFrame(data, columns=header[:len(data[0])])
    return df

def clean_numeric(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace(" ", "")
        .str.replace(",", ".")
        .str.replace(r"[^0-9\.\-]", "", regex=True)
        .replace("", "0")
        .astype(float)
    )

def process():
    df = read_report(REPORT_FILE)
    # Detect numeric columns by trying to clean each column and checking if conversion yields non‑zero values
    numeric_cols = []
    for col in df.columns:
        try:
            cleaned = clean_numeric(df[col])
            if cleaned.abs().sum() > 0:
                numeric_cols.append(col)
        except Exception:
            continue
    if len(numeric_cols) < 2:
        raise ValueError("Не удалось определить колонки количества и суммы в отчёте.")


    total_quantity = df[numeric_cols[0]].sum()
    total_sum = df[numeric_cols[1]].sum()

    top_items = df.nlargest(10, numeric_cols[1])[['Контрагент', numeric_cols[0], numeric_cols[1]]]

    # Save CSVs
    df.to_csv(OUTPUT_DIR / "sales_raw.csv", index=False, encoding="utf-8-sig")
    top_items.to_csv(OUTPUT_DIR / "sales_top10.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"Показатель": ["Общее количество", "Общая сумма"], "Значение": [total_quantity, total_sum]})\
        .to_csv(OUTPUT_DIR / "sales_summary.csv", index=False, encoding="utf-8-sig")

    # Markdown report
    md_lines = [
        "# 📊 Сводка продаж (01.05‑30.09.2026)",
        "",
        f"**Общее количество:** {total_quantity:,.0f}",
        f"**Общая сумма:** {total_sum:,.2f} RUB",
        "",
        "## 🔝 Топ‑10 позиций по сумме",
        "",
    ]
    md = "\n".join(md_lines)
    md += "\n" + top_items.to_markdown(index=False) + "\n"
    (BASE_DIR / "sales_summary.md").write_text(md, encoding="utf-8")
    print("✅ Анализ завершён, CSV и markdown созданы.")

if __name__ == "__main__":
    process()
