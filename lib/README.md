# lib

Shared library files — reusable modules, utilities, data loaders, and adapters.

Suggested layout (fill in as we build):

- `data/` — loaders/parsers for hospital datasets (NHRR, ABDM HFR, state portals)
- `agents/` — agent prompts, tools, schemas
- `voice/` — TTS/STT adapters (Bhashini, Sarvam, Deepgram, Fish Audio)
- `geo/` — distance, routing, isochrone helpers
- `predict/` — bed-availability forecasting models

Keep modules small and single-purpose so any teammate can drop one in without reading the rest.
