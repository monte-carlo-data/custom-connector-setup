from typing import List


class Connector:
    """BI connector template.

    Implement each stub method to connect your BI tool to Monte Carlo.
    The agent framework calls these methods and pushes the returned data
    to the Monte Carlo API — you only need to query your vendor and return
    plain dicts.

    A BI connector has a single fetch method:

    - **fetch_metadata** discovers the BI assets (dashboards, analyses,
      cards, workbooks) that exist in the vendor tool. It returns
      structural metadata only.

    There is **no** ``fetch_run_details`` and **no** webhook — BI assets
    have no run/execution pipeline, so the connector exposes only the
    metadata method above. Unlike ETL connectors (which redefine this base
    and implement both fetch methods), BI connectors implement the same
    contract standalone. Do **not** subclass or import this module from
    connector code — only the connector's own directory ships in the agent
    image, so a ``_base`` import fails at runtime with
    ``No module named 'bi_connectors'``.

    Return values are ``List[dict]`` — see ``pycarlo.features.ingestion.bi``
    for the full schema (``BiAsset`` for metadata).

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
        """Fetch BI asset metadata (dashboards, analyses, cards, workbooks).

        Returns structural metadata about the BI assets in the vendor tool.
        BI assets have no run pipeline, so this is the only fetch method.

        Each dict in the returned list should conform to the ``BiAsset``
        schema defined in ``pycarlo.features.ingestion.bi``. Required
        fields:

        - ``asset_source_id`` (str): unique, vendor-stable identifier for the
          asset within the container. It is the identity seed — it MUST
          remain stable across renames and moves, or Monte Carlo will treat
          the asset as a new one.
        - ``name`` (str): human-readable asset name
        - ``asset_type`` (str): free-form label for the asset kind
          (e.g. ``"dashboard"``, ``"analysis"``, ``"card"``, ``"workbook"``)

        Common optional fields include ``description``, ``asset_url``,
        ``folder``, ``view_count``, ``is_certified``, ``certification_note``,
        ``is_archived``, ``properties``, ``attributes``, and the time /
        owner / lineage fields below.

        Nested / scalar structures (all optional):

        - ``owner`` — dict with any of ``email``, ``name``, ``source_id``
        - ``created_time`` / ``last_modified_time`` / ``last_viewed_time`` —
          ISO-8601 timezone-aware timestamp strings
        - ``properties`` — list of ``{key, value}`` dicts (arbitrary tags)
        - ``attributes`` — dict of arbitrary vendor-specific metadata

        **BI-to-BI lineage (optional):** ``upstream_assets`` and
        ``downstream_assets`` are lists of BI asset-ref dicts describing how
        BI assets relate to one another. Each dict needs:

        - ``asset_source_id``: the related BI asset's source id (required)
        - ``relationship_type``: one of ``CONTAINED_IN``, ``DERIVES_FROM``,
          or ``REFERENCES`` (optional)

        Do NOT set ``container_source_id`` — cross-container references are
        unsupported in v1 and are dropped server-side.

        **Table lineage (optional):** ``inputs`` is a list of warehouse
        asset-ref dicts describing which data assets (tables, views, etc.)
        the BI asset reads. This enables cross-domain lineage in Monte Carlo.
        Each dict needs:

        - ``asset_type``: TABLE, VIEW, FILE, TOPIC, DATASET, or DASHBOARD
        - ``role``: ``INPUT`` (BI assets only consume warehouse assets)
        - ``mcon`` and/or ``fully_qualified_name``: at least one identifier
          (e.g. ``"db.schema.table"``)

        See ``pycarlo.features.ingestion.bi`` for the full schema.

        Args:
            limit: Maximum number of assets to return (for pagination).
            offset: Number of assets to skip (for pagination).

        Returns:
            List of dicts, each representing a BI asset.
        """
        # TODO: query your vendor API and return asset dicts, e.g.:
        # dashboards = self.client.list_dashboards()
        # return [
        #     {
        #         "asset_source_id": d.id,  # stable vendor id — survives renames
        #         "name": d.name,
        #         "asset_type": "dashboard",
        #         "description": d.description,
        #         "asset_url": d.url,
        #         "folder": d.folder_name,
        #         "owner": {"email": d.owner_email, "name": d.owner_name},
        #         # Optional BI->BI lineage — omit if vendor doesn't expose it:
        #         "upstream_assets": [
        #             {"asset_source_id": u.id, "relationship_type": "DERIVES_FROM"}
        #             for u in d.upstream_assets
        #         ],
        #         # Optional table lineage:
        #         "inputs": [
        #             {"asset_type": "TABLE", "role": "INPUT", "fully_qualified_name": t}
        #             for t in d.source_tables
        #         ],
        #     }
        #     for d in dashboards[offset:offset + limit]
        # ]
        raise NotImplementedError
