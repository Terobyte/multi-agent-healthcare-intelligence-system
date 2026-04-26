"""One-shot script that logs the TriageResponsesAgent via MLflow.

Run with:

    python scripts/sponsor/log_agent_bricks.py

Without ``MLFLOW_TRACKING_URI`` set, the run lands in ``./mlruns`` — that is
sufficient for the pitch since «agent is logged conforming to Mosaic AI Agent
Framework spec» holds without a remote tracking server.

If ``DATABRICKS_HOST`` + ``DATABRICKS_TOKEN`` + ``MLFLOW_TRACKING_URI`` are
set, the run lands in the workspace and ``databricks.agents.deploy()`` can be
called separately. We do NOT call deploy() from this script — workspace
permissions are flaky in hackathon settings and a missing UC catalog would
abort the demo prep.
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    try:
        import mlflow
    except ImportError:
        print(
            "mlflow is not installed. Install with `pip install mlflow databricks-agents`.",
            file=sys.stderr,
        )
        return 1

    from app.sponsor.agent_bricks import BRICKS_AVAILABLE, TriageResponsesAgent

    if not BRICKS_AVAILABLE:
        print(
            "mlflow.pyfunc.ResponsesAgent unavailable. Upgrade mlflow:\n"
            "    pip install --upgrade 'mlflow>=3.0' databricks-agents",
            file=sys.stderr,
        )
        return 2

    agent = TriageResponsesAgent()
    example = {"input": [{"role": "user", "content": "chest pain since morning"}]}

    pip_reqs = [
        "mlflow>=3.0",
        "databricks-agents",
        "databricks-sdk",
        "pydantic>=2",
    ]

    with mlflow.start_run(run_name="aarogyanet_triage_agent_bricks"):
        info = mlflow.pyfunc.log_model(
            name="triage_agent",
            python_model=agent,
            input_example=example,
            pip_requirements=pip_reqs,
        )
        print(f"logged model_uri={info.model_uri}")
        print(f"run_id={info.run_id}")

    if os.getenv("MLFLOW_REGISTERED_MODEL_NAME"):
        # Optional: register into Unity Catalog only when explicitly requested.
        # Skipped by default because UC write perms vary per workspace.
        target = os.environ["MLFLOW_REGISTERED_MODEL_NAME"]
        mlflow.register_model(model_uri=info.model_uri, name=target)
        print(f"registered as {target}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
