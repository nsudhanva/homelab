from io import BytesIO

from conftest import message, thread
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from jobs.config import Settings
from jobs.store import Store
from jobs.sync import evaluate
from jobs.web import create_app


def test_answer_flow_and_export(tmp_path, fake):
    settings = Settings(db_path=tmp_path / "jobs.db")
    store = Store(settings.db_path)
    store.save_thread(thread("t1", message(1)))
    assert evaluate(store, fake, workers=1) == (1, 0)
    assert store.pending() == []
    client = TestClient(create_app(settings, web_dist=tmp_path, extractor=lambda: fake))

    overview = client.get("/api/overview").json()
    assert overview["totals"]["companies"] == 1
    assert overview["companies"][0]["recruiters"][0]["email"] == "ann@acme.com"
    assert len(client.get("/api/questions").json()["open"]) == 1

    saved = client.post("/api/threads/t1/answer", json={"choice": "Not a job contact"}).json()
    assert saved["applied"] and saved["verdict"]["doubt"] is None
    assert fake.answers[-1]["choice"] == "Not a job contact"
    assert client.get("/api/overview").json()["totals"]["companies"] == 0
    assert client.get("/api/questions").json()["open"] == []
    assert client.post("/api/threads/t1/answer", json={}).status_code == 422

    xlsx = client.get("/api/export.xlsx")
    assert xlsx.status_code == 200
    assert load_workbook(BytesIO(xlsx.content)).sheetnames == [
        "Companies",
        "Recruiters",
        "Conversations",
        "Open questions",
    ]
    assert client.get("/api/nothing").status_code == 404
