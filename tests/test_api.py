import threading
import time

from card import api
from card.store import Store


def test_parallel_edits_keep_both_fields(tmp_path, monkeypatch):
    store = Store(tmp_path)
    draft_id, _ = store.new({})
    store.put(draft_id, {"fields": {}}, "ready")

    def slow_edit(draft, edits):
        time.sleep(0.2)
        return {**draft, "fields": {**draft["fields"], **edits}, "status": "ready"}

    monkeypatch.setattr(api, "store", store)
    monkeypatch.setattr(api.pipeline, "edit", slow_edit)
    monkeypatch.setattr(api, "output", lambda draft_id, data: data)
    threads = [threading.Thread(target=api.edit_fields, args=(draft_id, api.EditIn(fields={name: "1"}))) for name in ("net_quantity", "shelf_life")]
    for thread in threads:
        thread.start()
        time.sleep(0.05)
    for thread in threads:
        thread.join()
    assert set(store.get(draft_id)["fields"]) == {"net_quantity", "shelf_life"}