import os

# ── Пути ──────────────────────────────────────────────────────────────────────
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "concerts.xlsx")

# ── HTTP ───────────────────────────────────────────────────────────────────────
REQUEST_TIMEOUT = 15
REQUEST_DELAY = 1.5

# ── Столбцы xlsx (ключ → заголовок) ───────────────────────────────────────────
# Порядок здесь = порядок в файле
COLUMNS = {
    "id": "ID",
    "url": "Ссылка",
    "source": "Источник",
    # "title":        "Заголовок",
    "title_short": "Название",
    "description": "Описание",
    "venue": "Площадка",
    "address": "Адрес",
    "metro": "Метро",
    "date": "Дата",
    "age": "Возраст",
    "price_old": "Цена старая",
    "price_new": "Цена со скидкой",
    "discount_pct": "Скидка",
    "promo_code": "Промокод",
    "photo": "Фото",
    "found_at": "Найден",
    "duplicate_ids": "Дубли",
}

# ── Активные скраперы ──────────────────────────────────────────────────────────
SCRAPERS = {
    "gorbilet": True,
    "biglion": True,
    "yandex_afisha": True,
    "boombate": True,
}
