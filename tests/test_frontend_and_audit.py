from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re


ROOT = Path(__file__).parents[1]


class Inspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.buttons_without_name = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])
        if tag == "button" and not any(key in values for key in ("aria-label", "title")):
            self.buttons_without_name.append(values.get("id", "text-button"))


def test_html_has_no_duplicate_ids_and_dashboard_references_exist():
    for path in ROOT.glob("*.html"):
        parser = Inspector()
        text = path.read_text(encoding="utf-8")
        parser.feed(text)
        duplicates = [item for item, count in Counter(parser.ids).items() if count > 1]
        assert not duplicates, f"duplicate ids in {path.name}: {duplicates}"
        if path.name == "dashboard.html":
            references = set(re.findall(r"\$\('([^']+)'\)", text))
            assert not references.difference(parser.ids)


def test_dashboard_has_real_daily_tools_and_localised_navigation():
    text = (ROOT / "dashboard.html").read_text(encoding="utf-8")
    for marker in ("id=\"habits\"", "id=\"journal\"", "id=\"family\"", "id=\"languageSelect\""):
        assert marker in text
    assert "ગુજરાતી" in text
    assert "हिन्दी" in text
    assert "X-CSRF-Token" in text


def test_only_gemini_provider_and_no_committed_secrets():
    source_files = [
        path for path in ROOT.rglob("*")
        if path.is_file() and ".git" not in path.parts
        and "__pycache__" not in path.parts and "tests" not in path.parts
    ]
    combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in source_files)
    assert "generativelanguage.googleapis.com" in combined
    forbidden = ["api.openai.com", "anthropic.com/v1", "api.groq.com", "sk-proj-"]
    assert not [value for value in forbidden if value.lower() in combined.lower()]
    assert not re.search(r"postgres(?:ql)?://[^\s:@]+:[^\s@]+@", combined, re.I)


def test_service_worker_never_caches_api_responses():
    text = (ROOT / "service-worker.js").read_text(encoding="utf-8")
    assert 'url.pathname.startsWith("/api/")' in text
    assert '"/dashboard"' not in text.split("const APP_SHELL", 1)[1].split("];", 1)[0]
