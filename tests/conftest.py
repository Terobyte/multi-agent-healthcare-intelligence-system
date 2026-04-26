import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABRICKS_HOST", "https://test.cloud.databricks.com")
os.environ.setdefault("DATABRICKS_TOKEN", "dapi-test-token-not-real")
os.environ.setdefault("DATABRICKS_WAREHOUSE_ID", "test_wh_1234567890ab")
