from datetime import timedelta
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

      1. **Polling mode** (``lookback`` provided, no ``run_ids``): fetch all
         runs within the time window. Used by the agent on a schedule to
         discover recent activity.
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
        lookback: timedelta | None = None,
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

        **Polling mode** — when ``run_ids`` is *not* provided, use
        ``lookback`` to compute ``since = now - lookback`` and return all
        runs updated within that window. ``limit`` and ``offset`` control
        pagination.

        At least one of ``run_ids`` or ``lookback`` must be provided.

        Each dict in the returned list should conform to the ``EtlRunEvent``
        schema defined in ``pycarlo.features.ingestion.etl``. Required
        fields:

        - ``job_source_id`` (str): the job this run belongs to
        - ``run_source_id`` (str): unique vendor identifier for the run
        - ``status`` (str): run status (e.g. "success", "failed", "in_progress")
        - ``event_time`` (str): ISO 8601 timestamp of the event

        Common optional fields include ``start_time``, ``end_time``,
        ``trigger``, ``error``, ``task_runs``, ``run_url``. See
        ``pycarlo.features.ingestion.etl`` for the full schema.

        Args:
            run_ids: Vendor-native run identifiers to fetch. When provided,
                     ``lookback`` is ignored.
            lookback: Time interval to look back from now. Required when
                      ``run_ids`` is not provided.
            limit: Maximum number of run events to return (polling mode).
            offset: Number of run events to skip (polling mode).

        Returns:
            List of dicts, each representing a run event.

        Raises:
            ValueError: If neither ``run_ids`` nor ``lookback`` is provided.
        """
        if run_ids is None and lookback is None:
            raise ValueError(
                "At least one of run_ids or lookback must be provided"
            )

        # TODO: query your vendor API and return run event dicts, e.g.:
        #
        # Polling mode:
        #   since = datetime.now(timezone.utc) - lookback
        #   runs = self.client.list_runs(updated_after=since)
        #   return [
        #       {
        #           "job_source_id": r.pipeline_id,
        #           "run_source_id": r.run_id,
        #           "status": map_status(r.status),
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
