"""Fixtures for Playwright-based UI smoke tests.

Boots the real FastAPI app (vllm_playground.app.app) with a real uvicorn
server in a background thread on an ephemeral port -- Playwright drives an
actual browser and needs a real HTTP server to navigate to (unlike the
httpx-based ASGI TestClient used by tests/api). No real vLLM backend is
ever started; the server sits in its natural "not running" default state,
which is exactly what the UI sees on a fresh install before anyone has
started a model.
"""

import socket
import threading
import time

import pytest
import uvicorn

import vllm_playground.app as app_module


def _free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="session")
def live_server_url():
    """Serve the real app on a background thread for the whole test session.

    Uses ``app_module.app`` directly (no ``uvicorn.run``'s own signal
    handling) so it can be torn down cleanly. Lifespan startup is skipped by
    using ``uvicorn.Server`` with the default lifespan="on" -- that's fine
    here since the UI smoke tests want the app in its normal boot state.
    """
    port = _free_port()
    config = uvicorn.Config(app_module.app, host="127.0.0.1", port=port, log_level="warning", lifespan="off")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 10
    while not getattr(server, "started", False) and time.time() < deadline:
        time.sleep(0.05)

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=5)
