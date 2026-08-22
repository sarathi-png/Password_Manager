def test_employee_cannot_create_entry(client, employee_headers):
    resp = client.post(
        "/api/entries",
        json={"title": "Hack", "url": "https://x.com", "username": "u", "password": "p"},
        headers=employee_headers,
    )
    assert resp.status_code == 403


def test_employee_cannot_update_entry(client, employee_headers, sample_entry):
    resp = client.put(
        f"/api/entries/{sample_entry['id']}",
        json={**sample_entry, "password": "changed"},
        headers=employee_headers,
    )
    assert resp.status_code == 403


def test_employee_cannot_delete_entry(client, employee_headers, sample_entry):
    resp = client.delete(f"/api/entries/{sample_entry['id']}", headers=employee_headers)
    assert resp.status_code == 403


def test_employee_cannot_manage_users(client, employee_headers):
    resp = client.get("/api/users", headers=employee_headers)
    assert resp.status_code == 403


def test_employee_cannot_import(client, employee_headers):
    resp = client.post("/api/import/preview", files={"file": ("p.csv", b"x", "text/csv")}, headers=employee_headers)
    assert resp.status_code == 403


def test_employee_cannot_export(client, employee_headers):
    resp = client.get("/api/export", headers=employee_headers)
    assert resp.status_code == 403


def test_employee_cannot_read_audit(client, employee_headers):
    resp = client.get("/api/audit", headers=employee_headers)
    assert resp.status_code == 403


def test_employee_can_read_entries(client, employee_headers, sample_entry):
    resp = client.get("/api/entries", headers=employee_headers)
    assert resp.status_code == 200
    assert any(e["id"] == sample_entry["id"] for e in resp.json())


def test_employee_can_read_single_entry(client, employee_headers, sample_entry):
    resp = client.get(f"/api/entries/{sample_entry['id']}", headers=employee_headers)
    assert resp.status_code == 200
    assert resp.json()["password"] == "s3cret-Ä"