"""Playwright UI smoke tests.

Loads the real vLLM Playground frontend (served by the real FastAPI app, no
vLLM backend running behind it -- exactly the state a fresh install is in)
and exercises the main navigation, catching JS syntax errors and broken DOM
wiring that unit/API tests can't see.

Note: the app opens persistent WebSocket connections (chat + Omni) as soon
as the page loads, which never go idle. That means Playwright's
``wait_until="networkidle"`` never resolves for this app -- we use the
default ``"load"`` wait instead and then wait for a concrete selector to
appear, which is both correct and much faster.
"""

import pytest

IGNORED_CONSOLE_SUBSTRINGS = (
    # Favicon/asset 404s are cosmetic and unrelated to app logic; the nav
    # icons themselves already have onerror="this.style.display='none'".
    "favicon",
    "404",
)


def _collect_console_errors(page):
    errors = []

    def _on_console(msg):
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", _on_console)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    return errors


def _real_errors(errors):
    return [e for e in errors if not any(sub in e.lower() for sub in IGNORED_CONSOLE_SUBSTRINGS)]


def test_page_loads_without_js_errors(page, live_server_url):
    errors = _collect_console_errors(page)

    page.goto(live_server_url)
    page.wait_for_selector("#vllm-server-view")

    assert page.title() != ""
    assert page.locator("#vllm-server-view").is_visible()
    assert _real_errors(errors) == []


def test_default_view_is_vllm_server(page, live_server_url):
    page.goto(live_server_url)
    page.wait_for_selector("#vllm-server-view")

    assert "active" in (page.locator('.nav-item[data-view="vllm-server"]').get_attribute("class") or "")
    assert page.locator("#vllm-server-view").is_visible()


@pytest.mark.parametrize(
    "view_name",
    ["instances", "observability", "mcp-config", "settings", "guidellm", "tutorials"],
)
def test_can_switch_to_each_main_view(page, live_server_url, view_name):
    errors = _collect_console_errors(page)
    page.goto(live_server_url)
    page.wait_for_selector("#vllm-server-view")

    page.click(f'.nav-item[data-view="{view_name}"]')
    page.wait_for_timeout(200)

    view = page.locator(f"#{view_name}-view")
    assert view.is_visible(), f"Expected #{view_name}-view to become visible after clicking its nav item"
    assert _real_errors(errors) == []


def test_settings_view_shows_container_image_catalog_section(page, live_server_url):
    page.goto(live_server_url)
    page.wait_for_selector("#vllm-server-view")
    page.click('.nav-item[data-view="settings"]')
    page.wait_for_timeout(300)

    settings_view = page.locator("#settings-view")
    assert settings_view.is_visible()
    # Settings content is rendered client-side (empty container in the HTML
    # shell) -- assert it actually got populated rather than staying blank.
    assert settings_view.inner_html().strip() != ""


def test_mcp_servers_view_renders_without_crashing(page, live_server_url):
    errors = _collect_console_errors(page)
    page.goto(live_server_url)
    page.wait_for_selector("#vllm-server-view")

    page.click('.nav-item[data-view="mcp-config"]')
    page.wait_for_timeout(300)

    assert page.locator("#mcp-config-view").is_visible()
    assert _real_errors(errors) == []
