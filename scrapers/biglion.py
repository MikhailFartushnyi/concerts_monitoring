"""
Скрапер biglion.ru — POST API + GraphQL для дат.

Прогресс: один tqdm с known total (из первого ответа API).
"""

import hashlib
import re
import time
from datetime import date as date_cls
from datetime import datetime

import requests
from tqdm import tqdm

API_URL = "https://www.biglion.ru/gateway/dealOfferService/api/v1/deal-offer"
GRAPHQL_URL = "https://ticket-service.biglion.ru/graphql"
LIMIT = 60

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://www.biglion.ru",
    "Pragma": "no-cache",
    "Referer": "https://www.biglion.ru/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

HEADERS_HTML = {**HEADERS,
                "Accept": "text/html,*/*",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Site": "none"}

BASE_BODY = {
    "filters": [{
        "base": [
            {"field": "categorySlug", "operator": "in",
             "value": "/services/other/kontserty-klassicheskoy-muzyki/"},
            {"field": "citySlug", "operator": "=", "value": "moscow"},
            {"operator": "and"},
            {"field": "holdDay", "operator": "=", "value": "0"},
        ]
    }],
    "sort": "startDate desc",
    "limit": LIMIT,
    "category": {
        "slug": "/services/other/kontserty-klassicheskoy-muzyki/",
        "site": "biglion",
        "city": "moscow",
        "mainPage": "off",
        "popular": "off",
    },
}


def run() -> list[dict]:
    session = requests.Session()
    session.headers.update(HEADERS)

    # ── Шаг 1: собираем все deals, узнаём total из первого ответа ─────────────
    raw_deals = []
    offset = 0
    total = None

    while True:
        body = {**BASE_BODY, "offset": offset}
        try:
            r = session.post(API_URL, json=body, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            tqdm.write(f"  [biglion] ошибка offset={offset}: {e}")
            break

        # total только из первого ответа
        if total is None:
            total = (data.get("data", {})
                     .get("data", {})
                     .get("totalCount") or 0)

        deals = (data.get("data", {})
                 .get("data", {})
                 .get("deals", []))
        if not deals:
            break

        raw_deals.extend(deals)

        if len(deals) < LIMIT:
            break

        offset += LIMIT
        time.sleep(0.5)

    # ── Шаг 2: для каждого — детальная страница + GraphQL ─────────────────────
    items = []
    today = str(date_cls.today())

    with tqdm(total=len(raw_deals), desc="  biglion",
              unit=" концерт", leave=True, position=1) as pbar:

        for d in raw_deals:
            do_id = d.get("id")
            deal_url = d.get("url", "")
            url = f"https://www.biglion.ru/deals/{deal_url}" if deal_url else ""

            locations = d.get("locations") or []
            address = locations[0].get("friendlyAddress", "") if locations else ""
            metro = locations[0].get("metro", "") if locations else ""

            # activity_id из детальной страницы
            activity_id = _get_activity_id(session, url)

            # дата/площадка из GraphQL
            venue = ""
            date_txt = ""
            if do_id and activity_id:
                events = _fetch_events(session, do_id, activity_id)
                if events:
                    venue = events[0].get("venue", "")
                    address = events[0].get("address", "") or address
                    dates = []
                    for ev in events:
                        ts = ev.get("date")
                        if ts:
                            dt = datetime.utcfromtimestamp(ts)
                            dates.append(dt.strftime("%d.%m.%Y, %H:%M"))
                    date_txt = "; ".join(dates)

            price_old = d.get("price", "")
            price_new = d.get("priceDiscounted", "")
            discount = d.get("discount", "")

            items.append({
                "id": _make_id(url or d.get("title", "")),
                "url": url,
                "source": "biglion",
                # "title": d.get("title", ""),
                "title_short": d.get("title", ""),
                "description": "",
                "venue": venue,
                "address": address,
                "date": date_txt,
                "age": "",
                "price_old": f"{price_old} ₽" if price_old else "",
                "price_new": f"{price_new} ₽" if price_new else "",
                "discount_pct": f"{discount}%" if discount else "",
                "promo_code": "",
                "photo": d.get("image", ""),
                "found_at": today,
                "duplicate_ids": "",
            })

            pbar.update(1)
            time.sleep(0.5)

    return items


def _get_activity_id(session: requests.Session, url: str) -> str:
    if not url:
        return ""
    try:
        r = session.get(url, headers=HEADERS_HTML, timeout=15)
        r.raise_for_status()
        m = re.search(r'"ticketActivityExtId"\s*:\s*"(\d+)"', r.text)
        return m.group(1) if m else ""
    except Exception as e:
        tqdm.write(f"  [biglion] ошибка детальной {url}: {e}")
        return ""


def _fetch_events(session: requests.Session, do_id: int, activity_id: str) -> list[dict]:
    query = (
        f'mutation {{ fetchAndSaveEvents(input: {{'
        f'doId: {do_id}, activityId: "{activity_id}", '
        f'ticketSystemId: 2, yandexCityId: null }}) '
        f'{{ id doId date eventExtId name venue address ticketsSystemId hallId }} }}'
    )
    try:
        r = session.post(GRAPHQL_URL, json={"query": query}, timeout=15)
        r.raise_for_status()
        return r.json().get("data", {}).get("fetchAndSaveEvents", [])
    except Exception as e:
        tqdm.write(f"  [biglion] GraphQL ошибка do_id={do_id}: {e}")
        return []


def _make_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]
