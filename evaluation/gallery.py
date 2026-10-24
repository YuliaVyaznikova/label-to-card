import argparse
import html
import json

from card.config import ROOT, load_categories

from .metrics import ABLATED, correct
from .run import OUT

KINDS = {"front": "лицевая сторона", "ingredients": "состав", "nutrition": "пищевая ценность"}
UNITS = {"g": "г", "ml": "мл", "pcs": "шт"}
DURATIONS = {"days": "сут.", "months": "мес.", "years": "г.", "hours": "ч"}
METHODS = [("baseline", "Модель без проверки"), ("pipeline", "Сервис")]

STYLE = """
:root { --green: #2b6030; --grass: #238441; --lime: #a6ce39; --sun: #ffcb05; --ink: #1d2a1f; --muted: #64705f; --line: #e1e6db; --paper: #f4f6f0; }
* { box-sizing: border-box; }
body { margin: 0; font: 14px/1.5 Montserrat, "Segoe UI", Arial, sans-serif; color: var(--ink); background: var(--paper); }
header { background: var(--green); color: #fff; padding: 32px 16px 28px; }
header div, main { max-width: 1120px; margin: 0 auto; }
h1 { margin: 0; font-size: 28px; line-height: 1.2; font-weight: 600; }
header p { margin: 10px 0 0; max-width: 760px; color: rgba(255, 255, 255, 0.8); }
main { padding: 20px 16px 48px; }
nav { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 18px; }
button { font: inherit; font-size: 13px; font-weight: 600; border: 1px solid var(--line); background: #fff; color: var(--ink); border-radius: 999px; padding: 6px 14px; cursor: pointer; }
button.on { background: var(--grass); border-color: var(--grass); color: #fff; }
section { background: #fff; border: 1px solid var(--line); border-radius: 16px; padding: 20px; margin-bottom: 16px; }
h2 { margin: 0; font-size: 17px; font-weight: 600; }
.meta { margin: 4px 0 14px; color: var(--muted); font-size: 12px; }
.meta a { color: var(--grass); }
.photos { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; }
.photos a { display: flex; flex-direction: column; gap: 4px; color: var(--muted); text-decoration: none; font-size: 11px; }
.photos img { height: 150px; max-width: 100%; object-fit: contain; border: 1px solid var(--line); border-radius: 10px; background: var(--paper); }
.table { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; vertical-align: top; padding: 7px 10px; border-top: 1px solid var(--line); }
th { color: var(--muted); font-weight: 600; font-size: 12px; border-top: 0; }
td:first-child { color: var(--muted); white-space: nowrap; }
td.yes { background: #f1f7ea; }
td.no { background: #fdeceb; }
td.empty { color: #a3ab9f; }
.front { margin-top: 12px; padding: 10px 12px; border-radius: 10px; background: #fff8db; font-size: 13px; }
.front b { font-weight: 600; }
footer { max-width: 1120px; margin: 0 auto; padding: 0 16px 32px; color: var(--muted); font-size: 12px; }
"""

SCRIPT = """
const buttons = document.querySelectorAll('nav button')
buttons.forEach((button) => button.addEventListener('click', () => {
  buttons.forEach((other) => other.classList.toggle('on', other === button))
  document.querySelectorAll('section').forEach((section) => {
    const filter = button.dataset.filter
    section.hidden = filter === 'invented' ? section.dataset.invented !== 'yes' : filter !== 'all' && section.dataset.category !== filter
  })
}))
"""


def number(value):
    return f"{value:g}".replace(".", ",")


def show(name, kind, value):
    if not value:
        return ""
    main = value.get("value")
    if kind == "quantity":
        return f"{number(main)} {UNITS.get(value.get('unit'), value.get('unit'))}"
    if kind == "duration":
        return "не ограничен" if value.get("unit") == "unlimited" else f"{number(main)} {DURATIONS.get(value.get('unit'), value.get('unit'))}"
    if kind == "energy":
        return f"{number(main)} ккал"
    if kind == "number":
        return f"{number(main)} г"
    if kind == "percent":
        return f"{number(main)} %"
    return str(main or "")


def cell(text, mark=""):
    if not text:
        return '<td class="empty">пусто</td>'
    short = text if len(text) <= 160 else text[:157] + "..."
    return f'<td class="{mark}" title="{html.escape(text)}">{html.escape(short)}</td>'


def product(number_, row, results, spec, titles):
    full = {method: results.get(("full", method)) for method, _ in METHODS}
    names = [name for name in spec if any(item and name in item["fields"] for item in full.values())]
    lines = []
    for name in names:
        truth = next((item["fields"][name]["truth"] for item in full.values() if item and name in item["fields"]), None)
        known = show(name, spec[name]["kind"], {"value": float(truth)}) if isinstance(truth, (int, float)) else str(truth or "")
        cells = [cell(known)]
        for method, _ in METHODS:
            predicted = full[method]["fields"][name]["predicted"] if full[method] and name in full[method]["fields"] else None
            mark = "" if truth is None or not predicted else "yes" if correct(name, predicted, truth) else "no"
            cells.append(cell(show(name, spec[name]["kind"], predicted), mark))
        lines.append(f"<tr><td>{html.escape(spec[name]['title'])}</td>{''.join(cells)}</tr>")
    invented = {}
    for method, title in METHODS:
        item = results.get(("front_only", method))
        if not item:
            continue
        values = [f"{spec[name]['title'].split(',')[0].lower()} {show(name, spec[name]['kind'], field['predicted'])}"
                  for name, field in item["fields"].items() if name in ABLATED and not field["visible"] and field["predicted"]]
        invented[title] = values
    front = ""
    if any(invented.values()):
        parts = [f"<b>{html.escape(title)}</b> {html.escape('; '.join(values)) if values else 'ничего не придумал'}" for title, values in invented.items()]
        front = f'<div class="front">Только фото лицевой стороны, состава и пищевой ценности на нём нет. {". ".join(parts)}</div>'
    photos = []
    for photo in row["photos"]:
        label = ", ".join(KINDS.get(kind, kind) for kind in photo["kinds"])
        small = photo["url"].replace(".jpg", ".400.jpg")
        photos.append(f'<a href="{photo["url"]}" target="_blank" rel="noopener"><img src="{small}" alt="{label}" loading="lazy"><span>{label}</span></a>')
    header = "".join(f"<th>{title}</th>" for _, title in METHODS)
    return f'''<section data-category="{row['category']}" data-invented="{'yes' if invented.get('Модель без проверки') else 'no'}">
<h2>{number_}. {html.escape(row['truth']['name'] or row['code'])}</h2>
<p class="meta">{html.escape(titles.get(row['category'], row['category']))} · <a href="https://world.openfoodfacts.org/product/{row['code']}" target="_blank" rel="noopener">{row['code']} на Open Food Facts</a></p>
<div class="photos">{''.join(photos)}</div>
<div class="table"><table><tr><th>Поле</th><th>Open Food Facts</th>{header}</tr>{''.join(lines)}</table></div>
{front}
</section>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="full")
    args = parser.parse_args()
    folder = OUT / args.name
    categories = load_categories()
    spec = categories["fields"]
    titles = {key: value["title"] for key, value in categories["categories"].items()}
    manifest = {row["id"]: row for row in json.loads((ROOT / "data" / "off" / "manifest.json").read_text(encoding="utf-8"))}
    results = {}
    for line in (folder / "predictions.jsonl").read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        results.setdefault(item["id"], {})[(item["variant"], item["method"])] = item
    rows = [manifest[key] for key in results if key in manifest]
    sections = [product(number_, row, results[row["id"]], spec, titles) for number_, row in enumerate(rows, 1)]
    used = sorted({row["category"] for row in rows}, key=list(titles).index)
    buttons = "".join(f'<button data-filter="{key}">{html.escape(titles[key])}</button>' for key in used)
    page = f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Товары для оценки</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600&display=swap">
<style>{STYLE}</style></head><body>
<header><div><h1>Товары Open Food Facts и результаты сервиса</h1>
<p>{len(rows)} товаров с отдельными фото лицевой стороны, состава и пищевой ценности. Для каждого товара значения из базы Open Food Facts, ответ модели без проверки и итог сервиса. Зелёным отмечено совпадение с базой, красным расхождение. Жёлтая плашка показывает прогон только с лицевой стороной, где состава и пищевой ценности не видно.</p></div></header>
<main><nav><button data-filter="all" class="on">все</button>{buttons}<button data-filter="invented">модель без проверки выдумала значения</button></nav>
{''.join(sections)}</main>
<footer>Фото и данные товаров от участников Open Food Facts, фото по лицензии CC BY-SA, данные по лицензии ODbL. Фото загружаются с сайта Open Food Facts.</footer>
<script>{SCRIPT}</script>
</body></html>'''
    target = OUT / "gallery.html"
    target.write_text(page, encoding="utf-8")
    print(target, len(rows))


if __name__ == "__main__":
    main()