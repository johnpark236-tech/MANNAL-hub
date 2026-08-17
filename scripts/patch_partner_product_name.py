from pathlib import Path

p = Path('scripts/add_coupang_ad.py')
s = p.read_text(encoding='utf-8')

s = s.replace(
    'DEEPLINK_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"\n',
    'DEEPLINK_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"\nSEARCH_PATH = "/v2/providers/affiliate_open_api/apis/openapi/products/search"\n'
)

needle = '''def clean_product_title(value: str) -> str:\n'''
insert = '''def make_get_auth(access_key: str, secret_key: str, path: str, query: str) -> str:\n    now = datetime.datetime.now(datetime.timezone.utc)\n    signed_date = now.strftime("%y%m%dT%H%M%SZ")\n    message = signed_date + "GET" + path + query\n    signature = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()\n    return (\n        "CEA algorithm=HmacSHA256, "\n        f"access-key={access_key}, signed-date={signed_date}, signature={signature}"\n    )\n\n\ndef fetch_partner_product_name(coupang_url: str) -> str:\n    """Get productName from Coupang Partners product-search API only on exact productId match."""\n    m = re.search(r"/vp/products/(\\d+)", coupang_url)\n    if not m:\n        return ""\n    target_product_id = m.group(1)\n\n    parsed = urllib.parse.urlparse(coupang_url)\n    keyword = urllib.parse.parse_qs(parsed.query).get("q", [""])[0].strip()\n    keyword = urllib.parse.unquote_plus(keyword) if keyword else ""\n    if not keyword:\n        return ""\n\n    access_key = os.environ.get("COUPANG_ACCESS_KEY", "").strip()\n    secret_key = os.environ.get("COUPANG_SECRET_KEY", "").strip()\n    if not access_key or not secret_key:\n        return ""\n\n    query = urllib.parse.urlencode({"keyword": keyword, "limit": 10})\n    req = urllib.request.Request(\n        API_HOST + SEARCH_PATH + "?" + query,\n        method="GET",\n        headers={\n            "Authorization": make_get_auth(access_key, secret_key, SEARCH_PATH, query),\n            "Content-Type": "application/json;charset=UTF-8",\n        },\n    )\n    try:\n        with urllib.request.urlopen(req, timeout=30) as resp:\n            payload = json.loads(resp.read().decode("utf-8"))\n    except Exception as exc:\n        print(f"Partners product search skipped: {exc}")\n        return ""\n\n    data = payload.get("data") or {}\n    products = data.get("productData") or [] if isinstance(data, dict) else []\n    for item in products:\n        if not isinstance(item, dict):\n            continue\n        if str(item.get("productId", "")) == target_product_id:\n            name = clean_product_title(str(item.get("productName") or ""))\n            if name:\n                print(f"Product name resolved from Coupang Partners API: {name}")\n                return name\n    print(f"Exact productId {target_product_id} not present in Partners search results for keyword: {keyword}")\n    return ""\n\n\n'''
if 'def fetch_partner_product_name' not in s:
    s = s.replace(needle, insert + needle)

old = '''    if not product_name:\n        product_name = extract_title_from_pasted_text(raw_text)\n\n    if not product_name:\n        product_name = fetch_product_title(coupang_url)\n'''
new = '''    if not product_name:\n        product_name = fetch_partner_product_name(coupang_url)\n\n    if not product_name:\n        product_name = extract_title_from_pasted_text(raw_text)\n\n    if not product_name:\n        product_name = fetch_product_title(coupang_url)\n'''
if old not in s:
    raise SystemExit('derive_product_name target block not found')
s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('Patched Partners API productName lookup.')
