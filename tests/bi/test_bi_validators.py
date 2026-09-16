from bi_connectors._base.validators import validate_bi_metadata_events


def _minimal_asset(**overrides):
    asset = {
        "asset_source_id": "dash-1",
        "name": "Executive Dashboard",
        "asset_type": "dashboard",
    }
    asset.update(overrides)
    return asset


def test_valid_minimal_asset():
    assert validate_bi_metadata_events([_minimal_asset()]) == []


def test_missing_each_required_field():
    for field in ("asset_source_id", "name", "asset_type"):
        asset = _minimal_asset()
        del asset[field]
        errors = validate_bi_metadata_events([asset])
        assert len(errors) == 1
        assert errors[0].field == field


def test_valid_full_asset():
    asset = _minimal_asset(
        description="Weekly exec metrics",
        asset_url="https://bi.example.com/dashboards/1",
        folder="Executive",
        owner={"email": "jane@example.com", "name": "Jane", "source_id": "u-1"},
        created_time="2024-01-01T00:00:00Z",
        last_modified_time="2024-06-01T12:30:00+00:00",
        last_viewed_time="2024-06-02T08:00:00Z",
        view_count=42,
        is_certified=True,
        certification_note="Reviewed by data team",
        is_archived=False,
        upstream_assets=[{"asset_source_id": "dash-0", "relationship_type": "DERIVES_FROM"}],
        downstream_assets=[{"asset_source_id": "dash-2"}],
        inputs=[
            {"asset_type": "TABLE", "role": "INPUT", "fully_qualified_name": "db.schema.t"}
        ],
        properties=[{"key": "team", "value": "analytics"}],
        attributes={"vendor": "example"},
    )
    assert validate_bi_metadata_events([asset]) == []


def test_owner_with_unexpected_key():
    errors = validate_bi_metadata_events([_minimal_asset(owner={"email": "a@b.c", "bad": 1})])
    assert len(errors) == 1
    assert errors[0].field == "owner"


def test_owner_not_a_dict():
    errors = validate_bi_metadata_events([_minimal_asset(owner="jane@example.com")])
    assert any(e.field == "owner" for e in errors)


def test_naive_timestamp():
    errors = validate_bi_metadata_events([_minimal_asset(created_time="2024-01-01T00:00:00")])
    assert any(e.field == "created_time" for e in errors)


def test_non_iso_timestamp():
    errors = validate_bi_metadata_events([_minimal_asset(created_time="not-a-date")])
    assert any(e.field == "created_time" for e in errors)


def test_view_count_negative():
    errors = validate_bi_metadata_events([_minimal_asset(view_count=-1)])
    assert any(e.field == "view_count" for e in errors)


def test_view_count_non_int():
    errors = validate_bi_metadata_events([_minimal_asset(view_count="10")])
    assert any(e.field == "view_count" for e in errors)


def test_view_count_bool_rejected():
    errors = validate_bi_metadata_events([_minimal_asset(view_count=True)])
    assert any(e.field == "view_count" for e in errors)


def test_upstream_ref_missing_asset_source_id():
    asset = _minimal_asset(upstream_assets=[{"relationship_type": "REFERENCES"}])
    errors = validate_bi_metadata_events([asset])
    assert any(e.field == "asset_source_id" for e in errors)


def test_upstream_ref_with_container_source_id():
    asset = _minimal_asset(
        upstream_assets=[{"asset_source_id": "dash-0", "container_source_id": "other"}]
    )
    errors = validate_bi_metadata_events([asset])
    assert any(e.field == "container_source_id" for e in errors)


def test_ref_with_bad_relationship_type():
    asset = _minimal_asset(upstream_assets=[{"asset_source_id": "dash-0", "relationship_type": "OWNS"}])
    errors = validate_bi_metadata_events([asset])
    assert any(e.field == "relationship_type" for e in errors)


def test_ref_with_valid_relationship_type():
    for rel in ("CONTAINED_IN", "DERIVES_FROM", "REFERENCES"):
        asset = _minimal_asset(downstream_assets=[{"asset_source_id": "dash-2", "relationship_type": rel}])
        assert validate_bi_metadata_events([asset]) == []


def test_inputs_ref_with_output_role():
    asset = _minimal_asset(
        inputs=[{"asset_type": "TABLE", "role": "OUTPUT", "fully_qualified_name": "db.s.t"}]
    )
    errors = validate_bi_metadata_events([asset])
    assert any(e.field == "role" for e in errors)


def test_inputs_ref_with_no_identifier():
    asset = _minimal_asset(inputs=[{"asset_type": "TABLE", "role": "INPUT"}])
    errors = validate_bi_metadata_events([asset])
    assert any(e.field == "fully_qualified_name" for e in errors)


def test_empty_batch():
    errors = validate_bi_metadata_events([])
    assert len(errors) == 1
    assert errors[0].field == "events"


def test_batch_exceeds_max_size():
    errors = validate_bi_metadata_events([_minimal_asset() for _ in range(101)])
    assert any("batch exceeds 100 items" in e.message for e in errors)


def test_properties_item_missing_key():
    errors = validate_bi_metadata_events([_minimal_asset(properties=[{"value": "x"}])])
    assert any(e.field == "key" for e in errors)


def test_attributes_not_a_dict():
    errors = validate_bi_metadata_events([_minimal_asset(attributes=["a"])])
    assert any(e.field == "attributes" for e in errors)
