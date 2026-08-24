from datetime import datetime
from typing import List


class Connector:
    """Telemetry connector template.

    Implement the capabilities your telemetry source supports to let the
    Monte Carlo Troubleshooting Agent (and the Monte Carlo MCP server) pull
    runtime evidence from it during an investigation.

    A telemetry connector is attached to an existing Warehouse or ETL
    integration. When an investigation needs runtime evidence for one of that
    integration's resources, Monolith resolves the telemetry connection,
    checks that it advertises the requested capability, and invokes this
    connector synchronously through the Data Collector. The result is returned
    to the caller and **never stored** by Monte Carlo.

    Two capabilities exist:

    - **fetch_logs** returns ordered log records for a resource and time
      window — the raw runtime log lines (ECS task logs, Airflow task logs,
      job stdout/stderr, ...).
    - **fetch_telemetry** returns structured operational records or
      measurements for a resource and time window — named values with
      attributes (CPU utilization, queue depth, retry counts, ...).

    Declare which ones you support in ``manifest.json``::

        "capabilities": {
          "supports_logs": true,
          "supports_telemetry": true
        }

    Monte Carlo only calls a method you advertise. A capability you advertise
    but do not implement surfaces to the caller as
    ``TELEMETRY_INTEGRATION_UNAVAILABLE``.

    Both methods return a single **page** in the same envelope::

        {
            "items": [...],            # capability-specific records
            "next_cursor": "..."       # opaque continuation token, or None
        }

    The cursor is opaque to Monte Carlo — it is handed back to you unchanged
    on the next call, so put whatever your vendor's pagination needs in it.

    The agent sets ``self.credentials`` before calling any methods — use it in
    ``setup_connection()`` to initialize your API client.
    """

    credentials: dict

    ########################################
    # Connection Related Methods
    ########################################

    def setup_connection(self) -> None:
        """Initialize your vendor API client or connection.

        Called once before any fetch methods. Use ``self.credentials`` to
        access values from your ``credentials.json`` connect_args.

        Examples:
            REST API:  self.client = SomeClient(api_key=self.credentials["api_key"])
            SDK:       self.client = VendorSDK(token=self.credentials["token"])
        """
        # TODO: set up API client, e.g.:
        # self.client = SomeClient(api_key=self.credentials["api_key"])
        pass

    def close_connection(self) -> None:
        """Clean up resources when the connector session ends.

        Called after all fetch methods have completed. Override to close API
        clients, HTTP sessions, connections, etc.
        """
        # TODO: close API clients, connections, etc.
        pass

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
        """Fetch one page of log records for a resource and time window.

        Implement this when ``capabilities.supports_logs`` is true in
        ``manifest.json``.

        Return one page in the logs envelope. Each item:

        - ``timestamp`` (str): ISO 8601, timezone-aware
        - ``message`` (str): the log line
        - ``severity`` (str, optional): vendor-native severity/level

        Items must be ordered by ``timestamp`` ascending so the agent reads
        the failure in the order it happened::

            {
                "items": [
                    {
                        "timestamp": "2024-01-01T00:00:01Z",
                        "severity": "ERROR",
                        "message": "AccessDeniedException: secretsmanager:GetSecretValue",
                    }
                ],
                "next_cursor": "eyJhZnRlciI6ICIxNzA0MDY3MjAxIn0=",
            }

        An empty ``items`` list with ``next_cursor: None`` is a valid, correct
        result — it means the source was queried and had nothing matching.
        Do not raise for "no results".

        Args:
            resource_id: Vendor-native identifier of the resource being
                investigated, as configured on the associated Warehouse or
                ETL integration (an ECS task ARN, an Airflow DAG id, a job
                source id, ...). Use it to scope the query — never return
                logs for a resource that was not asked for.
            start_time: Inclusive lower bound (timezone-aware).
            end_time: Exclusive upper bound (timezone-aware).
            search_regex: Optional regular expression. Push it down to the
                vendor when the API supports it, otherwise filter the page
                yourself. ``None`` means no filter.
            severity: Optional list of vendor-native severities to include.
                ``None`` means all severities.
            page_size: Maximum number of items to return in this page.
            cursor: Opaque continuation token returned as ``next_cursor`` by
                a previous call. ``None`` for the first page.
            idempotency_key: Caller-generated key that is stable across
                retries of the same logical retrieval. Reads are naturally
                idempotent, so most connectors only log it for correlation.

        Returns:
            Dict with ``items`` and ``next_cursor``. ``next_cursor`` is
            ``None`` when this is the last page.
        """
        # TODO: query your vendor API and return a page of log records, e.g.:
        # response = self.client.search_logs(
        #     query=f'resource:"{resource_id}"',
        #     start=start_time,
        #     end=end_time,
        #     limit=page_size,
        #     cursor=cursor,
        # )
        # return {
        #     "items": [
        #         {
        #             "timestamp": record.timestamp.isoformat(),
        #             "severity": record.level,
        #             "message": record.message,
        #         }
        #         for record in response.records
        #     ],
        #     "next_cursor": response.next_cursor,
        # }
        raise NotImplementedError

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
        """Fetch one page of telemetry records for a resource and time window.

        Implement this when ``capabilities.supports_telemetry`` is true in
        ``manifest.json``.

        Return one page in the telemetry envelope. Each item:

        - ``timestamp`` (str): ISO 8601, timezone-aware
        - ``name`` (str): measurement or event name
        - ``value``: the structured value (number, string, or dict)
        - ``attributes`` (dict, optional): dimensions/tags for the record

        Items must be ordered by ``timestamp`` ascending::

            {
                "items": [
                    {
                        "timestamp": "2024-01-01T00:00:00Z",
                        "name": "ecs.task.memory.utilization",
                        "value": 98.4,
                        "attributes": {"unit": "percent", "cluster": "prod-etl"},
                    }
                ],
                "next_cursor": None,
            }

        As with logs, an empty page is a valid result, not an error.

        Args:
            resource_id: Vendor-native identifier of the resource being
                investigated. Use it to scope the query.
            start_time: Inclusive lower bound (timezone-aware).
            end_time: Exclusive upper bound (timezone-aware).
            names: Optional list of measurement/event names to include.
                ``None`` means return whatever the connector considers the
                default set for the resource.
            page_size: Maximum number of items to return in this page.
            cursor: Opaque continuation token from a previous call, or
                ``None`` for the first page.
            idempotency_key: Caller-generated key, stable across retries of
                the same logical retrieval.

        Returns:
            Dict with ``items`` and ``next_cursor``. ``next_cursor`` is
            ``None`` when this is the last page.
        """
        # TODO: query your vendor API and return a page of telemetry records,
        # e.g.:
        # series = self.client.query_metrics(
        #     resource=resource_id, start=start_time, end=end_time, names=names
        # )
        # return {
        #     "items": [
        #         {
        #             "timestamp": point.timestamp.isoformat(),
        #             "name": s.name,
        #             "value": point.value,
        #             "attributes": {"unit": s.unit},
        #         }
        #         for s in series
        #         for point in s.points
        #     ],
        #     "next_cursor": None,
        # }
        raise NotImplementedError
