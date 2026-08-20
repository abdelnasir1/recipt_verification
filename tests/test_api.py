from fastapi.testclient import TestClient

from app.main import app, celery_app


def test_verify_storage_queues_work_without_running_ocr(monkeypatch):
    queued = {}

    def send_task(name, args):
        queued["name"] = name
        queued["args"] = args

    monkeypatch.setattr(celery_app, "send_task", send_task)

    response = TestClient(app).post(
        "/verify/storage",
        json={"image_url": "receipts/payment.jpg", "payment_id": "payment-uuid"},
    )

    assert response.status_code == 200
    assert response.content == b""
    assert queued == {
        "name": "app.tasks.verify_receipt_task",
        "args": ["receipts/payment.jpg", "payment-uuid"],
    }


def test_verify_storage_requires_only_the_two_contract_fields():
    response = TestClient(app).post(
        "/verify/storage",
        json={"image_url": "receipts/payment.jpg"},
    )

    assert response.status_code == 422