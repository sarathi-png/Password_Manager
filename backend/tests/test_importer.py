from app.services.importer import (
    build_mapping,
    detect_format,
    parse_csv_bytes,
    parse_import,
    parse_xlsx_bytes,
)

CHROME_CSV = """name,url,username,password,note
Gmail,https://mail.google.com,user@example.com,hunter22,primary inbox
GitHub,https://github.com,octocat,ghpass,work account
"""

FIREFOX_CSV = """url,username,password,httpRealm,formActionOrigin,guid,timeCreated,timeLastUsed,timePasswordChanged
https://bank.example.com,john,firepass,Login,https://bank.example.com,,1,2,3
"""

BITWARDEN_CSV = """folder,favorite,type,name,notes,fields,reprompt,login_uri,login_username,login_password,login_totp
Work,0,login,Netflix,streaming,,0,https://netflix.com,bob,netpass,
"""

ONEPASSWORD_CSV = """Title,Url,Username,Password,Notes,OTPAuth
Twitter,https://twitter.com,@tweeter,twpass,two factor,
"""

GENERIC_CSV = """website,user,pwd,comments
example.com,alice,alicepw,nothing
"""


def test_detect_chrome():
    headers = ["name", "url", "username", "password", "note"]
    assert detect_format(headers) == "chrome"


def test_detect_firefox():
    headers = ["url", "username", "password", "httpRealm", "formActionOrigin"]
    assert detect_format(headers) == "firefox"


def test_detect_bitwarden():
    headers = ["folder", "favorite", "type", "name", "login_uri", "login_username", "login_password"]
    assert detect_format(headers) == "bitwarden"


def test_detect_onepassword():
    headers = ["Title", "Url", "Username", "Password", "Notes", "OTPAuth"]
    assert detect_format(headers) == "onepassword"


def test_detect_generic():
    headers = ["website", "user", "pwd"]
    assert detect_format(headers) == "generic"


def test_parse_chrome_csv():
    parsed = parse_csv_bytes(CHROME_CSV.encode("utf-8"))
    assert parsed.detected_format == "chrome"
    assert len(parsed.rows) == 2
    row = parsed.rows[0]
    assert row.title == "Gmail"
    assert row.url == "https://mail.google.com"
    assert row.username == "user@example.com"
    assert row.password == "hunter22"
    assert row.category == "email"


def test_parse_firefox_csv():
    parsed = parse_csv_bytes(FIREFOX_CSV.encode("utf-8"))
    assert parsed.detected_format == "firefox"
    assert parsed.rows[0].username == "john"
    assert parsed.rows[0].category == "banking"


def test_parse_bitwarden_csv():
    parsed = parse_csv_bytes(BITWARDEN_CSV.encode("utf-8"))
    assert parsed.detected_format == "bitwarden"
    assert parsed.rows[0].title == "Netflix"
    assert parsed.rows[0].category == "entertainment"


def test_parse_onepassword_csv():
    parsed = parse_csv_bytes(ONEPASSWORD_CSV.encode("utf-8"))
    assert parsed.detected_format == "onepassword"
    assert parsed.rows[0].username == "@tweeter"


def test_parse_generic_csv():
    parsed = parse_csv_bytes(GENERIC_CSV.encode("utf-8"))
    assert parsed.detected_format == "generic"
    assert parsed.rows[0].username == "alice"
    assert parsed.rows[0].category == "other"


def test_missing_password_column_raises():
    import pytest
    with pytest.raises(ValueError):
        build_mapping(["name", "url", "notes"])


def test_utf8_bom_tolerated():
    data = b"\xef\xbb\xbf" + CHROME_CSV.encode("utf-8")
    parsed = parse_csv_bytes(data)
    assert len(parsed.rows) == 2


def test_empty_rows_skipped():
    data = "name,url,username,password,note\nGmail,https://g.com,u,p,\n,\n,\n,\n"
    parsed = parse_csv_bytes(data.encode("utf-8"))
    assert len(parsed.rows) == 1


def test_xlsx_roundtrip():
    from openpyxl import Workbook
    import io

    wb = Workbook()
    ws = wb.active
    ws.append(["name", "url", "username", "password", "note"])
    ws.append(["Slack", "https://slack.com", "alice", "slackpw", "team"])
    buffer = io.BytesIO()
    wb.save(buffer)
    parsed = parse_xlsx_bytes(buffer.getvalue())
    assert parsed.detected_format == "chrome"
    assert parsed.rows[0].title == "Slack"
    assert parsed.rows[0].category == "work"


def test_parse_import_dispatches_by_extension():
    from openpyxl import Workbook
    import io

    wb = Workbook()
    ws = wb.active
    ws.append(["name", "url", "username", "password", "note"])
    ws.append(["X", "https://x.com", "u", "p", ""])
    buffer = io.BytesIO()
    wb.save(buffer)
    parsed = parse_import(buffer.getvalue(), "file.xlsx")
    assert parsed.rows[0].title == "X"


def test_legacy_xls_rejected():
    import pytest
    with pytest.raises(ValueError, match="[Ll]egacy"):
        parse_import(b"\xd0\xcf\x11\xe0", "old.xls")


def test_empty_file_rejected():
    import pytest
    with pytest.raises(ValueError, match="[Ee]mpty"):
        parse_csv_bytes(b"")