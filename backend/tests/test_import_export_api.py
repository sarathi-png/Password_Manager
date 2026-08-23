import io

CHROME_CSV = """name,url,username,password,note
Gmail,https://mail.google.com,user@example.com,hunter22,primary
GitHub,https://github.com,octocat,ghpass,work
"""


def test_preview_import(client, admin_headers):
    resp = client.post(
        "/api/import/preview",
        files={"file": ("chrome.csv", CHROME_CSV.encode("utf-8"), "text/csv")},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["detected_format"] == "chrome"
    assert body["total_rows"] == 2
    assert body["mapping"]["password"] == "password"
    assert body["sample"][0]["title"] == "Gmail"


def test_preview_bad_file(client, admin_headers):
    resp = client.post(
        "/api/import/preview",
        files={"file": ("bad.csv", b"nothing,here\n", "text/csv")},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_confirm_import_then_list(client, admin_headers):
    resp = client.post(
        "/api/import/confirm",
        files={"file": ("chrome.csv", CHROME_CSV.encode("utf-8"), "text/csv")},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["imported"] == 2

    resp = client.get("/api/entries", headers=admin_headers)
    titles = {e["title"] for e in resp.json()}
    assert "Gmail" in titles and "GitHub" in titles


def test_confirm_import_skips_duplicates(client, admin_headers):
    # explicit skip mode: old behavior via dedup_mode=title_url + skip_duplicates=true
    resp = client.post(
        "/api/import/confirm",
        files={"file": ("chrome.csv", CHROME_CSV.encode("utf-8"), "text/csv")},
        data={"skip_duplicates": "true", "dedup_mode": "title_url"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["imported"] == 0
    assert resp.json()["skipped_duplicates"] == 2


def test_confirm_import_marks_duplicates_not_skips(client, admin_headers):
    # default new behavior: import all (dedup_mode=none) and mark as duplicate
    resp = client.post(
        "/api/import/confirm",
        files={"file": ("chrome.csv", CHROME_CSV.encode("utf-8"), "text/csv")},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    # with dedup_mode=none, same file is imported again and flagged as duplicate
    assert resp.json()["imported"] == 2
    assert resp.json()["marked_duplicates"] == 2


def test_export_csv(client, admin_headers):
    resp = client.get("/api/export", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    text = resp.content.decode("utf-8-sig")
    assert "name,url,username,password,note" in text
    assert "hunter22" in text


def test_export_xlsx(client, admin_headers):
    resp = client.get("/api/export?format=xlsx", headers=admin_headers)
    assert resp.status_code == 200
    assert "spreadsheet" in resp.headers["content-type"]


def test_export_returns_decrypted_values(client, admin_headers):
    resp = client.get("/api/export", headers=admin_headers)
    text = resp.content.decode("utf-8-sig")
    assert "hunter22" in text
    assert "v1:" not in text


def test_xlsx_import_roundtrip(client, admin_headers):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["name", "url", "username", "password", "note"])
    ws.append(["Slack", "https://slack.com", "alice", "slackpw", "team"])
    buffer = io.BytesIO()
    wb.save(buffer)
    resp = client.post(
        "/api/import/confirm",
        files={"file": ("vault.xlsx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["imported"] == 1


def test_audit_log_records_actions(client, admin_headers):
    resp = client.get("/api/audit?limit=100", headers=admin_headers)
    assert resp.status_code == 200
    actions = {a["action"] for a in resp.json()}
    assert "login.success" in actions
    assert "import.run" in actions
    assert "export.run" in actions