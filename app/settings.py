import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    databricks_host: str
    databricks_token: str
    databricks_warehouse_id: str

    class Config:
        env_file = ".env"


settings = Settings()

# pydantic-settings reads .env into the model but does NOT export to os.environ.
# mlflow.deployments / databricks-sdk read auth from os.environ, so forward —
# otherwise local `uvicorn app.main:app` (no --env-file) silently fails to auth
# on first /health probe. setdefault preserves Render-set env vars in deploy.
os.environ.setdefault("DATABRICKS_HOST", settings.databricks_host)
os.environ.setdefault("DATABRICKS_TOKEN", settings.databricks_token)
