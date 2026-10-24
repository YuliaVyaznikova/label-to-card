import html
import json
import sys
import time

import httpx

from card.config import ROOT

FOLDER = ROOT / "data" / "off"
AGENT = "CardPrototype/0.1 (student research project)"
API = "https://world.openfoodfacts.org/api/v2"
IMAGES = "https://images.openfoodfacts.org/images/products"
FIELDS = [
    "code", "lang", "product_name", "product_name_ru", "quantity", "brands", "categories_tags",
    "ingredients_text_ru", "nutriments", "conservation_conditions_ru",
]
NUTRIENTS = {"energy_kcal": "energy-kcal_100g", "proteins_g": "proteins_100g", "fats_g": "fat_100g", "carbohydrates_g": "carbohydrates_100g"}
CATEGORY_TAGS = {
    "cheese": ["en:cheeses"],
    "meat": ["en:meats", "en:sausages", "en:hams", "en:prepared-meats"],
    "sweets": ["en:honeys", "en:jams", "en:chocolates", "en:candies", "en:biscuits", "en:confectioneries", "en:marshmallows"],
    "grocery": ["en:cereal-grains", "en:pastas", "en:flours", "en:teas", "en:nuts", "en:dried-fruits", "en:vegetable-oils", "en:chips-and-fries", "en:salty-snacks", "en:groats"],
}


def fetch(client, url, params, attempts=6):
    for attempt in range(attempts):
        response = client.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        print(f"http {response.status_code}, retry in {15 * (attempt + 1)} s", flush=True)
        time.sleep(15 * (attempt + 1))
    response.raise_for_status()


def search(pages):
    folder = FOLDER / "pages"
    folder.mkdir(parents=True, exist_ok=True)
    with httpx.Client(headers={"User-Agent": AGENT}, timeout=90) as client:
        for page in range(1, pages + 1):
            path = folder / f"{page:03d}.json"
            if path.exists():
                continue
            params = {"countries_tags_en": "russia", "languages_tags": "en:russian", "fields": ",".join(FIELDS),
                      "page_size": 100, "page": page, "sort_by": "unique_scans_n"}
            data = fetch(client, f"{API}/search", params)
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            print(f"page {page}: {len(data['products'])} products of {data['count']}", flush=True)
            if not data["products"]:
                break
            time.sleep(7)


def category(tags):
    for key, wanted in CATEGORY_TAGS.items():
        if any(tag in tags for tag in wanted):
            return key
    return "other"


def candidates():
    products = {}
    for path in sorted((FOLDER / "pages").glob("*.json")):
        for product in json.loads(path.read_text(encoding="utf-8"))["products"]:
            products[product["code"]] = product
    rows = []
    for product in products.values():
        nutriments = product.get("nutriments") or {}
        name = html.unescape(product.get("product_name_ru") or product.get("product_name") or "")
        if product.get("lang") != "ru" or not name or not product.get("ingredients_text_ru") or not product.get("quantity"):
            continue
        if any(key not in nutriments for key in NUTRIENTS.values()):
            continue
        rows.append({
            "id": f"off_{product['code']}",
            "code": product["code"],
            "category": category(product.get("categories_tags", [])),
            "truth": {
                "name": name,
                "composition": html.unescape(product["ingredients_text_ru"]),
                "net_quantity": product["quantity"],
                "storage": product.get("conservation_conditions_ru"),
                **{field: nutriments[key] for field, key in NUTRIENTS.items()},
            },
        })
    return rows


def folder_of(code):
    return f"{code[:3]}/{code[3:6]}/{code[6:9]}/{code[9:]}" if len(code) > 8 else code


def select(limit):
    rows = candidates()
    print(f"{len(rows)} candidates with Russian name, composition, quantity and nutrition", flush=True)
    manifest = []
    with httpx.Client(headers={"User-Agent": AGENT}, timeout=90) as client:
        for row in rows:
            if len(manifest) >= limit:
                break
            images = fetch(client, f"{API}/product/{row['code']}", {"fields": "images"}).get("product", {}).get("images", {})
            time.sleep(0.7)
            ids = {kind: str(images.get(f"{kind}_ru", {}).get("imgid", "")) for kind in ("front", "ingredients", "nutrition")}
            if not all(ids.values()) or ids["front"] in (ids["ingredients"], ids["nutrition"]):
                continue
            unique = list(dict.fromkeys([ids["front"], ids["ingredients"], ids["nutrition"]]))
            photos = [{"imgid": imgid, "kinds": [kind for kind, value in ids.items() if value == imgid],
                       "url": f"{IMAGES}/{folder_of(row['code'])}/{imgid}.jpg"} for imgid in unique]
            manifest.append({**row, "photos": photos})
    (FOLDER / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    counts = {}
    for row in manifest:
        counts[row["category"]] = counts.get(row["category"], 0) + 1
    print(f"{len(manifest)} products with separate front, ingredients and nutrition photos, by category {counts}")


def download(limit):
    rows = json.loads((FOLDER / "manifest.json").read_text(encoding="utf-8"))[:limit]
    with httpx.Client(headers={"User-Agent": AGENT}, timeout=120, follow_redirects=True) as client:
        for number, row in enumerate(rows, 1):
            folder = FOLDER / "images" / row["code"]
            folder.mkdir(parents=True, exist_ok=True)
            for photo in row["photos"]:
                path = folder / f"{photo['imgid']}.jpg"
                if path.exists():
                    continue
                response = client.get(photo["url"])
                if response.status_code == 200:
                    path.write_bytes(response.content)
                else:
                    print(f"{row['code']} {photo['imgid']}: http {response.status_code}", flush=True)
                time.sleep(0.2)
            if number % 20 == 0:
                print(f"{number} products", flush=True)


if __name__ == "__main__":
    command = sys.argv[1]
    argument = int(sys.argv[2]) if len(sys.argv) > 2 else None
    if command == "search":
        search(argument or 10)
    elif command == "select":
        select(argument or 120)
    elif command == "images":
        download(argument or 120)