import json
import threading
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import ROOT, category_fields, load_categories, load_config
from .pipeline import Pipeline
from .store import Store

Source = Literal["photo", "farmer", "edited", "none", "conflict"]
Status = Literal["processing", "draft", "ready", "confirmed", "sent", "failed"]


class Evidence(BaseModel):
    source: Literal["photo", "farmer"]
    text: str
    line: str | None = None
    photo: int | None = None
    box: list[int] | None = None


class FieldOut(BaseModel):
    value: dict | None = None
    raw: str | None = None
    source: Source
    confidence: float = 0.0
    evidence: list[Evidence] = []
    alternatives: list[dict] = []


class CategoryOut(BaseModel):
    key: str
    value: str
    confidence: float
    alternatives: list[dict] = []


class DescriptionOut(BaseModel):
    text: str
    checked: bool
    method: str
    problems: list[str] = []


class ReadinessOut(BaseModel):
    score: int
    fields: float
    photos: float
    text: float


class MissingOut(BaseModel):
    field: str | None = None
    action: str


class IssueOut(BaseModel):
    rule: str
    severity: Literal["block", "warning"]
    field: str | None = None
    message: str


class LogOut(BaseModel):
    field: str
    proposed: str | None = None
    source: str | None = None
    decision: Literal["accepted", "rejected"]
    reason: str | None = None
    score: float | None = None
    lines: list[str] = []


class PhotoOut(BaseModel):
    number: int
    url: str
    width: int | None = None
    height: int | None = None
    size: bool
    sharp: bool
    light: bool


class LineOut(BaseModel):
    id: str
    photo: int
    text: str
    confidence: float
    box: list[int]


class DraftOut(BaseModel):
    draft_id: str
    status: Status
    schema_version: str = "1.0"
    category: CategoryOut | None = None
    titles: dict[str, str] = {}
    kinds: dict[str, str] = {}
    required: list[str] = []
    fields: dict[str, FieldOut] = {}
    description: DescriptionOut | None = None
    readiness: ReadinessOut | None = None
    missing: list[MissingOut] = []
    moderation: list[IssueOut] = []
    photos: list[PhotoOut] = []
    lines: list[LineOut] = []
    log: list[LogOut] = []
    hints: dict = {}
    timings: dict = {}
    error: str | None = None


class Created(BaseModel):
    draft_id: str
    status: Status


class EditIn(BaseModel):
    fields: dict[str, str]


class CategoryInfo(BaseModel):
    key: str
    title: str


config = load_config()
categories = load_categories()
store = Store(config["paths"]["drafts"])
pipeline = Pipeline(config, categories)
lock = threading.Lock()


def warm_up():
    with lock:
        pipeline.ocr.load()
        pipeline.classifier.load()


@asynccontextmanager
async def lifespan(app):
    threading.Thread(target=warm_up, daemon=True).start()
    yield


app = FastAPI(title="Карточка товара за три минуты", version="1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def output(draft_id, data):
    category = data.get("category")
    fields_spec = category_fields(categories, category["key"]) if category else {}
    photos = [
        {"number": number, "url": f"/v1/drafts/{draft_id}/photos/{number}", **{key: quality.get(key) for key in ("width", "height", "size", "sharp", "light")}}
        for number, quality in enumerate(data.get("photos", []), 1)
    ]
    for field in data.get("fields", {}).values():
        for item in field.get("evidence", []):
            item.setdefault("line", None)
    return DraftOut(
        draft_id=draft_id, status=data["status"], category=category,
        titles={name: spec["title"] for name, spec in fields_spec.items()},
        kinds={name: spec["kind"] for name, spec in fields_spec.items()},
        required=[name for name, spec in fields_spec.items() if spec["required"]],
        fields=data.get("fields", {}), description=data.get("description"), readiness=data.get("readiness"),
        missing=data.get("missing", []), moderation=data.get("moderation", []), photos=photos,
        lines=list(data.get("lines", {}).values()), log=data.get("log", []), hints=data.get("hints", {}),
        timings=data.get("timings", {}), error=data.get("error"),
    )


def process(draft_id):
    data = store.get(draft_id)
    edits = {name: field["raw"] for name, field in data.get("fields", {}).items() if field.get("source") == "edited"}
    try:
        with lock:
            draft = pipeline.run(store.photos(draft_id), data.get("hints", {}))
            if edits:
                draft = pipeline.edit(draft, edits)
        status = draft.pop("status")
        store.put(draft_id, draft, status)
    except Exception as error:
        store.put(draft_id, {**data, "error": str(error)}, "failed")


@app.post("/v1/drafts", status_code=202, response_model=Created)
async def create_draft(background: BackgroundTasks, photos: list[UploadFile] = File(...), hints: str = Form("{}"),
                       idempotency_key: str | None = Header(None)):
    if not 1 <= len(photos) <= 5:
        raise HTTPException(422, "Нужно от 1 до 5 фото")
    try:
        parsed = json.loads(hints or "{}")
    except json.JSONDecodeError:
        raise HTTPException(422, "hints должен быть JSON")
    contents = []
    for photo in photos:
        if photo.content_type not in ("image/jpeg", "image/png"):
            raise HTTPException(415, "Фото должны быть в JPEG или PNG")
        content = await photo.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(413, "Фото больше 10 МБ")
        contents.append((content, ".png" if photo.content_type == "image/png" else ".jpg"))
    draft_id, fresh = store.new(parsed, idempotency_key)
    if fresh:
        for content, suffix in contents:
            store.save_photo(draft_id, content, suffix)
        background.add_task(process, draft_id)
    return Created(draft_id=draft_id, status=store.get(draft_id)["status"])


@app.get("/v1/drafts/{draft_id}", response_model=DraftOut)
def get_draft(draft_id: str):
    data = store.get(draft_id)
    if not data:
        raise HTTPException(404, "Черновик не найден")
    return output(draft_id, data)


@app.patch("/v1/drafts/{draft_id}/fields", response_model=DraftOut)
def edit_fields(draft_id: str, body: EditIn):
    data = store.get(draft_id)
    if not data:
        raise HTTPException(404, "Черновик не найден")
    if data["status"] in ("processing", "failed"):
        raise HTTPException(409, "Черновик ещё не готов")
    with lock:
        draft = pipeline.edit(data, body.fields)
    status = draft.pop("status")
    store.put(draft_id, draft, status)
    return output(draft_id, {**draft, "status": status})


@app.post("/v1/drafts/{draft_id}/photos", status_code=202, response_model=Created)
async def add_photo(draft_id: str, background: BackgroundTasks, photo: UploadFile = File(...)):
    data = store.get(draft_id)
    if not data:
        raise HTTPException(404, "Черновик не найден")
    if len(store.photos(draft_id)) >= 5:
        raise HTTPException(422, "Не больше 5 фото")
    if photo.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(415, "Фото должны быть в JPEG или PNG")
    store.save_photo(draft_id, await photo.read(), ".png" if photo.content_type == "image/png" else ".jpg")
    store.put(draft_id, {key: value for key, value in data.items() if key != "status"}, "processing")
    background.add_task(process, draft_id)
    return Created(draft_id=draft_id, status="processing")


@app.post("/v1/drafts/{draft_id}/confirm", response_model=DraftOut)
def confirm(draft_id: str):
    data = store.get(draft_id)
    if not data:
        raise HTTPException(404, "Черновик не найден")
    if any(issue["severity"] == "block" for issue in data.get("moderation", [])):
        raise HTTPException(409, "Есть блокирующие замечания модерации")
    if data["status"] != "ready":
        raise HTTPException(409, "Заполнены не все обязательные поля")
    store.put(draft_id, {key: value for key, value in data.items() if key != "status"}, "confirmed")
    return output(draft_id, {**data, "status": "confirmed"})


@app.get("/v1/drafts/{draft_id}/photos/{number}")
def photo_file(draft_id: str, number: int):
    photos = store.photos(draft_id)
    if not 1 <= number <= len(photos):
        raise HTTPException(404, "Фото не найдено")
    return FileResponse(photos[number - 1])


@app.get("/v1/categories", response_model=list[CategoryInfo])
def list_categories():
    return [CategoryInfo(key=key, title=spec["title"]) for key, spec in categories["categories"].items()]


@app.get("/v1/categories/{key}/schema")
def category_schema(key: str):
    if key not in categories["categories"]:
        raise HTTPException(404, "Категория не найдена")
    fields_spec = category_fields(categories, key)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": categories["categories"][key]["title"],
        "type": "object",
        "properties": {name: {"title": spec["title"], "x-kind": spec["kind"]} for name, spec in fields_spec.items()},
        "required": [name for name, spec in fields_spec.items() if spec["required"]],
    }


web = ROOT / "web" / "dist"
if web.exists():
    app.mount("/", StaticFiles(directory=web, html=True), name="web")