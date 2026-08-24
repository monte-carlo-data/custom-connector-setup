"""Datadog telemetry connector.

Worked example of the telemetry capability contracts against a real vendor
API. Advertises both capabilities in ``manifest.json``:

- ``fetch_logs``      → Datadog Logs Search API (v2)
- ``fetch_telemetry`` → Datadog Metrics Query API (v1)

Both are read-only, single-page, synchronous calls. Nothing is cached or
stored by the connector.
"""

import re
from datetime import datetime, timezone
from typing import List

from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.metrics_api import MetricsApi
from datadog_api_client.v2.api.logs_api import LogsApi
from datadog_api_client.v2.model.logs_list_request import LogsListRequest
from datadog_api_client.v2.model.logs_list_request_page import LogsListRequestPage
from datadog_api_client.v2.model.logs_query_filter import LogsQueryFilter
from datadog_api_client.v2.model.logs_sort import LogsSort

# Datadog log search has no regex operator, so `search_regex` is applied to the
# page after it comes back. Severity and the resource scope *are* pushed down.
_SAFE_SEVERITY = re.compile(r"[\w.-]+")

_RESOURCE_PLACEHOLDER = "{resource_id}"
_DEFAULT_LOG_QUERY_TEMPLATE = '@mcd.resource_id:"{resource_id}"'


def _render(template: str, resource_id: str) -> str:
    """Substitute the resource into a query template.

    Plain string replacement rather than ``str.format`` — Datadog query syntax
    is full of literal braces (``avg:foo{tag:bar}``) that ``format`` would try
    to interpret as fields.
    """
    return template.replace(_RESOURCE_PLACEHOLDER, resource_id)


class Connector:
    credentials: dict

    ########################################
    # Connection Related Methods
    ########################################

    def setup_connection(self) -> None:
        configuration = Configuration()
        configuration.api_key["apiKeyAuth"] = self.credentials["api_key"]
        configuration.api_key["appKeyAuth"] = self.credentials["application_key"]
        configuration.server_variables["site"] = self.credentials.get("site", "datadoghq.com")
        self.api_client = ApiClient(configuration)

        # How a Monte Carlo resource maps onto a Datadog query. Overridable so
        # the same connector works whatever tag the customer indexes runs under
        # (e.g. '@task_arn:"{resource_id}"' or 'service:{resource_id}').
        self.log_query_template = self.credentials.get(
            "log_query_template", _DEFAULT_LOG_QUERY_TEMPLATE
        )
        # Metric queries to answer fetch_telemetry with, each templated on the
        # resource. Keyed by the name reported back to Monte Carlo.
        self.metric_queries = self.credentials.get("metric_queries", {})

    def close_connection(self) -> None:
        self.api_client.close()

    ########################################
    # Logs Capability
    ########################################

    def fetch_logs(
        self,
        resource_id: str,
        start_time: datetime,
        end_time: datetime,
        search_regex: str | None = None,
        severity: List[str] | None = None,
        page_size: int = 100,
        cursor: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict:
        query_parts = [_render(self.log_query_template, resource_id)]
        if severity:
            invalid = [value for value in severity if not _SAFE_SEVERITY.fullmatch(value)]
            if invalid:
                raise ValueError(
                    f"severity values may contain only letters, numbers, _, ., or -: {invalid}"
                )
            query_parts.append(f"status:({' OR '.join(severity)})")

        page = LogsListRequestPage(limit=page_size)
        if cursor:
            page.cursor = cursor

        request = LogsListRequest(
            filter=LogsQueryFilter(
                _from=start_time.isoformat(),
                to=end_time.isoformat(),
                query=" AND ".join(query_parts),
            ),
            page=page,
            sort=LogsSort.TIMESTAMP_ASCENDING,
        )
        response = LogsApi(self.api_client).list_logs(body=request)

        pattern = re.compile(search_regex) if search_regex else None
        items = []
        for log in response.data or []:
            attributes = log.attributes
            timestamp = getattr(attributes, "timestamp", None)
            if not isinstance(timestamp, datetime):
                continue
            message = attributes.message if isinstance(attributes.message, str) else ""
            if pattern and not pattern.search(message):
                continue
            items.append(
                {
                    "timestamp": timestamp.isoformat(),
                    "severity": attributes.status if isinstance(attributes.status, str) else None,
                    "message": message,
                }
            )

        return {"items": items, "next_cursor": self._next_log_cursor(response)}

    @staticmethod
    def _next_log_cursor(response) -> str | None:
        """Pull Datadog's continuation token out of the response metadata."""
        page = getattr(getattr(response, "meta", None), "page", None)
        after = getattr(page, "after", None)
        return after if isinstance(after, str) and after else None

    ########################################
    # Telemetry Capability
    ########################################

    def fetch_telemetry(
        self,
        resource_id: str,
        start_time: datetime,
        end_time: datetime,
        names: List[str] | None = None,
        page_size: int = 100,
        cursor: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict:
        requested = names or list(self.metric_queries)
        unknown = [name for name in requested if name not in self.metric_queries]
        if unknown:
            raise ValueError(
                f"No metric query configured for {unknown}. "
                f"Add it to 'metric_queries' in credentials.json. "
                f"Configured: {sorted(self.metric_queries)}"
            )

        metrics_api = MetricsApi(self.api_client)
        items = []
        for name in requested:
            response = metrics_api.query_metrics(
                _from=int(start_time.timestamp()),
                to=int(end_time.timestamp()),
                query=_render(self.metric_queries[name], resource_id),
            )
            for series in response.series or []:
                attributes = {
                    key: value
                    for key, value in (("unit", self._unit(series)), ("scope", series.get("scope")))
                    if value
                }
                for point in series.get("pointlist") or []:
                    timestamp_ms, value = point[0], point[1]
                    if value is None:
                        continue
                    items.append(
                        {
                            "timestamp": datetime.fromtimestamp(
                                timestamp_ms / 1000, tz=timezone.utc
                            ).isoformat(),
                            "name": name,
                            "value": value,
                            "attributes": attributes,
                        }
                    )

        # Datadog returns the whole window in one response, so pagination is
        # applied here and the cursor is just the offset into the page.
        offset = int(cursor) if cursor else 0
        items.sort(key=lambda item: item["timestamp"])
        window = items[offset : offset + page_size]
        next_offset = offset + len(window)

        return {
            "items": window,
            "next_cursor": str(next_offset) if next_offset < len(items) else None,
        }

    @staticmethod
    def _unit(series) -> str | None:
        """Datadog returns units as a [numerator, denominator] pair."""
        units = series.get("unit") or []
        return units[0].get("name") if units and isinstance(units[0], dict) else None
