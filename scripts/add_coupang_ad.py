import os
import sys
import json
import hmac
import hashlib
import datetime
import html
import re
import random
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

API_HOST = "https://api-gateway.coupang.com"
DEEPLINK_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
SEARCH_PATH = "/v2/providers/affiliate_open_api/apis/openapi/products/search"


def make_auth(access_key: str, secret_key: str) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    signed_date = now.strftime("%y%m%dT%H%M%SZ")
    message = signed_date + "POST" + DEEPLINK_PATH
    signature = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return (
        "CEA algorithm=HmacSHA256, "
        f"access-key={access_key}, signed-date={signed_date}, signature={signature}"
    )


def extract_first_url(raw_text: str) -> str:
    raw_text = (raw_text or "").strip()
    pos = raw_text.find("https://")
    if pos < 0:
        return ""
    candidate = raw_text[pos:].split()[0].strip()
    return candidate.rstrip(".,)]}>\"'")


def extract_title_from_pasted_text(raw_text: str) -> str:
    """Use a product-name line that appears before the URL in Coupang share text."""
    if not raw_text:
        return ""
    before_url = raw_text.split("https://", 1)[0]
    lines = [re.sub(r"\s+", " ", line).strip() for line in before_url.splitlines()]
    ignored = {
        "쿠팡을 추천 합니다!",
        "쿠팡을 추천합니다!",
        "쿠팡을 추천 합니다! 🛒",
        "쿠팡을 추천합니다! 🛒",
    }
    candidates = []
    for line in lines:
        if not line or line in ignored:
            continue
        if line.startswith("아래 쿠팡 상품을") or line.startswith("쿠팡 상품을"):
            continue
        candidates.append(line)
    return candidates[-1] if candidates else ""


def convert_to_deeplink(coupang_url: str) -> str:
    if coupang_url.startswith("https://link.coupang.com/"):
        return coupang_url

    access_key = os.environ.get("COUPANG_ACCESS_KEY", "").strip()
    secret_key = os.environ.get("COUPANG_SECRET_KEY", "").strip()
    if not access_key or not secret_key:
        raise RuntimeError("Coupang Partners secrets are not configured.")

    body = json.dumps({"coupangUrls": [coupang_url]}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API_HOST + DEEPLINK_PATH,
        data=body,
        method="POST",
        headers={
            "Authorization": make_auth(access_key, secret_key),
            "Content-Type": "application/json;charset=UTF-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Coupang Deeplink API failed: HTTP {e.code}: {body_text[:500]}") from None

    if str(payload.get("rCode")) != "0" or not payload.get("data"):
        raise RuntimeError(f"Coupang Deeplink API returned an error: {payload.get('rMessage', 'unknown error')}")

    item = payload["data"][0]
    return item.get("shortenUrl") or item.get("landingUrl") or ""


def make_get_auth(access_key: str, secret_key: str, path: str, query: str) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    signed_date = now.strftime("%y%m%dT%H%M%SZ")
    message = signed_date + "GET" + path + query
    signature = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return (
        "CEA algorithm=HmacSHA256, "
        f"access-key={access_key}, signed-date={signed_date}, signature={signature}"
    )


def fetch_partner_product_name(coupang_url: str) -> str:
    """Get productName from Coupang Partners product-search API only on exact productId match."""
    m = re.search(r"/vp/products/(\d+)", coupang_url)
    if not m:
        return ""
    target_product_id = m.group(1)

    parsed = urllib.parse.urlparse(coupang_url)
    keyword = urllib.parse.parse_qs(parsed.query).get("q", [""])[0].strip()
    keyword = urllib.parse.unquote_plus(keyword) if keyword else ""
    if not keyword:
        return ""

    access_key = os.environ.get("COUPANG_ACCESS_KEY", "").strip()
    secret_key = os.environ.get("COUPANG_SECRET_KEY", "").strip()
    if not access_key or not secret_key:
        return ""

    query = urllib.parse.urlencode({"keyword": keyword, "limit": 10})
    req = urllib.request.Request(
        API_HOST + SEARCH_PATH + "?" + query,
        method="GET",
        headers={
            "Authorization": make_get_auth(access_key, secret_key, SEARCH_PATH, query),
            "Content-Type": "application/json;charset=UTF-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"Partners product search skipped: {exc}")
        return ""

    data = payload.get("data") or {}
    products = data.get("productData") or [] if isinstance(data, dict) else []
    for item in products:
        if not isinstance(item, dict):
            continue
        if str(item.get("productId", "")) == target_product_id:
            name = clean_product_title(str(item.get("productName") or ""))
            if name:
                print(f"Product name resolved from Coupang Partners API: {name}")
                return name
    print(f"Exact productId {target_product_id} not present in Partners search results for keyword: {keyword}")
    return ""


def clean_product_title(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"\s+", " ", value).strip()
    for suffix in (
        " | 쿠팡!",
        " - 쿠팡!",
        " : 쿠팡!",
        " | Coupang",
        " - Coupang",
    ):
        if value.endswith(suffix):
            value = value[:-len(suffix)].strip()
    return value


def fetch_product_title(coupang_url: str) -> str:
    req = urllib.request.Request(
        coupang_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            page = resp.read(2_000_000).decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"Product title lookup skipped: {exc}")
        return ""

    patterns = [
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']',
        r'<meta[^>]+name=["\']twitter:title["\'][^>]+content=["\']([^"\']+)["\']',
        r'<title[^>]*>(.*?)</title>',
    ]
    for pattern in patterns:
        match = re.search(pattern, page, re.I | re.S)
        if match:
            title = clean_product_title(match.group(1))
            if title and title.lower() not in {"coupang", "쿠팡!"}:
                return title

    for pattern in (
        r'"productName"\s*:\s*"((?:\\.|[^"\\])+)"',
        r'"title"\s*:\s*"((?:\\.|[^"\\])+)"',
    ):
        match = re.search(pattern, page, re.I)
        if match:
            try:
                decoded = json.loads('"' + match.group(1) + '"')
            except Exception:
                decoded = match.group(1)
            title = clean_product_title(decoded)
            if title and len(title) >= 3:
                return title

    return ""


def derive_product_name(coupang_url: str, request_data: dict, raw_text: str) -> str:
    product_name = (
        request_data.get("productName")
        or request_data.get("product_name")
        or request_data.get("title")
        or ""
    ).strip()

    if not product_name:
        product_name = fetch_partner_product_name(coupang_url)

    if not product_name:
        product_name = extract_title_from_pasted_text(raw_text)

    if not product_name:
        product_name = fetch_product_title(coupang_url)

    if not product_name:
        parsed = urllib.parse.urlparse(coupang_url)
        q = urllib.parse.parse_qs(parsed.query).get("q", [""])[0].strip()
        product_name = urllib.parse.unquote_plus(q) if q else "쿠팡 추천 상품"

    return clean_product_title(product_name)


def choose_ad_icon(product_name: str) -> tuple[str, str, str]:
    name = (product_name or "").lower()

    rules = [
        ("식품", ["치킨", "오리", "고기", "돼지", "소고기", "닭", "라면", "과자", "음료", "커피", "우유", "두유", "김치", "쌀", "과일", "채소", "식품", "간식", "빵", "떡", "소스", "참치", "햄", "만두", "피자", "버거", "계란", "달걀", "반숙란", "반숙계란", "구운계란", "훈제란"], "ad-icon-orange", "fa-utensils"),
        ("패션", ["여성", "남성", "니트", "반팔", "티셔츠", "셔츠", "블라우스", "바지", "팬츠", "원피스", "스커트", "재킷", "자켓", "코트", "신발", "운동화", "샌들", "슬리퍼", "가방", "모자", "의류"], "ad-icon-pink", "fa-shirt"),
        ("도서", ["책", "도서", "교재", "workbook", "student book", "문제집", "수험서", "모의고사", "토픽", "topik"], "ad-icon-yellow", "fa-book-open"),
        ("전자·가전", ["선풍기", "콘덴서", "모터", "충전기", "케이블", "이어폰", "헤드폰", "스피커", "노트북", "태블릿", "스마트폰", "모니터", "키보드", "마우스", "가전", "전기", "전자"], "ad-icon-yellow", "fa-plug"),
        ("생활·주방", ["주방", "냄비", "후라이팬", "프라이팬", "컵", "접시", "수저", "칼", "도마", "수납", "청소", "세제", "휴지", "타월", "수건", "생활", "콩나물 재배기"], "ad-icon-orange", "fa-house"),
        ("뷰티", ["화장품", "로션", "크림", "세럼", "에센스", "샴푸", "린스", "트리트먼트", "향수", "립", "마스크팩", "선크림", "쿠션", "파운데이션"], "ad-icon-pink", "fa-wand-magic-sparkles"),
        ("건강", ["건강", "비타민", "유산균", "영양제", "프로틴", "단백질", "안마", "마사지", "혈압", "체온계"], "ad-icon-pink", "fa-heart-pulse"),
        ("유아·완구", ["유아", "아기", "키즈", "어린이", "장난감", "완구", "블록", "가베", "레고", "인형", "퍼즐"], "ad-icon-yellow", "fa-puzzle-piece"),
        ("반려동물", ["강아지", "고양이", "반려", "애견", "애묘", "사료", "배변패드", "캣타워"], "ad-icon-orange", "fa-paw"),
        ("스포츠", ["운동", "헬스", "덤벨", "요가", "골프", "축구", "농구", "배드민턴", "테니스", "자전거", "캠핑", "등산"], "ad-icon-orange", "fa-dumbbell"),
        ("자동차", ["자동차", "차량", "와이퍼", "엔진", "타이어", "블랙박스", "세차", "카매트"], "ad-icon-yellow", "fa-car"),
        ("문구·사무", ["문구", "펜", "연필", "볼펜", "노트", "파일", "복사용지", "스테이플러", "사무"], "ad-icon-yellow", "fa-pen"),
    ]

    for category, keywords, color_class, icon_class in rules:
        if any(keyword.lower() in name for keyword in keywords):
            return category, color_class, icon_class

    common_icons = [
        ("공통", "ad-icon-orange", "fa-bag-shopping"),
        ("공통", "ad-icon-pink", "fa-gift"),
        ("공통", "ad-icon-yellow", "fa-star"),
        ("공통", "ad-icon-orange", "fa-box-open"),
        ("공통", "ad-icon-pink", "fa-tags"),
        ("공통", "ad-icon-yellow", "fa-cart-shopping"),
    ]
    return random.choice(common_icons)


def append_ad(index_path: Path, affiliate_url: str, product_name: str, color_class: str, icon_class: str) -> None:
    text = index_path.read_text(encoding="utf-8")
    if affiliate_url in text:
        print("Affiliate URL already exists; no duplicate ad added.")
        return

    marker = '    </div>\n\n    <p class="coupang-notice">'
    if marker not in text:
        raise RuntimeError("Could not find the end of the Coupang ads list in index.html.")

    ad = f'''      <a href="{html.escape(affiliate_url, quote=True)}" target="_blank" referrerpolicy="unsafe-url" class="ad-card">\n        <div class="ad-icon {html.escape(color_class)}"><i class="fa-solid {html.escape(icon_class)}"></i></div>\n        <p><b>{html.escape(product_name)}</b></p>\n        <span class="ad-cta">보러가기 →</span>\n      </a>\n\n'''
    text = text.replace(marker, ad + marker, 1)
    index_path.write_text(text, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: add_coupang_ad.py <request.json>")

    request_path = Path(sys.argv[1])
    data = json.loads(request_path.read_text(encoding="utf-8"))
    raw_text = data.get("rawText") or data.get("text") or data.get("url") or ""
    coupang_url = extract_first_url(raw_text)

    if not (
        coupang_url.startswith("https://www.coupang.com/")
        or coupang_url.startswith("https://link.coupang.com/")
    ):
        raise RuntimeError("Request must contain a valid Coupang URL beginning with https://.")

    affiliate_url = convert_to_deeplink(coupang_url)
    if not affiliate_url:
        raise RuntimeError("Coupang API returned no affiliate URL.")

    product_name = derive_product_name(coupang_url, data, raw_text)
    category, color_class, icon_class = choose_ad_icon(product_name)
    append_ad(Path("index.html"), affiliate_url, product_name, color_class, icon_class)

    Path(".coupang_last_result.json").write_text(
        json.dumps(
            {
                "affiliateUrl": affiliate_url,
                "productName": product_name,
                "category": category,
                "icon": icon_class,
                "iconColorClass": color_class,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Coupang affiliate ad prepared successfully: {product_name} [{category} / {icon_class}]")


if __name__ == "__main__":
    main()
