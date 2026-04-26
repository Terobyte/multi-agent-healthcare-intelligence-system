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
# Hard cap on streamed narration response size. If the sidecar is compromised
# or buggy and returns an unbounded stream, we abort once this threshold is
# hit instead of letting an attacker pin the worker on memory/socket time.
MAX_NARRATE_BYTES = 10 * 1024 * 1024


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
    if flags.SAFE_DEMO:
        # SAFE_DEMO is a hard kill-switch: we must never hit a live API call
        # in this mode, even when the pre-baked file is missing. Surfacing
        # VoiceUnavailable here lets the route map this to a clean 503.
        if file_iter is not None:
            return ("audio/mpeg", file_iter)
        raise VoiceUnavailable(
            f"SAFE_DEMO=1 and no pre-baked file for demo_id={demo_id!r} lang={lang!r}"
        )

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
        try:
            fh = path.open("rb")
        except OSError as exc:
            # Disk error / file vanished between exists()-check and open().
            # Yield nothing rather than letting OSError propagate as a 500.
            logger.warning("voice file read failed for %s: %s", path, exc)
            return
        try:
            while True:
                try:
                    chunk = fh.read(_FILE_CHUNK_BYTES)
                except OSError as exc:
                    logger.warning("voice file mid-read failed for %s: %s", path, exc)
                    return
                if not chunk:
                    return
                yield chunk
        finally:
            try:
                fh.close()
            except OSError:
                pass

    return _gen()


def _try_sidecar(text: str, lang: str) -> Iterator[bytes] | None:
    """POST to the Node sidecar; on any error return None so the caller
    can decide whether to surface a 503 or fall through to a different path.

    Streams chunks as they arrive (httpx.stream + iter_bytes) so we don't
    buffer the full audio body in memory — a single ~10s narration is small,
    but an upstream regression that returns an unbounded stream would otherwise
    pin the worker. We also stop after MAX_NARRATE_BYTES to bound exposure
    if the sidecar is compromised.
    """
    try:
        import httpx  # local import: httpx is already a backend dep
    except ImportError:
        logger.warning("httpx unavailable; sidecar narration disabled")
        return None

    def _streamer() -> Iterator[bytes]:
        try:
            with httpx.stream(
                "POST",
                _SIDECAR_URL,
                json={"text": text, "lang": lang},
                timeout=10.0,
            ) as resp:
                if resp.status_code != 200:
                    logger.warning("voice sidecar returned %s", resp.status_code)
                    return
                streamed = 0
                for chunk in resp.iter_bytes():
                    if not chunk:
                        continue
                    streamed += len(chunk)
                    if streamed >= MAX_NARRATE_BYTES:
                        logger.warning(
                            "voice sidecar response exceeded %d bytes (too_large); aborting stream",
                            MAX_NARRATE_BYTES,
                        )
                        return
                    yield chunk
        except httpx.HTTPError as exc:
            logger.warning("voice sidecar unreachable: %s", type(exc).__name__)
            return

    return _streamer()


class VoiceUnavailable(RuntimeError):
    """Raised when neither pre-baked file nor live sidecar can serve audio.

    Routes should map this to a 503 with a JSON body — never let it leak as
    a 500 because that's the difference between «retry the API» and «assume
    the whole feature is broken» for the frontend.
    """
