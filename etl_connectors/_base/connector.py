from datetime import datetime
from typing import List


class Connector:
    """ETL connector template.

    Implement each stub method to connect your ETL tool to Monte Carlo.
    The agent framework calls these methods and pushes the returned data
    to the Monte Carlo API — you only need to query your vendor and return
    plain dicts.

    The two fetch methods serve different purposes:

    - **fetch_metadata** discovers the ETL assets (pipelines, jobs, tasks)
      that exist in the vendor tool. It returns structural metadata only —
      no run history.

    - **fetch_run_details** returns run execution data. It operates in two
      modes:

      1. **Polling mode** (``window_start``/``window_end`` provided, no
         ``run_ids``): fetch all runs within the fixed time window. Used by
         the agent on a schedule to discover recent activity.
      2. **Webhook mode** (``run_ids`` provided): fetch details for specific
         runs by ID. Used when a webhook notifies Monte Carlo about a run
         (e.g. a failure), and we need error details, task-level breakdown,
         etc.

    Return values are ``List[dict]`` — see ``pycarlo.features.ingestion.etl``
    for the full schema (EtlAsset for metadata, EtlRunEvent for run details).

    The agent sets ``self.credentials`` before calling any methods — use it
    in ``setup_connection()`` to initialize your API client.
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
            GraphQL:   self.session = requests.Session(); self.session.headers.update(...)
            SDK:       self.client = VendorSDK(token=self.credentials["token"])
        """
        # TODO: set up API client, e.g.:
        # self.client = SomeClient(api_key=self.credentials["api_key"])
        pass

    def close_connection(self) -> None:
        """Clean up resources when the connector session ends.

        Called after all fetch methods have completed. Override to close
        API clients, HTTP sessions, connections, etc.

        Examples:
            REST API:  self.session.close()
            SDK:       self.client.close()
        """
        # TODO: close API clients, connections, etc.
        pass

    ########################################
    # Metadata Fetching
    ########################################

    def fetch_metadata(self, limit: int, offset: int) -> List[dict]:
        """Fetch ETL asset metadata (groups, jobs, tasks).

        Returns structural metadata about the jobs/pipelines/tasks in the
        vendor tool. This does not include run history — runs are fetched
        separately via :meth:`fetch_run_details`.

        Each dict in the returned list should conform to the ``EtlAsset``
        schema defined in ``pycarlo.features.ingestion.etl``. Required
        fields:

        - ``job_source_id`` (str): unique vendor identifier for the job
        - ``name`` (str): human-readable job name

        Common optional fields include ``description``, ``folder``,
        ``schedule``, ``owner``, ``properties``, ``inputs``, ``outputs``.

        Nested structures (all optional):
        - ``group`` — dict with ``source_id`` (required), ``name``,
          ``group_type``, ``schedule``, ``attributes``
        - ``tasks`` — list of dicts, each with ``task_source_id`` (required),
          ``name`` (required), ``task_type``, ``description``, ``inputs``,
          ``outputs``, ``upstream_task_source_ids``, ``triggered_job_source_ids``

        **Lineage (optional):** ``inputs`` and ``outputs`` are lists of
        asset-ref dicts that describe which data assets (tables, views,
        files, etc.) a job or task reads/writes. This enables cross-domain
        lineage in Monte Carlo. Each dict needs:

        - ``asset_type``: TABLE, VIEW, FILE, TOPIC, DATASET, or DASHBOARD
        - ``role``: INPUT or OUTPUT (must match the list it's in)
        - ``fully_qualified_name``: vendor-native asset identifier
          (e.g. ``"db.schema.table"``)

        See ``pycarlo.features.ingestion.etl`` for the full schema.

        Args:
            limit: Maximum number of assets to return (for pagination).
            offset: Number of assets to skip (for pagination).

        Returns:
            List of dicts, each representing an ETL asset.
        """
        # TODO: query your vendor API and return asset dicts, e.g.:
        # pipelines = self.client.list_pipelines()
        # return [
        #     {
        #         "job_source_id": p.id,
        #         "name": p.name,
        #         "group": {"source_id": p.workspace_id, "name": p.workspace_name},
        #         "description": p.description,
        #         # Optional lineage — omit if vendor doesn't expose it:
        #         "inputs": [
        #             {"asset_type": "TABLE", "role": "INPUT", "fully_qualified_name": t}
        #             for t in p.input_tables
        #         ],
        #         "outputs": [
        #             {"asset_type": "TABLE", "role": "OUTPUT", "fully_qualified_name": t}
        #             for t in p.output_tables
        #         ],
        #     }
        #     for p in pipelines[offset:offset + limit]
        # ]
        raise NotImplementedError

    ########################################
    # Run Detail Fetching
    ########################################

    def fetch_run_details(
        self,
        run_ids: List[str] | None = None,
        window_start: datetime | None = None,
        window_end: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """Fetch run execution data.

        Operates in two modes:

        **Webhook mode** — when ``run_ids`` is provided, fetch details for
        those specific runs regardless of the time window. This is the path
        used when a webhook notifies Monte Carlo about a particular run
        (typically a failure) and we need error details, task-level
        breakdown, etc.

        **Polling mode** — when ``run_ids`` is *not* provided, return all
        runs that fall within the fixed ``[window_start, window_end)`` window
        (closed lower bound, open upper bound). The caller pins this window
        once and passes the *same* bounds unchanged across every paginated
        call, so pages never skip or duplicate runs — do not derive the
        window from ``now()`` yourself. ``window_start`` and ``window_end``
        are timezone-aware ``datetime`` objects. ``limit`` and ``offset``
        control pagination.

        Provide ``run_ids`` (webhook mode) or both ``window_start`` and
        ``window_end`` (polling mode).

        Each dict in the returned list should conform to the ``EtlRunEvent``
        schema defined in ``pycarlo.features.ingestion.etl``. Required
        fields:

        - ``job_source_id`` (str): the job this run belongs to
        - ``run_source_id`` (str): unique vendor identifier for the run
        - ``status`` (str): the vendor's raw status string (normalized via
          ``run_status_mapping`` in manifest.json)
        - ``event_time`` (str): ISO 8601 timestamp of the event

        Common optional fields include ``start_time``, ``end_time``,
        ``trigger``, ``error``, ``task_runs``, ``run_url``,
        ``inputs``, ``outputs``, ``group``.

        **``group`` (optional):** a nested dict in the same shape as
        ``EtlAsset.group`` (``source_id`` required; ``name``, ``group_type``,
        etc. optional). Set it when the same job exists in multiple groups
        under one container and a run belongs to just one of them — it says
        which group. Omit it and Monte Carlo picks the group automatically
        (a job that lives in a single group needs nothing). Pass the group's
        ``source_id``; the backend resolves the rest (connectors never supply
        an internal group id)::

            {
                "job_source_id": "pipeline-123",
                "run_source_id": "run-456",
                "status": "success",
                "event_time": "2024-01-01T00:05:00Z",
                "group": {"source_id": "prod-workspace", "name": "Prod"},
            }

        **Runtime lineage (optional):** ``inputs`` and ``outputs`` follow
        the same asset-ref format as ``fetch_metadata`` but represent what
        was actually read/written during this specific run. Use these when
        lineage can vary between runs. See ``pycarlo.features.ingestion.etl``
        for the full schema.

        Args:
            run_ids: Vendor-native run identifiers to fetch. When provided,
                     the time window is ignored.
            window_start: Inclusive lower bound of the run-collection window
                          (timezone-aware). Required when ``run_ids`` is not
                          provided.
            window_end: Exclusive upper bound of the run-collection window
                        (timezone-aware). Required when ``run_ids`` is not
                        provided.
            limit: Maximum number of run events to return (polling mode).
            offset: Number of run events to skip (polling mode).

        Returns:
            List of dicts, each representing a run event.

        Raises:
            ValueError: If ``run_ids`` is not provided and the window bounds
                are incomplete.
        """
        if run_ids is None and (window_start is None or window_end is None):
            raise ValueError(
                "Provide run_ids (webhook mode) or both window_start and "
                "window_end (polling mode)"
            )

        # TODO: query your vendor API and return run event dicts, e.g.:
        #
        # Polling mode — filter to the fixed [window_start, window_end) window:
        #   runs = self.client.list_runs(updated_after=window_start)
        #   runs = [r for r in runs if window_start <= r.updated_at < window_end]
        #   return [
        #       {
        #           "job_source_id": r.pipeline_id,
        #           "run_source_id": r.run_id,
        #           "status": r.status,  # raw vendor status — mapped via manifest.json
        #           "event_time": r.updated_at.isoformat(),
        #           "start_time": r.started_at.isoformat(),
        #           "end_time": r.finished_at.isoformat() if r.finished_at else None,
        #       }
        #       for r in runs[offset:offset + limit]
        #   ]
        #
        # Webhook mode:
        #   return [self._fetch_single_run(rid) for rid in run_ids]
        raise NotImplementedError
