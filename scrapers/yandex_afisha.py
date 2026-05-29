"""
Скрапер afisha.yandex.ru — GraphQL API.
total берём из первого ответа paging.total → tqdm знает финиш.
promo_cards запрашиваем только если discountPercent != null.
"""

import hashlib
import re
import time
from datetime import date

import requests
from tqdm import tqdm

API_URL = "https://afisha.yandex.ru/api/graphql"
PROMO_CARD_URL = "https://afisha.yandex.ru/api/events/{event_id}/promo_cards"
LIMIT = 12

HEADERS = {
    "accept": "*/*",
    "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "referer": "https://afisha.yandex.ru/moscow/selections/discount-classical-concerts",
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "x-csrf-token": "null",
    "x-force-cors-preflight": "1",
}

GQL_QUERY = 'query SelectionEventsQuery($code: String!, $paging: PagingInput, $desktop: Boolean!, $eventsRankingType: ActualEventsSort!, $ticketsEnabled: Boolean!, $state: FacetsStateInput, $enablePersonalRecommendations: Boolean = false, $enableMLRecommendations: Boolean = false, $coordinates: CoordinatesInput, $multiFacetsFilter: MultiFacetsStateInput, $cursorPaging: CursorPagingInput) {\n  info: selection(code: $code) {\n    ...SelectionPageFragment\n    __typename\n  }\n  events: selectionEvents(code: $code, paging: $paging, sort: $eventsRankingType, filter: $state, enablePersonalRecommendations: $enablePersonalRecommendations, enableMLRecommendations: $enableMLRecommendations, coordinates: $coordinates, device: web, multiFacetsFilter: $multiFacetsFilter, cursorPaging: $cursorPaging) {\n    ...ActualEvents\n    __typename\n  }\n}\n\nfragment SelectionPageFragment on Selection {\n  ...SelectionBaseFragment\n  description\n  interval {\n    period\n    __typename\n  }\n  meta {\n    title\n    pageTitle\n    description\n    keywords\n    __typename\n  }\n  mainTag {\n    ...Tag\n    __typename\n  }\n  hasTickets @include(if: $ticketsEnabled)\n  adfoxBrandingId\n  adfoxBrandingIdTouch\n  contextTag {\n    code\n    __typename\n  }\n  __typename\n}\n\nfragment SelectionBaseFragment on Selection {\n  title\n  url\n  __typename\n}\n\nfragment Tag on Tag {\n  ...TagPreview\n  rubric {\n    ...TagRubricInfo\n    __typename\n  }\n  commercial {\n    ...TagCommercialInfo\n    __typename\n  }\n  adfoxBrandingId\n  adfoxBrandingIdTouch\n  adfoxSelectionBrandingId\n  adfoxSelectionBrandingIdTouch\n  meta {\n    title\n    pageTitle\n    keywords\n    description\n    __typename\n  }\n  __typename\n}\n\nfragment TagPreview on Tag {\n  id\n  adfoxBrandingId\n  adfoxBrandingIdTouch\n  rubricUrl\n  rubricPlacesUrl\n  code\n  description\n  type\n  status\n  name\n  namePlural\n  nameAcc: cases(case: accusative)\n  nameGen: cases(case: genetive)\n  nameAdj: cases(case: adjective)\n  plural {\n    ...PluralForms\n    __typename\n  }\n  __typename\n}\n\nfragment PluralForms on PluralForms {\n  one\n  some\n  many\n  none\n  __typename\n}\n\nfragment TagRubricInfo on TagRubricInfo {\n  enableEventsSorting\n  enableTopBannerOnNewLayout\n  disableTopBannerOnNewLayoutSelections\n  disableAdsTouch\n  noindex\n  shareImages {\n    facebook(size: origin) {\n      ...ImageSize\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment ImageSize on MediaImageSize {\n  url\n  width\n  height\n  precision\n  __typename\n}\n\nfragment TagCommercialInfo on TagCommercialInfo {\n  banner(size: origin) {\n    ...ImageSize\n    __typename\n  }\n  background(size: origin) {\n    ...ImageSize\n    __typename\n  }\n  color\n  url\n  description\n  links {\n    type\n    url\n    title\n    __typename\n  }\n  pixel\n  disableTopBanner\n  disableSidebarYabs\n  disableSidebarDirect\n  disableFooterDirect\n  __typename\n}\n\nfragment ActualEvents on ActualEventList {\n  items {\n    ...ActualEventWithTravelInfo\n    __typename\n  }\n  paging {\n    ...Paging\n    __typename\n  }\n  __typename\n}\n\nfragment ActualEventWithTravelInfo on ActualEvent {\n  ...ActualEvent\n  travelInfo {\n    ...TravelInfo\n    __typename\n  }\n  __typename\n}\n\nfragment ActualEvent on ActualEvent {\n  event {\n    ...EventPreview\n    __typename\n  }\n  scheduleInfo {\n    ...EventScheduleInfo\n    __typename\n  }\n  distance\n  isPersonal\n  commentsCount\n  __typename\n}\n\nfragment EventPreview on EventPreview {\n  id\n  url\n  title\n  originalTitle\n  dateReleased\n  permanent\n  type {\n    ...TagPreview\n    __typename\n  }\n  tags(codeNotIn: ["other"], status: approved) {\n    ...TagPreview\n    __typename\n  }\n  systemTags: tags(status: [approved, reviewed]) {\n    ...SystemTag\n    __typename\n  }\n  image {\n    ...EventPreviewImage\n    __typename\n  }\n  poster {\n    ...EventPreviewPoster\n    __typename\n  }\n  argument\n  promoArgument: summerFestArgument\n  contentRating\n  kinopoisk {\n    ...KinopoiskInfo\n    __typename\n  }\n  tickets @include(if: $ticketsEnabled) {\n    ...Ticket\n    __typename\n  }\n  userRating {\n    ...EventUserRatingPreview\n    __typename\n  }\n  isFavorite\n  isDisliked\n  promoImage2PreviewL: promoImage(type: preview_new_desktop) {\n    ...PromoImage2PreviewL\n    __typename\n  }\n  promoImage2PreviewM: promoImage(type: preview_new_desktop) {\n    ...PromoImage2PreviewM\n    __typename\n  }\n  promoImage2PreviewS: promoImage(type: preview_new_desktop) {\n    ...PromoImage2PreviewS\n    __typename\n  }\n  promoImage2PreviewXS: promoImage(type: preview_new_desktop) {\n    ...PromoImage2PreviewL\n    __typename\n  }\n  promoImage2FeaturedDesktop: promoImage(type: featured_rubric) @include(if: $desktop) {\n    ...PromoImage2FeaturedDesktop\n    __typename\n  }\n  promoImage2FeaturedTouch: promoImage(type: featured_touch) @skip(if: $desktop) {\n    ...PromoImage2FeaturedTouch\n    __typename\n  }\n  promoImage2FeaturedBannerDesktop: promoImage(type: mini_featured_rubric) {\n    ...PromoImage2FeaturedBannerDesktop\n    __typename\n  }\n  promoImage2FeaturedBannerTouch: promoImage(type: mini_featured_touch) @skip(if: $desktop) {\n    ...PromoImage2FeaturedBannerTouch\n    __typename\n  }\n  promoVideo2FeaturedDesktop: promoVideo(type: featured_rubric) @include(if: $desktop) {\n    poster {\n      ...PromoImage2FeaturedDesktop\n      __typename\n    }\n    mp4\n    webm\n    __typename\n  }\n  promoVideo2FeaturedTouch: promoVideo(type: featured_touch) @skip(if: $desktop) {\n    poster {\n      ...PromoImage2FeaturedTouch\n      __typename\n    }\n    mp4\n    webm\n    __typename\n  }\n  promoVideo2PreviewClassifiedDesktop: promoVideo(type: event_preview_classified_desktop) @include(if: $desktop) {\n    poster {\n      ...PromoVideo2PreviewClassifiedPosterDesktop\n      __typename\n    }\n    mp4\n    webm\n    __typename\n  }\n  __typename\n}\n\nfragment SystemTag on Tag {\n  code\n  __typename\n}\n\nfragment PromoVideo2PreviewClassifiedPosterDesktop on Image {\n  x1: image(size: s380x324) {\n    ...ImageSize\n    __typename\n  }\n  x2: image(size: s760x648) {\n    ...ImageSize\n    __typename\n  }\n  __typename\n}\n\nfragment PromoImage2FeaturedTouch on Image {\n  x1: image(size: s420x420_crop) {\n    ...ImageSize\n    __typename\n  }\n  x2: image(size: s840x840_crop) {\n    ...ImageSize\n    __typename\n  }\n  __typename\n}\n\nfragment PromoImage2FeaturedDesktop on Image {\n  x1: image(size: s940x380_crop) {\n    ...ImageSize\n    __typename\n  }\n  x2: image(size: s1880x760_crop) {\n    ...ImageSize\n    __typename\n  }\n  __typename\n}\n\nfragment PromoImage2FeaturedBannerTouch on Image {\n  x1: image(size: s220x144_crop) {\n    ...ImageSize\n    __typename\n  }\n  x2: image(size: s440x288_crop) {\n    ...ImageSize\n    __typename\n  }\n  __typename\n}\n\nfragment PromoImage2FeaturedBannerDesktop on Image {\n  x1: image(size: s285x167_plain_crop) {\n    ...ImageSize\n    __typename\n  }\n  x2: image(size: s570x334_plain_crop) {\n    ...ImageSize\n    __typename\n  }\n  __typename\n}\n\nfragment PromoImage2PreviewL on Image {\n  x1: image(size: s380x220_crop) {\n    ...ImageSize\n    __typename\n  }\n  x2: image(size: s760x440_crop) {\n    ...ImageSize\n    __typename\n  }\n  __typename\n}\n\nfragment PromoImage2PreviewM on Image {\n  x1: image(size: s343x190_crop) {\n    ...ImageSize\n    __typename\n  }\n  x2: image(size: s686x380_crop) {\n    ...ImageSize\n    __typename\n  }\n  __typename\n}\n\nfragment PromoImage2PreviewS on Image {\n  x1: image(size: s220x144_crop) {\n    ...ImageSize\n    __typename\n  }\n  x2: image(size: s440x288_crop) {\n    ...ImageSize\n    __typename\n  }\n  __typename\n}\n\nfragment EventUserRatingPreview on EventUserRatingPreview {\n  overall {\n    value\n    count\n    __typename\n  }\n  __typename\n}\n\nfragment Ticket on Ticket {\n  id\n  price {\n    currency\n    min\n    max\n    __typename\n  }\n  discount {\n    dateStart\n    dateFinish\n    discountPercent\n    __typename\n  }\n  discountPercents\n  hasSpecificLoyalty\n  hasSpecificPlusWalletPercent\n  plusWalletPercent\n  saleStatus\n  __typename\n}\n\nfragment KinopoiskInfo on KinopoiskInfo {\n  url\n  value: rating\n  votes\n  __typename\n}\n\nfragment EventPreviewPoster on Image {\n  subType\n  bgColor\n  source {\n    ...InfoSource\n    __typename\n  }\n  schedulePoster: image(size: s50x75) {\n    ...ImageSize\n    __typename\n  }\n  touchSchedulePoster: image(size: s220x144_crop) @skip(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  eventCoverPromoActionDiscount: image(size: s340x230_crop) @include(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  touchEventCoverPromoActionDiscount: image(size: s340x230_crop) @skip(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  eventCoverPromoActionPopular: image(size: s540x300_crop) @include(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  touchEventCoverPromoActionPopular: image(size: s700x472_crop) @skip(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  __typename\n}\n\nfragment InfoSource on InfoSource {\n  id\n  title\n  url\n  __typename\n}\n\nfragment EventPreviewImage on Image {\n  subType\n  bgColor\n  baseColor\n  source {\n    ...InfoSource\n    __typename\n  }\n  eventCover: image(size: s270x135_crop) @include(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  eventCoverXS: image(size: s90x60_crop) @include(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  eventCoverS: image(size: s100x60_crop) @include(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  eventCoverM: image(size: s380x190_crop) @include(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  eventCoverM2x: image(size: s760x380_crop) @include(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  eventCoverL: image(size: s380x220_crop) @include(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  eventCoverL2x: image(size: s760x440_crop) @include(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  microdata: image(size: origin) {\n    ...ImageSize\n    __typename\n  }\n  touchEventCoverS: image(size: s300x200_crop) @skip(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  touchEventCoverS2x: image(size: s420x280_crop) @skip(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  touchEventCoverM: image(size: s220x144_crop) @skip(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  touchEventCoverM2x: image(size: s440x288_crop) @skip(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  touchEventCoverL: image(size: s400x190_crop) @skip(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  touchEventCoverL2x: image(size: s800x380_crop) @skip(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  featured: image(size: s940x380_crop) @include(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  featuredSelection: image(size: s420x140_crop) @include(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  headingPrimaryS: image(size: s1260x400_crop) @include(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  touchHeadingCover: image(size: s770w) @skip(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  suggest: image(size: s130x90_crop) @include(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  touchSuggest: image(size: s250x170_crop) @skip(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  topEventImageTouch1x: image(size: s160x220_crop) @skip(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  topEventImageTouch2x: image(size: s320x440_crop) @skip(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  topEventImageDesktop1x: image(size: s240x300_crop) @include(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  topEventImageDesktop2x: image(size: s480x600_crop) @include(if: $desktop) {\n    ...ImageSize\n    __typename\n  }\n  __typename\n}\n\nfragment EventScheduleInfo on EventScheduleInfo {\n  dates\n  dateStarted\n  dateEnd\n  dateGroups(count: 4) {\n    ...ScheduleDateGroup\n    __typename\n  }\n  dateReleased\n  permanent\n  multiSession\n  tagsPreview\n  regularity {\n    ...Regularity\n    __typename\n  }\n  onlyPlace {\n    ...PlacePreview\n    __typename\n  }\n  oneOfPlaces {\n    ...PlacePreview\n    __typename\n  }\n  placePreview\n  placesTotal\n  preview(short: false) {\n    ...SchedulePreview\n    __typename\n  }\n  collapsedText(short: false)\n  prices {\n    currency\n    value\n    __typename\n  }\n  pushkinCardAllowed\n  __typename\n}\n\nfragment Regularity on Regularity {\n  singleShowtime\n  isRegular\n  daily\n  weekly {\n    ...WeeklyRegularity\n    __typename\n  }\n  __typename\n}\n\nfragment WeeklyRegularity on WeeklyRegularity {\n  times\n  weekdays\n  __typename\n}\n\nfragment PlacePreview on PlacePreview {\n  id\n  url\n  title\n  logo {\n    ...PlaceLogo\n    __typename\n  }\n  address\n  type {\n    ...TagPreview\n    __typename\n  }\n  tags(codeNotIn: ["other"], status: approved) {\n    ...TagPreview\n    __typename\n  }\n  systemTags: tags(status: [approved, reviewed]) {\n    ...SystemTag\n    __typename\n  }\n  city {\n    ...CityPreview\n    __typename\n  }\n  metro {\n    ...Metro\n    __typename\n  }\n  coordinates {\n    ...Coordinates\n    __typename\n  }\n  bgColor\n  logoColor\n  distance\n  isFavorite\n  promoImage2FeaturedDesktop: promoImage(type: featured_rubric) @include(if: $desktop) {\n    ...PromoImage2FeaturedDesktop\n    __typename\n  }\n  promoImage2FeaturedTouch: promoImage(type: featured_touch) @skip(if: $desktop) {\n    ...PromoImage2FeaturedTouch\n    __typename\n  }\n  promoImage2FeaturedBannerDesktop: promoImage(type: mini_featured_rubric) {\n    ...PromoImage2FeaturedBannerDesktop\n    __typename\n  }\n  promoImage2FeaturedBannerTouch: promoImage(type: mini_featured_touch) @skip(if: $desktop) {\n    ...PromoImage2FeaturedBannerTouch\n    __typename\n  }\n  promoVideo2FeaturedDesktop: promoVideo(type: featured_rubric) @include(if: $desktop) {\n    mp4\n    webm\n    poster {\n      ...PromoImage2FeaturedDesktop\n      __typename\n    }\n    __typename\n  }\n  promoVideo2FeaturedTouch: promoVideo(type: featured_touch) @skip(if: $desktop) {\n    mp4\n    webm\n    poster {\n      ...PromoImage2FeaturedTouch\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment PlaceLogo on Image {\n  bgColor\n  microdata: image(size: origin) {\n    ...ImageSize\n    __typename\n  }\n  place: image(size: s70x70) {\n    ...ImageSize\n    __typename\n  }\n  placeCover: image(size: s100x100) {\n    ...ImageSize\n    __typename\n  }\n  placeCoverXS: image(size: s103x103) {\n    ...ImageSize\n    __typename\n  }\n  placeCoverM: image(size: s170x170) {\n    ...ImageSize\n    __typename\n  }\n  touchPlace: image(size: s80x80) {\n    ...ImageSize\n    __typename\n  }\n  touchPlaceCard: image(size: s140x140) {\n    ...ImageSize\n    __typename\n  }\n  touchPlaceCover: image(size: s220x220) {\n    ...ImageSize\n    __typename\n  }\n  touchConcertPlace: image(size: s88x88_plain_crop) {\n    ...ImageSize\n    __typename\n  }\n  __typename\n}\n\nfragment CityPreview on CityPreview {\n  id\n  name\n  geoid\n  timezone\n  __typename\n}\n\nfragment Metro on Metro {\n  name\n  colors\n  __typename\n}\n\nfragment Coordinates on Coordinates {\n  longitude\n  latitude\n  __typename\n}\n\nfragment SchedulePreview on SchedulePreview {\n  type\n  text\n  startDate\n  regularity\n  singleDate {\n    day\n    month\n    __typename\n  }\n  __typename\n}\n\nfragment ScheduleDateGroup on ScheduleDateGroup {\n  title\n  date\n  period\n  hasTickets @include(if: $ticketsEnabled)\n  hasDiscounts @include(if: $ticketsEnabled)\n  __typename\n}\n\nfragment TravelInfo on TravelInfo {\n  aviaView {\n    minPrice {\n      ...Money\n      __typename\n    }\n    arrivalCity\n    departureCity\n    __typename\n  }\n  hotelView {\n    minPrice {\n      ...Money\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment Money on Money {\n  currency\n  value\n  __typename\n}\n\nfragment Paging on Paging {\n  limit\n  offset\n  total\n  __typename\n}\n'


def run() -> list[dict]:
    session = requests.Session()
    session.headers.update(HEADERS)

    all_items = []
    offset = 0
    total = None  # узнаём из первого ответа

    with tqdm(desc="  afisha.yandex", unit=" концерт",
              leave=True, position=1) as pbar:

        while True:
            json_data = {
                "operationName": "SelectionEventsQuery",
                "variables": {
                    "enablePersonalRecommendations": False,
                    "enableMLRecommendations": True,
                    "code": "discount-classical-concerts",
                    "desktop": True,
                    "eventsRankingType": "rank",
                    "ticketsEnabled": True,
                    "paging": {"limit": LIMIT, "offset": offset},
                    "multiFacetsFilter": {"dates": None},
                },
                "query": GQL_QUERY,
            }
            try:
                r = session.post(
                    API_URL,
                    params={"city": "moscow", "version": "555.0.0"},
                    json=json_data,
                    timeout=15,
                )
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                tqdm.write(f"  [afisha.yandex] ошибка offset={offset}: {e}")
                break

            events_block = data.get("data", {}).get("events", {})

            # Берём total из первого ответа и выставляем в pbar
            if total is None:
                total = (events_block.get("paging") or {}).get("total") or 0
                if total:
                    pbar.total = total
                    pbar.refresh()

            items_raw = events_block.get("items", [])
            if not items_raw:
                break

            batch = _parse(session, items_raw)
            all_items.extend(batch)
            pbar.update(len(batch))

            if len(items_raw) < LIMIT:
                break

            offset += LIMIT
            time.sleep(0.5)

    return all_items


def _parse(session: requests.Session, items: list[dict]) -> list[dict]:
    result = []
    today = str(date.today())

    for d in items:
        event = d.get("event", {})
        event_id = event.get("id", "")
        deal_url = event.get("url", "")
        url = f"https://afisha.yandex.ru{deal_url}" if deal_url else ""
        title_short = event.get("title", "")

        place = d.get("scheduleInfo", {}).get("onlyPlace") or {}
        venue = place.get("title", "") or ""
        address = place.get("address", "") or ""
        metros = place.get("metro") or []
        metro = ", ".join(m.get("name", "") for m in metros if m.get("name"))

        age = event.get("contentRating", "") or ""
        date_txt = (d.get("scheduleInfo", {}).get("preview") or {}).get("text", "") or ""

        tickets = event.get("tickets") or []
        ticket = tickets[0] if tickets else {}
        price_info = ticket.get("price") or {}
        price_min = price_info.get("min")
        price_max = price_info.get("max")
        price_new = ""
        if price_min is not None:
            price_new = f"от {price_min // 100} ₽"
            if price_max and price_max != price_min:
                price_new += f" до {price_max // 100} ₽"

        discount_info = ticket.get("discount") or {}
        discount_pct = discount_info.get("discountPercent")
        discount_str = f"{discount_pct}%" if discount_pct else ""
        promo_code = ""

        # promo_cards только если есть скидка
        if not discount_pct and event_id:
            promo_code, discount = _fetch_promo_code(session, event_id)
            if discount:
                discount_str = f"{discount}%" if discount_pct else ""
            time.sleep(0.3)

        photo = ""
        try:
            photo = event["image"]["microdata"]["url"]
        except (KeyError, TypeError):
            pass

        result.append({
            "id": _make_id(url or title_short),
            "url": url,
            "source": "yandex_afisha",
            # "title": title_short,
            "title_short": title_short,
            "description": "",
            "venue": venue,
            "address": address,
            "date": date_txt,
            "age": age,
            "price_old": "",
            "price_new": price_new,
            "discount_pct": discount_str,
            "promo_code": promo_code,
            "photo": photo,
            "found_at": today,
            "duplicate_ids": "",
        })

    return result


def _fetch_promo_code(session: requests.Session, event_id: str) -> tuple[str, str]:
    try:
        r = session.get(
            PROMO_CARD_URL.format(event_id=event_id),
            params={"city": "moscow"},
            timeout=10,
        )
        r.raise_for_status()
        cards = r.json()
    except Exception:
        return "", ""

    for card in cards.values():
        name_html = card.get("nameHtml") or ""

        # Промокод
        promo_match = re.search(r"<b>([A-Za-zА-Яа-я0-9_\-]+)</b>", name_html)

        # Скидка
        discount_match = re.search(r"Скидка\s+(\d+)%", name_html)

        if promo_match:
            promo_code = promo_match.group(1)
            discount = discount_match.group(1) if discount_match else ""

            return promo_code, discount

    return "", ""


def _make_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]
