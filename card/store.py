import json
import sqlite3
import time
import uuid
from pathlib import Path


class Store:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.path = self.folder / "drafts.sqlite"
        with self.connect() as db:
            db.execute("create table if not exists drafts (id text primary key, status text, data text, idempotency text, created real, updated real)")

    def connect(self):
        return sqlite3.connect(self.path, check_same_thread=False)

    def new(self, hints, idempotency=None):
        if idempotency:
            with self.connect() as db:
                row = db.execute("select id from drafts where idempotency = ?", (idempotency,)).fetchone()
            if row:
                return row[0], False
        draft_id = "d_" + uuid.uuid4().hex[:12]
        (self.folder / draft_id).mkdir(parents=True, exist_ok=True)
        now = time.time()
        with self.connect() as db:
            db.execute("insert into drafts values (?, ?, ?, ?, ?, ?)", (draft_id, "processing", json.dumps({"hints": hints}, ensure_ascii=False), idempotency, now, now))
        return draft_id, True

    def save_photo(self, draft_id, content, suffix):
        folder = self.folder / draft_id
        number = len(self.photos(draft_id)) + 1
        path = folder / f"photo_{number}{suffix}"
        path.write_bytes(content)
        return path

    def photos(self, draft_id):
        folder = self.folder / draft_id
        return sorted(folder.glob("photo_*"), key=lambda path: int(path.stem.split("_")[1])) if folder.exists() else []

    def get(self, draft_id):
        with self.connect() as db:
            row = db.execute("select status, data from drafts where id = ?", (draft_id,)).fetchone()
        if not row:
            return None
        return {**json.loads(row[1]), "status": row[0]}

    def put(self, draft_id, data, status):
        data = {key: value for key, value in data.items() if key != "status"}
        with self.connect() as db:
            db.execute("update drafts set status = ?, data = ?, updated = ? where id = ?", (status, json.dumps(data, ensure_ascii=False), time.time(), draft_id))