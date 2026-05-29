"""
Поиск одинаковых концертов с разных сайтов.

Проблема старой версии:
  Порог 0.72 + сравнение "грязных" title давал ложные дубли.
  Слова "концерт", "билет", "скидка 25%" есть у всех — SequenceMatcher
  видел их как совпадение и помечал разные события как дубли.

Новая логика:
  1. Очищаем название от стоп-слов (концерт, билет, скидка X% и т.д.)
  2. Сравниваем очищенные title_short (не title — там маркетинговые хвосты)
  3. Порог поднят до 0.82 — нужно реальное совпадение имён/программы
  4. Даты совместимы или хотя бы одна пустая
"""

import re
from difflib import SequenceMatcher

TITLE_THRESHOLD = 0.82

STOP_WORDS = [
    r"скидк[аиуой]\s+\d+\s*%",
    r"со\s+скидк[аиуой]",
    r"скидк[аиуой]",
    r"\d+\s*%",
    r"\bбилет[ыа]?\b",
    r"\bконцерт[а-я]*\b",
    r"\bвходн[а-я]+\b",
    r"\bна\b",
    r"\bв\b",
    r"\bи\b",
]

STOP_RE = re.compile("|".join(STOP_WORDS), re.IGNORECASE)


def _normalize(title: str) -> str:
    title = title.lower()
    title = STOP_RE.sub(" ", title)
    title = re.sub(r"[^\w\s]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _dates_compatible(d1: str, d2: str) -> bool:
    if not d1 or not d2:
        return True
    clean = lambda d: re.sub(r"\D", "", d)[:8]
    return clean(d1) == clean(d2)


def find_duplicates(records: list[dict]) -> list[dict]:
    n = len(records)

    # Берём title_short — без маркетинговых хвостов "со скидкой 25%"
    norm = []
    for r in records:
        raw = r.get("title_short") or r.get("title") or ""
        norm.append(_normalize(raw))

    for i in range(n):
        if not norm[i]:
            continue
        dupes = []
        for j in range(n):
            if i == j:
                continue
            if records[i]["source"] == records[j]["source"]:
                continue
            if not norm[j]:
                continue
            if _similarity(norm[i], norm[j]) >= TITLE_THRESHOLD:
                if _dates_compatible(
                    records[i].get("date", ""),
                    records[j].get("date", ""),
                ):
                    dupes.append(records[j]["id"])

        if dupes:
            existing     = records[i].get("duplicate_ids", "")
            existing_set = set(existing.split(",")) if existing else set()
            existing_set.update(dupes)
            records[i]["duplicate_ids"] = ",".join(sorted(existing_set))

    return records