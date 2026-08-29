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


def test_account_return_path_is_restricted_to_private_pages():
    text = (ROOT / "account.html").read_text(encoding="utf-8")
    assert "['/dashboard','/chat'].includes(params.get('next'))" in text
    assert "location.href=destination" in text


def test_account_exposes_explicit_session_duration_choice():
    text = (ROOT / "account.html").read_text(encoding="utf-8")
    assert 'id="signupRemember"' in text
    assert 'id="loginRemember"' in text
    assert "remember:document.getElementById('loginRemember').checked" in text
    assert "remember:document.getElementById('signupRemember').checked" in text
    assert "beforeunload" not in text and "sendBeacon" not in text


def test_chat_has_working_attachment_controls_and_multipart_flow():
    text = (ROOT / "chat.html").read_text(encoding="utf-8")
    for marker in (
        'id="attachButton"', 'id="fileInput"', 'id="attachmentTray"',
        "new FormData()", "body.append('attachments'", "instanceof FormData",
        "message.attachments", 'id="chatMode"', 'id="uploadStatus"',
        "XMLHttpRequest()", "xhr.upload.onprogress", "request_id",
        "clipboardData", "dataTransfer", "quick-actions", 'id="taskDialog"',
        'id="reminderDialog"', "Save task", "Set reminder",
    ):
        assert marker in text
    assert "application/pdf,image/jpeg,image/png,image/webp" in text
    assert "Simpler" in text and "Deeper" in text and "Quiz me" in text


def test_chat_history_titles_and_right_aligned_user_messages_are_wired():
    text = (ROOT / "chat.html").read_text(encoding="utf-8")
    for marker in (
        ".message.user{grid-template-columns:minmax(0,76%) 34px",
        "conversation-copy",
        "conversation-preview",
        "function conversationTitle(text)",
        "function attachmentConversationTitle(mode,files)",
        "firstUserMessage",
        "el.chatTitle.textContent=active.title",
    ):
        assert marker in text


def test_chat_history_sidebar_is_on_the_right_across_breakpoints():
    text = (ROOT / "chat.html").read_text(encoding="utf-8")
    for marker in (
        'grid-template-columns:minmax(0,1fr) var(--sidebar-width)',
        'grid-template-areas:"main sidebar"',
        '.sidebar{grid-area:sidebar',
        'border-left:1px solid var(--line)',
        '.main{grid-area:main',
        'inset:0 0 0 auto',
        'transform:translateX(103%)',
        '.mobile-menu{display:grid;grid-column:3;grid-row:1}',
    ):
        assert marker in text
    assert 'border-right:1px solid var(--line)' not in text
    assert 'transform:translateX(-103%)' not in text


def test_memory_view_edit_and_global_logout_controls_are_wired():
    text = (ROOT / "dashboard.html").read_text(encoding="utf-8")
    for marker in (
        'id="memoryDialog"',
        'id="memoryEditForm"',
        'id="memoryEditLabel"',
        'id="memoryEditContent"',
        "View & edit",
        "function openMemory(memory)",
        "'/api/memories/'+id",
        'id="logoutAllButton"',
        "'/api/logout-all'",
    ):
        assert marker in text


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
    assert 'saathi-shell-v5' in text


def test_interactive_pages_have_visible_keyboard_focus():
    for name in ("account.html", "chat.html", "dashboard.html", "saathi.html"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert ":focus-visible" in text, name
    assert ":focus-visible" in (ROOT / "public.css").read_text(encoding="utf-8")


def test_landing_navigation_and_faq_expose_accessible_state():
    text = (ROOT / "saathi.html").read_text(encoding="utf-8")
    assert 'aria-controls="mobileMenu"' in text
    assert "setAttribute('aria-expanded'" in text
    assert "faq-answer-" in text
    assert '<span class="card-status">Visible to you</span>' in text


def test_launch_readiness_files_are_wired():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    render = (ROOT / "render.yaml").read_text(encoding="utf-8")
    smoke = (ROOT / "scripts" / "smoke_test.py").read_text(encoding="utf-8")
    assert "pytest -q" in workflow
    assert "scripts/check_javascript.sh" in workflow
    assert "healthCheckPath: /api/health" in render
    assert "sync: false" in render
    assert '"/app.py"' in smoke and '"/api/health"' in smoke
    assert 'EXPECTED_RELEASE = "2026-08-29-conversation-security"' in smoke


def test_dependencies_are_reproducible_and_scheduled_for_review():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    development = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    dependabot = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert all("==" in line for line in requirements.splitlines() if line.strip())
    assert "pytest==" in development
    assert "package-ecosystem: pip" in dependabot
    assert "package-ecosystem: github-actions" in dependabot
