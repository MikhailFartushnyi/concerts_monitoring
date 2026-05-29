"""
Точка входа: python main.py
"""

import time
from tqdm import tqdm
import traceback
from config import SCRAPERS
from scrapers import SCRAPER_MAP
from storage import load_existing_ids, save_new_records
from utils.dedup import find_duplicates


def main_wrapper():
    try:
        # Запускаем основную функцию
        main()
        input(f'Работа завершена. Нажмите Enter для выхода!')
    except Exception as e:
        tqdm.write("❌ Произошла ошибка во время выполнения main():")
        # Полный traceback ошибки
        tqdm.write(traceback.format_exc())
        input("Сделайте скриншот ошибки и отправьте разработчику. Нажмите Enter, чтобы завершить...")

def main():
    t_start = time.time()
    active  = [slug for slug, enabled in SCRAPERS.items() if enabled]

    all_fresh: list[dict] = []
    stats: dict[str, int] = {}

    # position=0 — шкала сайтов всегда снизу
    # скраперы рисуют свою шкалу на position=1 (над этой)
    sites_bar = tqdm(
        active,
        desc="Сайты",
        unit=" сайт",
        position=0,
        leave=True,
    )

    for slug in sites_bar:
        sites_bar.set_postfix_str(slug)
        module = SCRAPER_MAP.get(slug)
        if not module:
            tqdm.write(f"[!] Скрапер '{slug}' не найден, пропускаем")
            continue
        try:
            items = module.run()
            all_fresh.extend(items)
            stats[slug] = len(items)
            tqdm.write(f"  ✓ {slug}: {len(items)} концертов")
        except Exception as e:
            tqdm.write(f"  [!] Ошибка '{slug}': {e}")
            stats[slug] = 0

    sites_bar.close()

    # ── Итог ──────────────────────────────────────────────────────────────────
    tqdm.write(f"\n{'─'*40}")
    for slug, count in stats.items():
        tqdm.write(f"  {slug:<20} {count:>6} концертов")
    tqdm.write(f"{'─'*40}")
    tqdm.write(f"  {'ИТОГО':<20} {len(all_fresh):>6}")

    if not all_fresh:
        tqdm.write("\nНет данных. Завершение.")
        return

    # ── Только новые ──────────────────────────────────────────────────────────
    existing_ids = load_existing_ids()
    new_records  = [r for r in all_fresh if r["id"] not in existing_ids]
    tqdm.write(f"\nУже в xlsx: {len(existing_ids)}  |  Новых: {len(new_records)}")

    if not new_records:
        tqdm.write("✅  Новых концертов нет. Файл не изменён.")
        tqdm.write(f"⏱  {time.time() - t_start:.1f} с")
        return

    # ── Дубли ─────────────────────────────────────────────────────────────────
    find_duplicates(new_records)
    dupes = sum(1 for r in new_records if r.get("duplicate_ids"))
    tqdm.write(f"Дублей на разных сайтах: {dupes} (жёлтый в xlsx)")

    # ── Сохранение ────────────────────────────────────────────────────────────
    saved = save_new_records(new_records)
    tqdm.write(f"\n✅  Добавлено {saved} строк → concerts.xlsx")
    tqdm.write(f"⏱  {time.time() - t_start:.1f} с")


if __name__ == "__main__":
    main_wrapper()