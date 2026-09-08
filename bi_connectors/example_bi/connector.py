"""Reference BI connector that reads asset metadata from a local JSON file.

This connector exercises the full BI test path (bi_connection + bi_metadata)
without any external vendor dependency: it loads a ``sample_assets.json`` file
bundled with the connector and returns its contents as BI asset dicts.

Point ``assets_path`` (in credentials.json connect_args) at a different JSON
file to feed arbitrary asset data through the same path.
"""

from __future__ import annotations

import json
import os
from typing import List

from bi_connectors._base.connector import Connector as _BaseConnector

_DEFAULT_ASSETS_PATH = os.path.join(os.path.dirname(__file__), "sample_assets.json")


class Connector(_BaseConnector):
    """BI connector backed by a local JSON file of asset dicts."""

    def setup_connection(self) -> None:
        """Resolve the assets file path from credentials (or the default)."""
        self._assets_path = self.credentials.get("assets_path", _DEFAULT_ASSETS_PATH)

    def close_connection(self) -> None:
        """No-op — there is no live connection or client to close."""

    def fetch_metadata(self, limit: int, offset: int) -> List[dict]:
        """Return a page of BI assets loaded from the local JSON file.

        Returns an empty list if the file is missing or does not contain a
        valid JSON array.
        """
        try:
            with open(self._assets_path) as f:
                assets = json.load(f)
        except (OSError, ValueError):
            return []
        if not isinstance(assets, list):
            return []
        return assets[offset:offset + limit]
