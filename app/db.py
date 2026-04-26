import time
from urllib.parse import urlparse

from databricks import sql
from databricks.sql.exc import OperationalError, ServerOperationError

from app.settings import settings


def _server_hostname(host: str) -> str:
    """Strip scheme + trailing slash from a configured Databricks host URL.

    The previous `replace("https://", "")` only handled one scheme and left
    trailing slashes intact — `https://x.cloud.databricks.com/` would yield
    `x.cloud.databricks.com/`, which the databricks SQL driver rejects with a
    cryptic DNS error. urlparse handles `http://`, `https://`, and bare hosts;
    we then strip any leading/trailing slashes for safety.
    """
    parsed = urlparse(host)
    hostname = parsed.hostname or parsed.path or host
    return hostname.strip("/")


def warehouse_query(query: str, params: list | None = None, _retries: int = 1):
    """Execute a SQL query against the configured Databricks SQL warehouse.

    Returns rows for SELECTs (cursor.description present), None for DML.
    Retries once on cold-start / transient connection errors so the second
    attempt hits an already-warm warehouse instead of bubbling the timeout.
    """
    for attempt in range(_retries + 1):
        try:
            with sql.connect(
                server_hostname=_server_hostname(settings.databricks_host),
                http_path=f"/sql/1.0/warehouses/{settings.databricks_warehouse_id}",
                access_token=settings.databricks_token,
                session_configuration={"STATEMENT_TIMEOUT": "30"},
                _socket_timeout=45,
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params or [])
                    if cur.description:
                        return cur.fetchall()
                    return None
        except (ServerOperationError, OperationalError, OSError):
            if attempt < _retries:
                time.sleep(2)
                continue
            raise
    # Loop is exhaustive: either we returned, retried again, or re-raised.
    # No trailing `raise last_exc` — that was unreachable dead code.
