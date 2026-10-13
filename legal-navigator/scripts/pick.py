#!/usr/bin/env python3
"""Детерминированный подбор актов из базы по профилю проекта.

Правило: акт попадает в подбор, если
  - пересекается по флагам (triggers ∩ profile.flags), или
  - base=true и пересекается по доменам (domains ∩ profile.domains).
Это стартовый список для skill'а, а не исчерпывающий перечень.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from kb import known_flags, load_acts, load_profile, load_region

CATEGORY_TITLES = {
    "law": "Законодательство и чек-лист НПА",
    "permits": "Разрешения, согласования, лицензии",
    "support": "Меры поддержки и особые режимы",
}


def select(acts: list[dict], profile: dict) -> list[dict]:
    flags = set(profile.get("flags") or [])
    domains = set(profile.get("domains") or [])
    picked = []
    for act in acts:
        hit_flags = sorted(flags & set(act["triggers"]))
        hit_base = act["base"] and bool(domains & set(act["domains"]))
        if hit_flags or hit_base:
            picked.append({**act, "matched_by": hit_flags or ["base"]})
    return picked


def unknown_flags(profile: dict, flags: set[str]) -> list[str]:
    return sorted(set(profile.get("flags") or []) - flags)


def render_md(profile: dict, picked: list[dict], region: dict | None) -> str:
    lines = [f"# Подбор НПА: {profile.get('name', '—')}", ""]
    lines.append(f"**Вопрос:** {str(profile.get('question', '—')).strip()}")
    lines.append("")
    for cat, title in CATEGORY_TITLES.items():
        group = [a for a in picked if a["category"] == cat]
        if not group:
            continue
        lines += [f"## {title}", "", "| Акт | Почему | Сверено |", "|---|---|---|"]
        for a in group:
            name = f"{a['kind']} от {a['date']:%d.%m.%Y} № {a['number']} «{a['title']}»"
            verified = a["verified"] or "нет"
            lines.append(f"| {name} | {', '.join(a['matched_by'])} | {verified} |")
        lines.append("")
    if region:
        lines += [f"## Региональный слой: {region['name']}", ""]
        lines += [f"- {t}" for t in region.get("special_territories", [])]
        lines += ["", "Где искать:"] + [f"- {s}" for s in region.get("lookup", [])]
        lines.append("")
    elif profile.get("region"):
        lines += [f"## Региональный слой: код {profile['region']}", "",
                  "- Нет файла в kb/regions/ — региональные акты искать вручную.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--format", choices=["md", "json"], default="md")
    args = parser.parse_args()

    profile = load_profile(args.profile)
    if bad := unknown_flags(profile, known_flags()):
        print(f"ERROR: флаги не из анкеты: {bad}", file=sys.stderr)
        return 2
    picked = select(load_acts(), profile)
    region = load_region(profile.get("region"))

    if args.format == "json":
        out = [{k: v for k, v in a.items() if not k.startswith("_")} for a in picked]
        print(json.dumps(out, ensure_ascii=False, default=str, indent=2))
    else:
        print(render_md(profile, picked, region))
    return 0


if __name__ == "__main__":
    sys.exit(main())
