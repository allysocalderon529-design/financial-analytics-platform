# sales_dynamic_analysis.py
"""
Главный скрипт, который собирает все файлы продаж, прибыли и складских партий,
выполняет агрегирование, расчёт KPI, формирует CSV/Markdown и отправляет результаты
по email. Также предоставляет простой "шлюз" (gateway) для добавления новых файлов
и подтверждения их обработки.
"""

import pathlib
import pandas as pd
import matplotlib.pyplot as plt
import smtplib
from email.message import EmailMessage
import json
import os

# ---------------------------------------------------------------------------
# Конфигурация и пути
# ---------------------------------------------------------------------------
BASE_DIR = pathlib.Path(r"c:/Users/Zalina/Downloads/общая папка для антигравити и вс код/проект конечная кастомная платформа")
DATA_DIR = BASE_DIR / "ведомости для анализа База"
ATTACH_DIR = BASE_DIR / "attachments"
ATTACH_DIR.mkdir(exist_ok=True)

# Импортируем утилиты из sales_parser.py
from sales_parser import read_txt, clean_numeric, detect_numeric_columns

# Параметры email (берём из knowledge "User Email & Contacts")
CONTACTS_PATH = pathlib.Path(r"C:/Users/Zalina/.gemini/antigravity/knowledge/user-contacts/artifacts/contacts.md")
# Файл contacts.md имеет простую структуру, возьмём email вручную
USER_EMAIL = "pfkbyf77@rambler.ru"
SMTP_HOST = "smtp.rambler.ru"
SMTP_PORT = 465
SMTP_PASSWORD = "pfkbyf77pfkbyf77"

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def parse_sales_file(path: pathlib.Path) -> pd.DataFrame:
    df = read_txt(path)
    numeric_cols = detect_numeric_columns(df)
    # Ожидаем, что среди numeric_cols есть "Количество" и "Сумма"
    quantity_col = next((c for c in numeric_cols if "Количество" in c), None)
    sum_col = next((c for c in numeric_cols if "Сумма" in c), None)
    if not quantity_col or not sum_col:
        raise ValueError(f"Не найдены колонка количества/суммы в {path.name}")
    df["Количество"] = clean_numeric(df[quantity_col])
    df["Сумма"] = clean_numeric(df[sum_col])
    # Дата в формате ДД.MM.YYYY или похожем
    if "Дата" in df.columns:
        df["Дата"] = pd.to_datetime(df["Дата"], dayfirst=True, errors="coerce")
    else:
        # Если нет отдельной даты, пытаемся взять из имени файла
        df["Дата"] = pd.NaT
    return df[["Дата", "Контрагент", "Количество", "Сумма"]]


def parse_profit_file(path: pathlib.Path) -> pd.DataFrame:
    df = read_txt(path)
    numeric_cols = detect_numeric_columns(df)
    profit_col = next((c for c in numeric_cols if "Приб" in c or "Прибыль" in c), None)
    if not profit_col:
        raise ValueError(f"Не найдена колонка прибыли в {path.name}")
    df["Прибыль"] = clean_numeric(df[profit_col])
    if "Дата" in df.columns:
        df["Дата"] = pd.to_datetime(df["Дата"], dayfirst=True, errors="coerce")
    else:
        df["Дата"] = pd.NaT
    return df[["Дата", "Прибыль"]]


def parse_stock_file(path: pathlib.Path) -> pd.DataFrame:
    df = read_txt(path)
    # Ожидаем колонки: Номенклатура, Количество, Стоимость (и аналогичные)
    # Приведём числовые колонки
    numeric_cols = detect_numeric_columns(df)
    for col in numeric_cols:
        df[col] = clean_numeric(df[col])
    return df


def aggregate_monthly(sales_df: pd.DataFrame, profit_df: pd.DataFrame) -> pd.DataFrame:
    # Приведём даты к первой календарной дате месяца
    sales_df = sales_df.dropna(subset=["Дата"]).copy()
    profit_df = profit_df.dropna(subset=["Дата"]).copy()
    sales_df["YearMonth"] = sales_df["Дата"].dt.to_period('M')
    profit_df["YearMonth"] = profit_df["Дата"].dt.to_period('M')
    sales_month = sales_df.groupby("YearMonth").agg({"Количество": "sum", "Сумма": "sum"}).reset_index()
    profit_month = profit_df.groupby("YearMonth").agg({"Прибыль": "sum"}).reset_index()
    merged = pd.merge(sales_month, profit_month, on="YearMonth", how="outer").fillna(0)
    merged["YearMonth"] = merged["YearMonth"].astype(str)
    return merged


def calculate_kpis(sales_df: pd.DataFrame, stock_df: pd.DataFrame, profit_df: pd.DataFrame):
    # Убыточные позиции (отрицательная маржа) И/ИЛИ продажи <=10 шт/мес
    # Для маржи нужно знать себестоимость – берём её из stock_df (Стоимость * Количество)
    # Предположим, что столбец "Стоимость" соответствует стоимости единицы
    if "Стоимость" in stock_df.columns and "Количество" in stock_df.columns:
        stock_df["Себестоимость"] = stock_df["Стоимость"] * stock_df["Количество"]
    else:
        stock_df["Себестоимость"] = 0
    # Сводка продаж по номенклатуре
    sales_by_item = sales_df.groupby("Контрагент").agg({"Сумма": "sum", "Количество": "sum"})
    # Маржа = Выручка - себестоимость (приведём к тем же позициям, если имена совпадают)
    # Здесь упрощаем: считаем общую маржу
    total_margin = sales_df["Сумма"].sum() - stock_df["Себестоимость"].sum()
    # Нерентабельные товары
    unprofitable = sales_by_item[(sales_by_item["Сумма"] < stock_df["Себестоимость"].sum()) | (sales_by_item["Количество"] <= 10)]
    # Низкоценные покупатели (доля <5%)
    total_sales = sales_df["Сумма"].sum()
    cust_sum = sales_df.groupby("Контрагент")["Сумма"].sum()
    low_value_customers = cust_sum[cust_sum / total_sales < 0.05]
    # Оборот склада (sales_qty / avg_stock_qty)
    if "Конечный остаток" in stock_df.columns:
        avg_stock = stock_df["Конечный остаток"].mean()
        turnover = sales_df["Количество"].sum() / avg_stock if avg_stock else 0
    else:
        turnover = 0
    # Среднее время поступления (lead time) – разница между первой датой прихода и первой продажей
    lead_time = None
    if not stock_df.empty and not sales_df.empty:
        first_stock = stock_df["Дата"].min() if "Дата" in stock_df.columns else None
        first_sale = sales_df["Дата"].min()
        if pd.notna(first_stock) and pd.notna(first_sale):
            lead_time = (first_sale - first_stock).days
    return {
        "total_margin": total_margin,
        "unprofitable_items": unprofitable,
        "low_value_customers": low_value_customers,
        "turnover": turnover,
        "lead_time_days": lead_time,
    }


def plot_trends(monthly_df: pd.DataFrame):
    plt.figure(figsize=(10,6))
    plt.plot(monthly_df["YearMonth"], monthly_df["Сумма"], marker='o', label='Продажи (RUB)')
    plt.plot(monthly_df["YearMonth"], monthly_df["Прибыль"], marker='x', label='Прибыль (RUB)')
    plt.xticks(rotation=45)
    plt.title('Динамика продаж и прибыли по месяцам')
    plt.xlabel('Месяц')
    plt.ylabel('RUB')
    plt.grid(True)
    plt.legend()
    trend_path = ATTACH_DIR / "sales_profit_trend.png"
    plt.tight_layout()
    plt.savefig(trend_path)
    plt.close()
    return trend_path


def generate_markdown(monthly_df: pd.DataFrame, kpis: dict, trend_path: pathlib.Path):
    md_lines = []
    md_lines.append("# 📊 Динамический аналитический отчет")
    md_lines.append("")
    md_lines.append("## 📈 Тренд продаж и прибыли")
    md_lines.append(f"![]({trend_path.name})")
    md_lines.append("")
    md_lines.append("## 📅 Сводка по месяцам")
    md_lines.append(monthly_df.to_markdown(index=False))
    md_lines.append("")
    md_lines.append("## 📊 Ключевые KPI")
    md_lines.append(f"**Общая маржа:** {kpis['total_margin']:.2f} RUB")
    md_lines.append(f"**Оборот склада:** {kpis['turnover']:.2f}")
    if kpis['lead_time_days'] is not None:
        md_lines.append(f"**Среднее время поставки:** {kpis['lead_time_days']} дней")
    md_lines.append("")
    md_lines.append("### 🚩 Нерентабельные позиции")
    if not kpis['unprofitable_items'].empty:
        md_lines.append(kpis['unprofitable_items'].to_markdown())
    else:
        md_lines.append("_Нет нерентабельных позиций_\n")
    md_lines.append("")
    md_lines.append("### 👥 Низкоценные покупатели (<5% от общей выручки)")
    if not kpis['low_value_customers'].empty:
        df_low = kpis['low_value_customers'].reset_index()
        df_low.columns = ["Контрагент", "Сумма"]
        md_lines.append(df_low.to_markdown(index=False))
    else:
        md_lines.append("_Все покупатели приносят более 5% выручки_\n")
    md_content = "\n".join(md_lines)
    md_path = ATTACH_DIR / "dynamic_report.md"
    md_path.write_text(md_content, encoding="utf-8")
    return md_path


def send_email_with_attachments(subject: str, body: str, files: list[pathlib.Path]):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = USER_EMAIL
    msg["To"] = USER_EMAIL
    msg.set_content(body)
    for f in files:
        with f.open('rb') as fp:
            data = fp.read()
            maintype, subtype = ('application', 'octet-stream')
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=f.name)
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(USER_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)

# ---------------------------------------------------------------------------
# Шлюз (gateway) – простые функции взаимодействия
# ---------------------------------------------------------------------------

def add_new_file(src_path: pathlib.Path):
    """Копирует новый файл в директорию DATA_DIR.
    Используется ботами или внешними системами.
    """
    dest = DATA_DIR / src_path.name
    dest.write_bytes(src_path.read_bytes())
    print(f"Файл {src_path.name} добавлен в очередь обработки.")

def mark_approved(file_name: str):
    """Удаляет исходный файл после подтверждения пользователем (кнопка «согласовано»)."""
    target = DATA_DIR / file_name
    if target.exists():
        target.unlink()
        print(f"Файл {file_name} удалён после согласования.")
    else:
        print(f"Файл {file_name} не найден.")

# ---------------------------------------------------------------------------
# Основная функция
# ---------------------------------------------------------------------------

def process_all():
    # Сбор файлов
    sales_files = list(DATA_DIR.glob("отчет продажи *.txt"))
    profit_files = list(DATA_DIR.glob("валовая прибыль *.txt"))
    stock_files = list(DATA_DIR.glob("партии товаров на складах *.txt"))

    # Чтение и объединение
    sales_frames = [parse_sales_file(p) for p in sales_files]
    profit_frames = [parse_profit_file(p) for p in profit_files]
    stock_frames = [parse_stock_file(p) for p in stock_files]

    sales_df = pd.concat(sales_frames, ignore_index=True) if sales_frames else pd.DataFrame()
    profit_df = pd.concat(profit_frames, ignore_index=True) if profit_frames else pd.DataFrame()
    stock_df = pd.concat(stock_frames, ignore_index=True) if stock_frames else pd.DataFrame()

    monthly_df = aggregate_monthly(sales_df, profit_df)
    kpis = calculate_kpis(sales_df, stock_df, profit_df)
    trend_path = plot_trends(monthly_df)
    md_path = generate_markdown(monthly_df, kpis, trend_path)

    # Сохраняем CSV‑версии
    monthly_df.to_csv(ATTACH_DIR / "monthly_summary.csv", index=False, encoding="utf-8-sig")
    # KPI‑таблицы
    if not kpis['unprofitable_items'].empty:
        kpis['unprofitable_items'].to_csv(ATTACH_DIR / "unprofitable_items.csv", encoding="utf-8-sig")
    if not kpis['low_value_customers'].empty:
        (kpis['low_value_customers']
         .reset_index()
         .to_csv(ATTACH_DIR / "low_value_customers.csv", index=False, encoding="utf-8-sig"))

    # Отправка email
    subject = "✅ Динамический аналитический отчёт готов"
    body = "Во вложении – полный аналитический отчёт и CSV‑данные."
    send_email_with_attachments(subject, body, [md_path, trend_path])
    print("Отчёт отправлен на почту и сохранён в attachments.")

if __name__ == "__main__":
    process_all()
