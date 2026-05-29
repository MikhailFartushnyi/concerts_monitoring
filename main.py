"""
Точка входа: python main.py
"""

import time
from tqdm import tqdm

from config import SCRAPERS
from scrapers import SCRAPER_MAP
from storage import load_existing_ids, save_new_records
from utils.dedup import find_duplicates


def main():
    t_start = time.time()

    active = [slug for slug, enabled in SCRAPERS.items() if enabled]

    # ── 1. Сбор данных ────────────────────────────────────────────────────────
    all_fresh: list[dict] = []
    stats: dict[str, int] = {}

    print("🎼  Мониторинг концертов классической музыки\n")

    for slug in tqdm(active, desc="Сайты", unit=" сайт", position=0):
        module = SCRAPER_MAP.get(slug)
        if not module:
            tqdm.write(f"[!] Скрапер '{slug}' не найден, пропускаем")
            continue
        try:
            items = module.run()
            all_fresh.extend(items)
            stats[slug] = len(items)
        except Exception as e:
            tqdm.write(f"[!] Ошибка '{slug}': {e}")
            stats[slug] = 0

    # ── Итог по сайтам ────────────────────────────────────────────────────────
    print(f"\n{'─'*40}")
    for slug, count in stats.items():
        print(f"  {slug:<20} {count:>6} концертов")
    print(f"{'─'*40}")
    print(f"  {'ИТОГО':<20} {len(all_fresh):>6}")

    if not all_fresh:
        print("\nНет данных. Завершение.")
        return

    # ── 2. Только новые ───────────────────────────────────────────────────────
    existing_ids = load_existing_ids()
    new_records  = [r for r in all_fresh if r["id"] not in existing_ids]
    print(f"\nУже в xlsx: {len(existing_ids)}  |  Новых: {len(new_records)}")

    if not new_records:
        print("✅  Новых концертов нет. Файл не изменён.")
        _elapsed(t_start)
        return

    # ── 3. Дубли между сайтами ────────────────────────────────────────────────
    find_duplicates(new_records)
    dupes = sum(1 for r in new_records if r.get("duplicate_ids"))
    print(f"Дублей на разных сайтах: {dupes} (жёлтый в xlsx)")

    # ── 4. Сохранение ─────────────────────────────────────────────────────────
    saved = save_new_records(new_records)
    print(f"\n✅  Добавлено {saved} строк → concerts.xlsx")
    _elapsed(t_start)


def _elapsed(t: float):
    print(f"⏱  {time.time() - t:.1f} с")


if __name__ == "__main__":
    main()
