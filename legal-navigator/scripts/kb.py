"""Загрузка базы НПА, словаря флагов и профилей проектов."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
KB_DIR = ROOT / "kb"
QUESTIONNAIRE = ROOT / "intake" / "questionnaire.md"

DOMAINS = {"invest-gov", "construction", "it-ai", "corporate"}
CATEGORIES = {"law", "permits", "support"}
REQUIRED_FIELDS = (
    "id", "kind", "number", "date", "title",
    "domains", "triggers", "base", "category", "verified",
)


def known_flags() -> set[str]:
    """Флаги берутся из таблицы анкеты — единственный источник словаря."""
    text = QUESTIONNAIRE.read_text(encoding="utf-8")
    return set(re.findall(r"^\| `([a-z0-9-]+)` \|", text, flags=re.M))


def load_acts(kb_dir: Path = KB_DIR) -> list[dict]:
    acts: list[dict] = []
    for path in sorted((kb_dir / "npa").glob("*.yaml")):
        for act in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
            act["_file"] = str(path.relative_to(kb_dir.parent))
            acts.append(act)
    return acts


def load_region(code: str | None, kb_dir: Path = KB_DIR) -> dict | None:
    if not code:
        return None
    matches = sorted((kb_dir / "regions").glob(f"{code}-*.yaml"))
    if not matches:
        return None
    return yaml.safe_load(matches[0].read_text(encoding="utf-8"))


def load_profile(path: Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
