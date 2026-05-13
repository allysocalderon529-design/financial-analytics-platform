import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH, чтобы модули импортировались
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

def test_imports():
    """Проверяем, что ключевые модули импортируются без ошибок."""
    try:
        import sales_parser
        import sales_dynamic_analysis
        import obsidian_importer
    except Exception as e:
        raise AssertionError(f"Импорт модуля завершился ошибкой: {e}")

def test_dummy():
    """Простейший заглушка‑тест, всегда проходит."""
    assert True
