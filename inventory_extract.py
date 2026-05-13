# inventory_extract.py
"""
Парсер банковских выписок формата 1CClientBankExchange (TXT ANSI/CP1251 или UTF-8).
Извлекает дневные сводки: дата, начальный остаток, приход, расход, конечный остаток.
Также обрабатывает транзакции по бенефициарам.
Формирует analysis_summary.md и CSV-файлы для дальнейшего анализа.
"""

import pathlib
import re
import pandas as pd

BASE_DIR = pathlib.Path(r"c:/Users/Zalina/Downloads/общая папка для антигравити и вс код/проект конечная кастомная платформа")
ANALYSIS_DIR = BASE_DIR / "ведомости для анализа База"
OUTPUT_MD = BASE_DIR / "analysis_summary.md"
ATTACH = BASE_DIR / "attachments"
ATTACH.mkdir(exist_ok=True)

summary_lines = [
    "# 📊 Аналитический обзор банковских выписок (1CClientBankExchange)",
    "",
    f"Папка: `{ANALYSIS_DIR}`",
    "",
]

def try_read(path):
    """Читает файл, пробуя CP1251, затем UTF-8."""
    for enc in ("cp1251", "utf-8", "utf-8-sig"):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            continue
    return path.read_text(encoding="cp1251", errors="replace")

def parse_1c_statement(content):
    """
    Парсит текст формата 1CClientBankExchange.
    Возвращает:
      - meta: dict с общими данными (счёт, период и т.д.)
      - daily: list of dict (дневные сводки)
      - transactions: list of dict (транзакции по бенефициарам, если есть)
    """
    meta = {}
    daily = []
    transactions = []

    # Разбиваем на секции
    sections = re.split(r"КонецРаздела\r?\n", content)

    for sec in sections:
        lines = sec.strip().splitlines()
        block = {}
        for line in lines:
            if "=" in line:
                key, _, val = line.partition("=")
                block[key.strip()] = val.strip()

        if not block:
            continue

        sec_type = block.get("СекцияРасчСчет", "")
        if sec_type or "РасчСчет" in block:
            if "НачальныйОстаток" in block:
                daily.append({
                    "Дата":              block.get("ДатаНачала", block.get("ДатаКон", "")),
                    "Счёт":              block.get("РасчСчет", ""),
                    "НачальныйОстаток":  block.get("НачальныйОстаток", ""),
                    "ВсегоПоступило":    block.get("ВсегоПоступило", block.get("Приход", "")),
                    "ВсегоСписано":      block.get("ВсегоСписано", block.get("Расход", "")),
                    "КонечныйОстаток":   block.get("КонечныйОстаток", ""),
                })

        # Транзакции по бенефициарам
        if "Плательщик" in block or "Получатель" in block or "НазначениеПлатежа" in block:
            transactions.append({
                "Дата":              block.get("Дата", ""),
                "Сумма":             block.get("Сумма", ""),
                "Вид":               block.get("ВидДокумента", ""),
                "Плательщик":        block.get("Плательщик", ""),
                "СчётПлательщика":   block.get("ПлательщикСчет", ""),
                "Получатель":        block.get("Получатель", ""),
                "СчётПолучателя":    block.get("ПолучательСчет", ""),
                "Назначение":        block.get("НазначениеПлатежа", ""),
            })

        # Заголовок файла
        if "РасчСчет" in block and "ДатаНачала" in block and not meta:
            meta = {
                "Счёт":    block.get("РасчСчет", ""),
                "С":       block.get("ДатаНачала", ""),
                "По":      block.get("ДатаКон", ""),
            }

    return meta, daily, transactions


txt_files = sorted(ANALYSIS_DIR.glob("*.txt"))
if not txt_files:
    summary_lines.append("*Текстовые выписки не найдены.*")
else:
    for txt_path in txt_files:
        summary_lines.append(f"## 📁 {txt_path.name}")
        summary_lines.append("")
        try:
            content = try_read(txt_path)
            meta, daily, transactions = parse_1c_statement(content)

            # Метаданные
            if meta:
                summary_lines.append(f"**Счёт:** `{meta.get('Счёт','')}`  |  "
                                     f"**Период:** {meta.get('С','')} — {meta.get('По','')}")
                summary_lines.append("")

            # Дневные сводки
            if daily:
                df_daily = pd.DataFrame(daily)
                # Сохраняем CSV
                csv_name = f"{txt_path.stem}_daily.csv"
                df_daily.to_csv(ATTACH / csv_name, index=False, encoding="utf-8-sig")
                summary_lines.append("### 📅 Дневные сводки")
                summary_lines.append("")
                summary_lines.append(df_daily.to_markdown(index=False))
                summary_lines.append("")
                summary_lines.append(f"[Скачать CSV](attachments/{csv_name})")
                summary_lines.append("")
            else:
                summary_lines.append("*Дневные сводки не найдены в файле.*")
                summary_lines.append("")

            # Транзакции по бенефициарам
            if transactions:
                df_tx = pd.DataFrame(transactions)
                csv_name_tx = f"{txt_path.stem}_transactions.csv"
                df_tx.to_csv(ATTACH / csv_name_tx, index=False, encoding="utf-8-sig")
                summary_lines.append("### 💳 Транзакции по бенефициарам")
                summary_lines.append("")
                summary_lines.append(df_tx.head(10).to_markdown(index=False))
                summary_lines.append(f"\n*Всего транзакций: {len(df_tx)}*")
                summary_lines.append("")
                summary_lines.append(f"[Скачать CSV](attachments/{csv_name_tx})")
                summary_lines.append("")
            else:
                summary_lines.append("*Детальные транзакции не найдены (нет полей Плательщик/Получатель). "
                                     "Файл содержит только дневные сводки.*")
                summary_lines.append("")

        except Exception as e:
            summary_lines.append(f"**Ошибка обработки:** {e}")
            summary_lines.append("")

        summary_lines.append("---")
        summary_lines.append("")

OUTPUT_MD.write_text("\n".join(summary_lines), encoding="utf-8")
print(f"Gotovo! Otchet sokhranen: {OUTPUT_MD}")
print(f"CSV-fayly: {ATTACH}")
