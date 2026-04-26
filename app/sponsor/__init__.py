"""Sponsor stack — Databricks-criteria features that wrap existing endpoints.

All modules here are gated by env flags read at request time via :mod:`.flags`.
Importing this package has zero side effects: token-scrub extension lives in
:mod:`.scrub` as a passive ``PATTERNS`` list which ``app.main`` merges into
its own pattern list at startup.
"""
