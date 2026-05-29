"""
Поиск одинаковых концертов с разных сайтов.

Логика:
  Два концерта считаются "одним и тем же", если совпадают оба условия:
    1. Нечёткое совпадение названий (ratio >= TITLE_THRESHOLD)
    2. Совпадение даты (если оба поля непустые)

В столбце duplicate_ids каждой записи сохраняются id концертов-дублей
с других источников — клиент видит все варианты и выбирает сам.
"""

import re
from difflib import SequenceMatcher

# Минимальный порог схожести названий (0.0 – 1.0)
TITLE_THRESHOLD = 0.72


def _normalize_title(title: str) -> str:
    """Приводим к нижнему регистру, убираем пунктуацию и лишние пробелы."""
    title = title.lower()
    title = re.sub(r"[^\w\s]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _dates_compatible(d1: str, d2: str) -> bool:
    """
    Возвращает True если даты совпадают или хотя бы одна пустая.
    Сравниваем первые 10 символов (YYYY-MM-DD или DD.MM.YYYY).
    """
    if not d1 or not d2:
        return True
    # оставляем только цифры для сравнения
    clean = lambda d: re.sub(r"\D", "", d)[:8]
    return clean(d1) == clean(d2)


def find_duplicates(records: list[dict]) -> list[dict]:
    """
    Принимает объединённый список концертов со всех сайтов.
    Заполняет поле duplicate_ids для записей, у которых есть аналоги
    с других источников.
    Возвращает тот же список (изменяет на месте).
    """
    n = len(records)
    norm_titles = [_normalize_title(r.get("title", "")) for r in records]

    for i in range(n):
        dupes = []
        for j in range(n):
            if i == j:
                continue
            if records[i]["source"] == records[j]["source"]:
                continue  # дубли только с РАЗНЫХ сайтов
            sim = _similarity(norm_titles[i], norm_titles[j])
            if sim >= TITLE_THRESHOLD:
                if _dates_compatible(records[i].get("date", ""), records[j].get("date", "")):
                    dupes.append(records[j]["id"])

        if dupes:
            existing = records[i].get("duplicate_ids", "")
            existing_set = set(existing.split(",")) if existing else set()
            existing_set.update(dupes)
            records[i]["duplicate_ids"] = ",".join(sorted(existing_set))

    return records
