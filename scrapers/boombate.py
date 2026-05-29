"""
Скрапер boombate.com — двухэтапный:
  1. GET /json/city/42426/category/1136/deal  → список slug'ов
  2. GET /slug → HTML детальной страницы → парсинг selectolax

Только московские концерты классической музыки (cityId=42426).
Стендапы и прочее отфильтровываются по ключевым словам.
"""

import hashlib
import re
import time
from datetime import date

import requests
from selectolax.parser import HTMLParser
from tqdm import tqdm

LIST_URL       = "https://boombate.com/json/city/42426/category/1136/deal"
BASE_URL       = "https://boombate.com"
MOSCOW_CITY_ID = 42426

# Слова в title/name → пропускаем (стендап и подобное)
EXCLUDE_KEYWORDS = [
    "стендап", "stand-up", "standup", "stand up",
    "комик", "юмор", "comedy", "комедия",
    "дискотек", "вечеринк", "квиз", "квн",
]

HEADERS_API = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Pragma": "no-cache",
    "Referer": "https://boombate.com/kontserty",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

HEADERS_HTML = {**HEADERS_API}
HEADERS_HTML.pop("X-Requested-With")
HEADERS_HTML["Accept"] = "text/html,application/xhtml+xml,*/*"
HEADERS_HTML["Sec-Fetch-Mode"] = "navigate"
HEADERS_HTML["Sec-Fetch-Dest"] = "document"
HEADERS_HTML["Sec-Fetch-Site"] = "none"

LIST_PARAMS = {
    "sort": "new",
    "order": "desc",
    "offset": "0",
    "limit": "0",
    "subways": "",
    "districts": "",
}


def _is_excluded(text: str) -> bool:
    """True если название содержит стоп-слова (без учёта регистра)."""
    low = text.lower()
    return any(kw in low for kw in EXCLUDE_KEYWORDS)


def run() -> list[dict]:
    session = requests.Session()

    # ── Шаг 1: список slug'ов ─────────────────────────────────────────────────
    session.headers.update(HEADERS_API)
    try:
        r = session.get(LIST_URL, params=LIST_PARAMS, timeout=15)
        r.raise_for_status()
        deals_raw = r.json()
    except Exception as e:
        tqdm.write(f"  [boombate] ошибка списка: {e}")
        return []

    if not isinstance(deals_raw, list):
        tqdm.write(f"  [boombate] неожиданный формат: {type(deals_raw)}")
        return []

    slugs = []
    skipped = 0
    for d in deals_raw:
        name = d.get("name", "") or d.get("slug", "")

        # Фильтр стоп-слов на этапе списка (быстро, без доп. запросов)
        if _is_excluded(name):
            skipped += 1
            continue

        is_moscow = any(
            (a.get("city") or {}).get("id") == MOSCOW_CITY_ID
            for a in (d.get("addresses") or [])
        )
        if is_moscow:
            slugs.append({
                "slug":       d.get("slug", ""),
                "smallImage": d.get("smallImage", ""),
            })

    if skipped:
        tqdm.write(f"  [boombate] отфильтровано по стоп-словам: {skipped}")

    # ── Шаг 2: детальные страницы ─────────────────────────────────────────────
    session.headers.update(HEADERS_HTML)
    items = []
    today = str(date.today())

    for entry in tqdm(slugs, desc="  boombate", unit=" концерт", leave=True):
        slug = entry["slug"]
        if not slug:
            continue
        url = f"{BASE_URL}/{slug}"
        try:
            r = session.get(url, timeout=15)
            r.raise_for_status()
            item = _parse_detail(r.text, url, entry["smallImage"], today)
            if item:
                items.append(item)
        except Exception as e:
            tqdm.write(f"  [boombate] ошибка {slug}: {e}")
        time.sleep(0.7)

    return items


def _parse_detail(html: str, url: str, small_image: str, today: str) -> dict | None:
    tree = HTMLParser(html)

    title = _text(tree, "h1.deal-title")
    if not title:
        return None

    # Дополнительный фильтр на детальной странице (заголовок может отличаться от slug)
    if _is_excluded(title):
        return None

    description = _text(tree, "p.deal-text")

    # Фото
    photo = ""
    img = tree.css_first("img.gallery-item--main")
    if img:
        photo = img.attributes.get("src", "") or small_image
    if not photo:
        photo = small_image

    # Блок условий
    conditions = tree.css_first(".deal-conditions-content")
    conditions_text = conditions.text(strip=True) if conditions else ""

    # Промокод — h3 содержит ТОЛЬКО "Промокод <КОД>" и ничего больше
    # Пропускаем h3 вида "Промокод дает право..." (описание, не код)
    promo_code = ""
    for h3 in tree.css(".deal-conditions-content h3"):
        t = h3.text(strip=True)
        m = re.match(r"[Пп]ромокод\s+([А-Яа-яA-Za-z0-9_\-]+)\s*$", t)
        if m:
            promo_code = m.group(1)
            break

    # Цена
    price_new = ""
    m = re.search(r"[Оо]т\s+([\d\s]+)\s*р", conditions_text)
    if m:
        price_new = f"от {m.group(1).strip()} ₽"

    # Скидка
    discount_pct = ""
    m = re.search(r"[Сс]кидк[аи]\s+(\d+)\s*%", title)
    if m:
        discount_pct = f"{m.group(1)}%"

    # Возраст: "Возрастное ограничение: балкон 12+, партер 6+" → берём минимум
    age = ""
    for li in (conditions.css("li") if conditions else []):
        if "Возрастное ограничение" in li.text(strip=True):
            ages = re.findall(r"(\d+)\+", li.text(strip=True))
            if ages:
                age = str(min(int(a) for a in ages)) + "+"
            break

    # Дата и время — два варианта структуры:
    # 1. "Концерт состоится 12 июля, начало в 19:00." (одна дата)
    # 2. Блок "Москва:" с несколькими li вида "29 мая в 20:00"
    MONTHS = r"января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря"
    date_txt = ""

    # Вариант 1: "Концерт состоится ..."
    m = re.search(
        rf"[Кк]онцерт состоится\s+"
        rf"(\d{{1,2}}\s+(?:{MONTHS})(?:\s+\d{{4}}(?:\s+года)?)?),?\s*(?:начало в\s*([\d:]+))?",
        conditions_text,
    )
    if m:
        date_txt = m.group(1).strip()
        if m.group(2):
            date_txt += ", " + m.group(2)

    # Вариант 2: блок с городами — берём только московские даты
    if not date_txt and conditions:
        raw_html = conditions.html or ""
        if re.search(r"[Мм]осква", raw_html):
            # Разбиваем по h3 и ищем московский блок
            blocks = re.split(r"<h3[^>]*>", raw_html)
            moscow_dates = []
            in_moscow = False
            for block in blocks:
                text = re.sub(r"<[^>]+>", " ", block).strip()
                if re.search(r"^[Мм]осква", text):
                    in_moscow = True
                    continue
                if in_moscow:
                    lis = re.findall(r"<li[^>]*>(.*?)</li>", block, re.DOTALL)
                    for li in lis:
                        li_text = re.sub(r"<[^>]+>", " ", li).strip()
                        dm = re.search(
                            rf"(\d{{1,2}}\s+(?:{MONTHS})(?:\s+\d{{4}})?)"
                            rf"(?:\s+в\s+([\d:]+))?",
                            li_text,
                        )
                        if dm:
                            entry = dm.group(1).strip()
                            if dm.group(2):
                                entry += ", " + dm.group(2)
                            moscow_dates.append(entry)
                    break  # только первый московский блок
            if moscow_dates:
                date_txt = "; ".join(moscow_dates)

    # ── Адрес и метро: два источника ─────────────────────────────────────────
    venue, address, metro = "", "", ""

    # Источник 1: текст li "Место проведения: X. Адрес: Y (м. Z)."
    for li in (conditions.css("li") if conditions else []):
        li_text = li.text(strip=True)
        if "Место проведения" in li_text:
            m = re.search(r"Место проведения:\s*([^\.]+)", li_text)
            if m:
                venue = m.group(1).strip()
            m = re.search(r"Адрес:\s*([^(]+)", li_text)
            if m:
                address = m.group(1).strip().rstrip(",.")
            m = re.search(r"\(м\.?\s*([^)]+)\)", li_text)
            if m:
                metro = m.group(1).strip()
            break

    # Источник 2: структурированный блок .deal-locations → ищем московский город
    if not address or not metro:
        for loc in tree.css(".deal-location"):
            city_el = loc.css_first(".deal-location-city")
            if not city_el:
                continue
            if "Москва" not in city_el.text(strip=True):
                continue
            # Нашли московский блок
            if not address:
                addr_el = loc.css_first("[itemprop='streetAddress']")
                if addr_el:
                    address = addr_el.text(strip=True)
            if not metro:
                metro_el = loc.css_first(".deal-address-metro a")
                if metro_el:
                    metro = metro_el.text(strip=True)
            break

    if not venue and metro:
        venue = metro

    return {
        "id":            _make_id(url),
        "url":           url,
        "source":        "boombate",
        # "title":         title,
        "title_short":   title,
        "description":   description,
        "venue":         venue,
        "address":       address,
        "date":          date_txt,
        "age":           age,
        "price_old":     "",
        "price_new":     price_new,
        "discount_pct":  discount_pct,
        "promo_code":    promo_code,
        "photo":         photo,
        "found_at":      today,
        "duplicate_ids": "",
    }


def _text(tree, selector: str) -> str:
    el = tree.css_first(selector)
    return el.text(strip=True) if el else ""


def _make_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]