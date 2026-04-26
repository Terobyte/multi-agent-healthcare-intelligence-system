import time

from databricks import sql
from databricks.sql.exc import OperationalError, ServerOperationError

from app.settings import settings


def warehouse_query(query: str, params: list | None = None, _retries: int = 1):
    """Execute a SQL query against the configured Databricks SQL warehouse.

    Returns rows for SELECTs (cursor.description present), None for DML.
    Retries once on cold-start / transient connection errors so the second
    attempt hits an already-warm warehouse instead of bubbling the timeout.
    """
    last_exc: Exception | None = None
    for attempt in range(_retries + 1):
        try:
            with sql.connect(
                server_hostname=settings.databricks_host.replace("https://", ""),
                http_path=f"/sql/1.0/warehouses/{settings.databricks_warehouse_id}",
                access_token=settings.databricks_token,
                session_configuration={"STATEMENT_TIMEOUT": "30"},
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params or [])
                    if cur.description:
                        return cur.fetchall()
                    return None
        except (ServerOperationError, OperationalError) as e:
            last_exc = e
            if attempt < _retries:
                time.sleep(2)
                continue
            raise
    raise last_exc  # unreachable; satisfies type-checker
