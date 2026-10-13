#!/usr/bin/env python3
"""Валидация базы НПА: схема, уникальность id, известные флаги/домены, свежесть сверки.

Код выхода 1 — ошибки схемы. Несверенные и устаревшие акты — предупреждения.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys

from kb import CATEGORIES, DOMAINS, REQUIRED_FIELDS, known_flags, load_acts

STALE_DAYS = 90


def validate(acts: list[dict], flags: set[str], today: dt.date) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for act in acts:
        where = f"{act.get('_file')}:{act.get('id', '?')}"
        missing = [f for f in REQUIRED_FIELDS if f not in act]
        if missing:
            errors.append(f"{where}: нет полей {missing}")
            continue
        if act["id"] in seen:
            errors.append(f"{where}: дубль id")
        seen.add(act["id"])
        if not isinstance(act["date"], dt.date):
            errors.append(f"{where}: date должен быть YYYY-MM-DD")
        if bad := set(act["domains"]) - DOMAINS:
            errors.append(f"{where}: неизвестные домены {sorted(bad)}")
        if bad := set(act["triggers"]) - flags:
            errors.append(f"{where}: флаги не из анкеты {sorted(bad)}")
        if act["category"] not in CATEGORIES:
            errors.append(f"{where}: category должен быть одним из {sorted(CATEGORIES)}")
        if not act["base"] and not act["triggers"]:
            errors.append(f"{where}: base=false и пустые triggers — акт никогда не подберётся")
        verified = act["verified"]
        if verified is None:
            warnings.append(f"{where}: редакция не сверялась")
        elif not isinstance(verified, dt.date):
            errors.append(f"{where}: verified должен быть YYYY-MM-DD или null")
        elif (today - verified).days > STALE_DAYS:
            warnings.append(f"{where}: сверка старше {STALE_DAYS} дн. ({verified})")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-q", "--quiet", action="store_true", help="не печатать предупреждения")
    args = parser.parse_args()

    acts = load_acts()
    errors, warnings = validate(acts, known_flags(), dt.date.today())
    for e in errors:
        print(f"ERROR   {e}")
    if not args.quiet:
        for w in warnings:
            print(f"WARN    {w}")
    print(f"актов: {len(acts)}, ошибок: {len(errors)}, предупреждений: {len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
