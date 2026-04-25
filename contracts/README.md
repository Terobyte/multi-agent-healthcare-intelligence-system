# Contracts

JSON contracts shared by all 4 owners. **This is the only place where everyone touches the same code.**

Pydantic schemas + mock JSON files. Owners import from here:

```python
from contracts.schemas import TriageOutput, PredictorOutput, RouterOutput, TransferOutput, VoiceOutput, SupervisorResponse
```

## Files

| File | Owner of contract | Owner of consuming code |
|---|---|---|
| `schemas.py` | Tero (defines) | All 4 (imports) |
| `triage_output.json` | Mubarak (mock) | Tero (consumes) |
| `predictor_output.json` | Mian (mock) | Tero (consumes) |
| `router_output.json` | Tero (mock) | Tero (consumes) |
| `transfer_output.json` | Tero (mock) | Tero, Arushi (consumes) |
| `voice_output.json` | Tero (mock) | Tero (consumes) |
| `supervisor_response.json` | Tero (mock) | Arushi (consumes) |

## Rule

**If you change a schema in `schemas.py`, you must update your mock file in the same commit.** Otherwise other people's mock-based dev breaks.
