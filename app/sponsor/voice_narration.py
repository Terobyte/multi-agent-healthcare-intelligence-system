"""Fish Audio TTS narration — Hindi/Urdu output for the patient handoff.

Architecture (per ``SPONSOR_STACK_PLAN.md`` v2 §Feature 3):

- **Path A (default):** narrate from a pre-baked MP3 file in ``_demo/``. Zero
  live API calls during the demo. Files are produced offline by adapting
  ``~/Desktop/Projects/Active/ai_hack/fishaudio/scripts/e2e-test.mjs``.
- **Path B (live, opt-in):** proxy to a Node sidecar running the
  ``@fishaudio-engine/core`` package over HTTP at ``localhost:9301/narrate``.
  The sidecar MUST call ``stream(asyncIter)`` not ``speak(text)`` — ``speak``
  accumulates the full sentence before sending and ruins TTFB.

Both paths return ``(media_type, bytes_iter)`` so a FastAPI route can wrap
them in a ``StreamingResponse``.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Final

from app.sponsor._demo_lookup import voice_path
from app.sponsor.flags import flags


logger = logging.getLogger(__name__)


# Deterministic templates — no LLM in the loop, so demo-day output is byte-for-
# byte identical across runs. ``{hospital_name}`` and ``{eta}`` are the only
# substitutions; both come from /book's response, not user input.
HI_TEMPLATE: Final[str] = (
    "आपके लिए {hospital_name} में बिस्तर आरक्षित है। "
    "एम्बुलेंस {eta} मिनट में पहुंचेगी।"
)
UR_TEMPLATE: Final[str] = (
    "آپ کے لیے {hospital_name} میں بستر محفوظ ہے۔ "
    "ایمبولینس {eta} منٹ میں پہنچے گی۔"
)
EN_TEMPLATE: Final[str] = (
    "A bed has been reserved for you at {hospital_name}. "
    "An ambulance will arrive in {eta} minutes."
)


def render_template(lang: str, hospital_name: str, eta_min: int) -> str:
    template = {"hi": HI_TEMPLATE, "ur": UR_TEMPLATE, "en": EN_TEMPLATE}.get(
        lang, EN_TEMPLATE
    )
    return template.format(hospital_name=hospital_name, eta=eta_min)


_SIDECAR_URL: Final[str] = "http://127.0.0.1:9301/narrate"
_FILE_CHUNK_BYTES: Final[int] = 16 * 1024


def narrate(
    *, demo_id: str, lang: str, hospital_name: str = "", eta_min: int = 0
) -> tuple[str, Iterator[bytes]]:
    """Return (media_type, byte iterator) for the narration audio.

    Demo-time precedence:

    1. ``SAFE_DEMO=1``                     → always pre-baked file
    2. Pre-baked file exists for demo_id   → file
    3. ``SPONSOR_VOICE`` and sidecar up    → live stream from sidecar
    4. Otherwise                           → :class:`VoiceUnavailable`

    Splitting precedence this way means a missing FISH_API_KEY or sidecar
    crash silently degrades to the file path — the demo never goes silent
    on stage.
    """
    file_iter = _try_file(demo_id, lang)
    if flags.SAFE_DEMO and file_iter is not None:
        return ("audio/mpeg", file_iter)

    if file_iter is not None:
        return ("audio/mpeg", file_iter)

    if flags.SPONSOR_VOICE:
        text = render_template(lang, hospital_name or "the hospital", eta_min)
        live = _try_sidecar(text, lang)
        if live is not None:
            return ("audio/mpeg", live)

    raise VoiceUnavailable(
        f"no pre-baked file for demo_id={demo_id!r} lang={lang!r} and live path off"
    )


def _try_file(demo_id: str, lang: str) -> Iterator[bytes] | None:
    path: Path | None = voice_path(demo_id, lang)
    if path is None or not path.exists():
        return None
    return _read_chunks(path)


def _read_chunks(path: Path) -> Iterator[bytes]:
    def _gen() -> Iterator[bytes]:
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(_FILE_CHUNK_BYTES)
                if not chunk:
                    return
                yield chunk

    return _gen()


def _try_sidecar(text: str, lang: str) -> Iterator[bytes] | None:
    """POST to the Node sidecar; on any error return None so the caller
    can decide whether to surface a 503 or fall through to a different path.
    """
    try:
        import httpx  # local import: httpx is already a backend dep
    except ImportError:
        logger.warning("httpx unavailable; sidecar narration disabled")
        return None

    try:
        resp = httpx.post(
            _SIDECAR_URL,
            json={"text": text, "lang": lang},
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        logger.warning("voice sidecar unreachable: %s", type(exc).__name__)
        return None

    if resp.status_code != 200:
        logger.warning("voice sidecar returned %s", resp.status_code)
        return None

    body: bytes = resp.content
    return iter([body])


class VoiceUnavailable(RuntimeError):
    """Raised when neither pre-baked file nor live sidecar can serve audio.

    Routes should map this to a 503 with a JSON body — never let it leak as
    a 500 because that's the difference between «retry the API» and «assume
    the whole feature is broken» for the frontend.
    """
