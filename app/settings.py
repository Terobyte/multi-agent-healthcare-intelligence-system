import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Optional so the process starts on Render before dashboard env vars are set.
    # When all three are present, os.environ.setdefault below forwards them to
    # mlflow/databricks-sdk which read auth exclusively from os.environ.
    databricks_host: Optional[str] = None
    databricks_token: Optional[str] = None
    databricks_warehouse_id: Optional[str] = None


settings = Settings()

# pydantic-settings reads .env into the model but does NOT export to os.environ.
# mlflow.deployments / databricks-sdk read auth from os.environ, so forward —
# otherwise local `uvicorn app.main:app` (no --env-file) silently fails to auth
# on first /health probe. setdefault preserves Render-set env vars in deploy.
# Skip None values so a missing var doesn't clobber an already-set os.environ entry.
if settings.databricks_host:
    os.environ.setdefault("DATABRICKS_HOST", settings.databricks_host)
if settings.databricks_token:
    os.environ.setdefault("DATABRICKS_TOKEN", settings.databricks_token)
if settings.databricks_warehouse_id:
    os.environ.setdefault("DATABRICKS_WAREHOUSE_ID", settings.databricks_warehouse_id)
