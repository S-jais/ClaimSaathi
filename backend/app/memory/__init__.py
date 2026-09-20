"""
app/memory
Institutional memory layer with Cognee integration.
"""
from app.memory.cognee_client import CogneeClient, get_cognee_client

__all__ = ["CogneeClient", "get_cognee_client"]
