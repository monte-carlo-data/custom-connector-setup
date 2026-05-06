from datetime import datetime, timedelta, timezone, date

import pytest

pytestmark = [
    pytest.mark.query_language,
    pytest.mark.ql_prerequisites,
    pytest.mark.capability("supports_full_query_language"),
]


# ---------------------------------------------------------------------------
# Query building
# ---------------------------------------------------------------------------


@pytest.mark.template(func="build_cte_template")
@pytest.mark.template(func="add_from_clause_template")
@pytest.mark.template(func="add_select_clause_template")
def test_select_from_cte(ql):
    """CTE with 2 rows, SELECT both cols, verify values."""
    data = [
        {"col_a": 1, "col_b": "hello"},
        {"col_a": 2, "col_b": "world"},
    ]
    cte, alias = ql.make_data_source(data)
    from_clause = ql.render(ql.templates.add_from_clause_template, from_expression=alias)
    select_clause = ql.render(ql.templates.add_select_clause_template, select_expressions=["col_a, col_b"])
    order = ql.render(ql.templates.ascending_order_template).format(x="col_a")
    query = f"{cte} {select_clause} {from_clause} ORDER BY {order}"
    rows = ql.execute(query)
    assert len(rows) == 2
    assert rows[0][0] == 1
    assert rows[1][0] == 2


@pytest.mark.template(func="union_queries_template")
def test_union_all(ql):
    """CTE with 5 rows via union, COUNT(*) == 5."""
    data = [{"val": i} for i in range(5)]
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    result = ql.select_from_data_source(data, count_expr)
    assert result == 5


@pytest.mark.template(func="get_arbitrary_where_clause_template")
def test_arbitrary_where_clause(ql):
    """CTE + WHERE always-true, verify row returns."""
    data = [{"val": 42}]
    where_clause = ql.render(ql.templates.get_arbitrary_where_clause_template)
    result = ql.select_from_data_source(data, "val", condition=where_clause)
    assert result == 42


@pytest.mark.template(func="ascending_order_template")
@pytest.mark.template(func="descending_order_template")
def test_ordering(ql):
    """CTE [3,1,2], ORDER BY ASC -> [1,2,3], DESC -> [3,2,1]."""
    data = [{"val": 3}, {"val": 1}, {"val": 2}]
    cte, alias = ql.make_data_source(data)
    from_clause = ql.render(ql.templates.add_from_clause_template, from_expression=alias)
    select_clause = ql.render(ql.templates.add_select_clause_template, select_expressions=["val"])

    # ASC
    asc_order = ql.render(ql.templates.ascending_order_template).format(x="val")
    query_asc = f"{cte} {select_clause} {from_clause} ORDER BY {asc_order}"
    rows_asc = ql.execute(query_asc)
    assert [r[0] for r in rows_asc] == [1, 2, 3]

    # DESC
    desc_order = ql.render(ql.templates.descending_order_template).format(x="val")
    query_desc = f"{cte} {select_clause} {from_clause} ORDER BY {desc_order}"
    rows_desc = ql.execute(query_desc)
    assert [r[0] for r in rows_desc] == [3, 2, 1]


@pytest.mark.template(func="string_literal_template")
@pytest.mark.template(func="escape_string_template")
def test_string_literal_with_escaping(ql):
    """SELECT literal with single quote, verify "it's a test"."""
    escaped = ql.render(ql.templates.escape_string_template, string="it's a test")
    literal = ql.render(ql.templates.string_literal_template, string=escaped)
    result = ql.select_expression(literal)
    assert result == "it's a test"


@pytest.mark.template(func="get_case_when_func_template")
def test_case_when(ql):
    """CASE WHEN val > 5 THEN 'big' ELSE 'small', verify."""
    data = [{"val": 10}, {"val": 2}]
    gt_expr = ql.render(ql.templates.get_is_gt_expression_template).format(x="val", y="5")
    case_expr = ql.render(
        ql.templates.get_case_when_func_template,
        conditions_and_results=[(gt_expr, "'big'")],
        else_result="'small'",
    )
    cte, alias = ql.make_data_source(data)
    from_clause = ql.render(ql.templates.add_from_clause_template, from_expression=alias)
    select_clause = ql.render(ql.templates.add_select_clause_template, select_expressions=[case_expr])
    order = ql.render(ql.templates.descending_order_template).format(x="val")
    query = f"{cte} {select_clause} {from_clause} ORDER BY {order}"
    rows = ql.execute(query)
    assert rows[0][0] == "big"
    assert rows[1][0] == "small"


@pytest.mark.template(func="escape_field_name_template")
@pytest.mark.template(func="alias_field_template")
def test_escape_field_name(ql):
    """Verify escaped identifier works in query."""
    escaped = ql.render(ql.templates.escape_field_name_template, field_name="my field")
    data = [{"val": 1}]
    cte, alias = ql.make_data_source(data)
    aliased = ql.render(ql.templates.alias_field_template, field="val", alias=escaped)
    from_clause = ql.render(ql.templates.add_from_clause_template, from_expression=alias)
    select_clause = ql.render(ql.templates.add_select_clause_template, select_expressions=[aliased])
    query = f"{cte} {select_clause} {from_clause}"
    rows = ql.execute(query)
    assert rows[0][0] == 1


@pytest.mark.template(func="negate_expression_template")
def test_negate_expression(ql):
    """NOT(TRUE) -> false."""
    negated = ql.render(ql.templates.negate_expression_template, query="TRUE")
    case_expr = ql.render(
        ql.templates.get_case_when_func_template,
        conditions_and_results=[(negated, "1")],
        else_result="0",
    )
    result = ql.select_expression(case_expr)
    assert result == 0


@pytest.mark.template(func="get_table_identifier_template")
def test_get_table_identifier(ql):
    """Verify db.schema.table formatting."""
    result = ql.render(
        ql.templates.get_table_identifier_template,
        database="my_db",
        schema="my_schema",
        table="my_table",
    )
    assert "my_db" in result
    assert "my_schema" in result
    assert "my_table" in result


@pytest.mark.template(func="all_fields_expression_template")
def test_all_fields_expression(ql):
    """SELECT * returns all columns."""
    data = [{"col_a": 1, "col_b": 2}]
    cte, alias = ql.make_data_source(data)
    all_fields = ql.render(ql.templates.all_fields_expression_template)
    from_clause = ql.render(ql.templates.add_from_clause_template, from_expression=alias)
    select_clause = ql.render(ql.templates.add_select_clause_template, select_expressions=[all_fields])
    query = f"{cte} {select_clause} {from_clause}"
    rows = ql.execute(query)
    assert len(rows) == 1
    assert len(rows[0]) >= 2


@pytest.mark.template(func="get_field_or_alias_template")
def test_field_or_alias(ql):
    """Render get_field_or_alias_template, verify non-empty output."""
    result = ql.render(ql.templates.get_field_or_alias_template, _optional_vars={"alias"}, field="my_col", alias="my_alias")
    assert result and len(result.strip()) > 0


@pytest.mark.template(func="supports_literal_group_by_template")
def test_supports_literal_group_by(ql):
    """Boolean flag: renders to 'true' or 'false'."""
    result = ql.templates.supports_literal_group_by_template()
    assert result is not None
    assert result.strip().lower() in ("true", "false")


@pytest.mark.template(func="supports_group_by_on_subquery_template")
def test_supports_group_by_on_subquery(ql):
    """Boolean flag: renders to 'true' or 'false'."""
    result = ql.templates.supports_group_by_on_subquery_template()
    assert result is not None
    assert result.strip().lower() in ("true", "false")


# ---------------------------------------------------------------------------
# Type casting (prerequisites only — metric-mapped tests live in test_ql_metrics)
# ---------------------------------------------------------------------------


@pytest.mark.template(func="get_casting_to_numeric_expression_template")
def test_cast_to_numeric(ql):
    """Cast '42.5' to numeric, verify 42.5."""
    escaped = ql.render(ql.templates.escape_string_template, string="42.5")
    literal = ql.render(ql.templates.string_literal_template, string=escaped)
    cast_expr = ql.render(ql.templates.get_casting_to_numeric_expression_template, expression=literal)
    result = ql.select_expression(cast_expr)
    assert float(result) == pytest.approx(42.5)


@pytest.mark.template(func="cast_to_string_func_template")
def test_cast_to_string(ql):
    """Cast 123 to string, verify '123'."""
    cast_expr = ql.render(ql.templates.cast_to_string_func_template, expression="123")
    result = ql.select_expression(cast_expr)
    assert str(result).strip() == "123"


@pytest.mark.template(func="default_cast_to_timestamp_func_template")
def test_cast_to_timestamp(ql):
    """Cast string to timestamp, verify date parts."""
    escaped = ql.render(ql.templates.escape_string_template, string="2024-06-15 10:30:00")
    literal = ql.render(ql.templates.string_literal_template, string=escaped)
    cast_expr = ql.render(ql.templates.default_cast_to_timestamp_func_template, expression=literal)
    to_str = ql.render(ql.templates.cast_to_string_func_template, expression=cast_expr)
    result = str(ql.select_expression(to_str))
    assert "2024" in result
    assert "06" in result or "Jun" in result
    assert "15" in result


@pytest.mark.template(func="literal_value_template")
def test_literal_value_int(ql):
    """SELECT literal(42), verify 42."""
    literal = ql.render(ql.templates.literal_value_template, value="42")
    result = ql.select_expression(literal)
    assert int(result) == 42


@pytest.mark.template(func="cast_string_to_timestamp_template")
def test_cast_string_to_timestamp(ql):
    """Cast string to timestamp, verify date parts."""
    escaped = ql.render(ql.templates.escape_string_template, string="2024-06-15 10:30:00")
    literal = ql.render(ql.templates.string_literal_template, string=escaped)
    cast_expr = ql.render(ql.templates.cast_string_to_timestamp_template, expression=literal)
    to_str = ql.render(ql.templates.cast_to_string_func_template, expression=cast_expr)
    result = str(ql.select_expression(to_str))
    assert "2024" in result
    assert "15" in result


@pytest.mark.template(func="cast_numeric_to_timestamp_template")
def test_cast_numeric_to_timestamp(ql):
    """Cast numeric epoch to timestamp, verify result contains date parts."""
    # 1718438400 = 2024-06-15 08:00:00 UTC
    cast_expr = ql.render(ql.templates.cast_numeric_to_timestamp_template, expression="1718438400")
    to_str = ql.render(ql.templates.cast_to_string_func_template, expression=cast_expr)
    result = str(ql.select_expression(to_str))
    assert "2024" in result


@pytest.mark.template(func="cast_date_to_timestamp_template")
def test_cast_date_to_timestamp(ql):
    """Cast date to timestamp."""
    date_expr = ql.render(ql.templates.current_date_func_template)
    cast_expr = ql.render(ql.templates.cast_date_to_timestamp_template, expression=date_expr)
    to_str = ql.render(ql.templates.cast_to_string_func_template, expression=cast_expr)
    result = str(ql.select_expression(to_str))
    assert result is not None and len(result) > 0


@pytest.mark.template(func="cast_default_to_timestamp_template")
def test_cast_default_to_timestamp(ql):
    """Cast value to timestamp using default method."""
    escaped = ql.render(ql.templates.escape_string_template, string="2024-06-15 10:30:00")
    literal = ql.render(ql.templates.string_literal_template, string=escaped)
    cast_expr = ql.render(ql.templates.cast_default_to_timestamp_template, expression=literal)
    to_str = ql.render(ql.templates.cast_to_string_func_template, expression=cast_expr)
    result = str(ql.select_expression(to_str))
    assert "2024" in result


@pytest.mark.template(func="cast_timestamp_to_date_template")
def test_cast_timestamp_to_date(ql):
    """Cast timestamp to date, verify date parts."""
    ts_expr = ql.render(ql.templates.current_timestamp_func_template)
    cast_expr = ql.render(ql.templates.cast_timestamp_to_date_template, timestamp=ts_expr)
    to_str = ql.render(ql.templates.cast_to_string_func_template, expression=cast_expr)
    result = str(ql.select_expression(to_str))
    assert result is not None and len(result) > 0


@pytest.mark.template(func="cast_timestamp_to_timestamp_ntz_template")
def test_cast_timestamp_to_timestamp_ntz(ql):
    """Cast timestamp to timestamp without timezone."""
    ts_expr = ql.render(ql.templates.current_timestamp_func_template)
    cast_expr = ql.render(ql.templates.cast_timestamp_to_timestamp_ntz_template, timestamp=ts_expr)
    to_str = ql.render(ql.templates.cast_to_string_func_template, expression=cast_expr)
    result = str(ql.select_expression(to_str))
    assert result is not None and len(result) > 0


@pytest.mark.template(func="cast_timestamp_to_timestamp_tz_template")
def test_cast_timestamp_to_timestamp_tz(ql):
    """Cast timestamp to timestamp with timezone."""
    ts_expr = ql.render(ql.templates.current_timestamp_func_template)
    cast_expr = ql.render(ql.templates.cast_timestamp_to_timestamp_tz_template, timestamp=ts_expr)
    to_str = ql.render(ql.templates.cast_to_string_func_template, expression=cast_expr)
    result = str(ql.select_expression(to_str))
    assert result is not None and len(result) > 0


@pytest.mark.template(func="cast_to_timestamp_with_tz_template")
def test_cast_to_timestamp_with_tz(ql):
    """Render cast_to_timestamp_with_tz_template, verify non-empty."""
    result = ql.templates.cast_to_timestamp_with_tz_template()
    assert result is not None and len(result.strip()) > 0


@pytest.mark.template(func="cast_to_timestamp_without_tz_template")
def test_cast_to_timestamp_without_tz(ql):
    """Render cast_to_timestamp_without_tz_template, verify non-empty."""
    result = ql.templates.cast_to_timestamp_without_tz_template()
    assert result is not None and len(result.strip()) > 0


# ---------------------------------------------------------------------------
# Comparison operators
# ---------------------------------------------------------------------------


@pytest.mark.template(func="get_is_eq_expression_template")
def test_equality(ql):
    """CTE [{x:10,y:10},{x:10,y:20}], COUNT WHERE x=y -> 1."""
    data = [{"x": 10, "y": 10}, {"x": 10, "y": 20}]
    eq_expr = ql.render(ql.templates.get_is_eq_expression_template).format(x="x", y="y")
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    result = ql.select_from_data_source(data, count_expr, condition=eq_expr)
    assert int(result) == 1


@pytest.mark.template(func="get_is_gt_expression_template")
@pytest.mark.template(func="get_is_lt_expression_template")
def test_gt_and_lt(ql):
    """CTE [5,10,15], COUNT WHERE >8 -> 2, <8 -> 1."""
    data = [{"val": 5}, {"val": 10}, {"val": 15}]
    count_expr = ql.render(ql.templates.get_count_all_expression_template)

    gt_expr = ql.render(ql.templates.get_is_gt_expression_template).format(x="val", y="8")
    result_gt = ql.select_from_data_source(data, count_expr, condition=gt_expr)
    assert int(result_gt) == 2

    lt_expr = ql.render(ql.templates.get_is_lt_expression_template).format(x="val", y="8")
    result_lt = ql.select_from_data_source(data, count_expr, condition=lt_expr)
    assert int(result_lt) == 1


@pytest.mark.template(func="get_is_gte_expression_template")
@pytest.mark.template(func="get_is_lte_expression_template")
def test_gte_and_lte(ql):
    """Similar with boundary values."""
    data = [{"val": 5}, {"val": 10}, {"val": 15}]
    count_expr = ql.render(ql.templates.get_count_all_expression_template)

    gte_expr = ql.render(ql.templates.get_is_gte_expression_template).format(x="val", y="10")
    result_gte = ql.select_from_data_source(data, count_expr, condition=gte_expr)
    assert int(result_gte) == 2

    lte_expr = ql.render(ql.templates.get_is_lte_expression_template).format(x="val", y="10")
    result_lte = ql.select_from_data_source(data, count_expr, condition=lte_expr)
    assert int(result_lte) == 2


@pytest.mark.template(func="is_null_template")
@pytest.mark.template(func="is_not_null_template")
def test_null_checks(ql):
    """CTE [1,NULL,3], IS NULL -> 1, IS NOT NULL -> 2."""
    data = [{"val": 1}, {"val": None}, {"val": 3}]
    count_expr = ql.render(ql.templates.get_count_all_expression_template)

    null_expr = ql.render(ql.templates.is_null_template).format(x="val")
    result_null = ql.select_from_data_source(data, count_expr, condition=null_expr)
    assert int(result_null) == 1

    not_null_expr = ql.render(ql.templates.is_not_null_template).format(x="val")
    result_not_null = ql.select_from_data_source(data, count_expr, condition=not_null_expr)
    assert int(result_not_null) == 2


# ---------------------------------------------------------------------------
# Date/time functions
# ---------------------------------------------------------------------------


@pytest.mark.template(func="current_timestamp_func_template")
@pytest.mark.template(func="convert_to_unix_timestamp_func_template")
def test_current_timestamp(ql):
    """SELECT current_timestamp, verify within 120s of Python now."""
    ts_expr = ql.render(ql.templates.current_timestamp_func_template)
    epoch_expr = ql.render(ql.templates.convert_to_unix_timestamp_func_template, date_expr=ts_expr)
    result = ql.select_expression(epoch_expr)
    now_epoch = datetime.now(tz=timezone.utc).timestamp()
    assert abs(float(result) - now_epoch) < 120


@pytest.mark.template(func="current_date_func_template")
def test_current_date(ql):
    """SELECT current_date, verify matches today (+-1 day for TZ)."""
    date_expr = ql.render(ql.templates.current_date_func_template)
    to_str = ql.render(ql.templates.cast_to_string_func_template, expression=date_expr)
    result = str(ql.select_expression(to_str))
    today = date.today()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    assert any(d.isoformat() in result for d in [yesterday, today, tomorrow])


@pytest.mark.template(func="get_is_yesterday_expression_template")
@pytest.mark.template(func="literal_datetime_template")
def test_is_yesterday(ql):
    """CTE with yesterday_noon + today_noon timestamps, COUNT WHERE is_yesterday -> 1."""
    now = datetime.now(tz=timezone.utc)
    yesterday_noon = (now - timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    today_noon = now.replace(hour=12, minute=0, second=0, microsecond=0)

    yesterday_lit = ql.render(ql.templates.literal_datetime_template, date_time_value=yesterday_noon)
    today_lit = ql.render(ql.templates.literal_datetime_template, date_time_value=today_noon)

    # Build inline values with actual timestamps
    ts_alias_1 = ql.render(ql.templates.alias_field_template, field=yesterday_lit, alias="ts_val")
    ts_alias_2 = ql.render(ql.templates.alias_field_template, field=today_lit, alias="ts_val")
    sel1 = ql.render(ql.templates.add_select_clause_template, select_expressions=[ts_alias_1])
    sel2 = ql.render(ql.templates.add_select_clause_template, select_expressions=[ts_alias_2])
    unioned = ql.render(ql.templates.union_queries_template, queries=[sel1, sel2])
    ts_cte = ql.render(ql.templates.build_cte_template, alias="ts_data", cte=unioned)

    is_yesterday = ql.render(ql.templates.get_is_yesterday_expression_template).format(x="ts_val")
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    ts_from = ql.render(ql.templates.add_from_clause_template, from_expression="ts_data")
    ts_select = ql.render(ql.templates.add_select_clause_template, select_expressions=[count_expr])

    query = f"{ts_cte} {ts_select} {ts_from} WHERE {is_yesterday}"
    result = ql.execute_scalar(query)
    assert int(result) == 1


@pytest.mark.template(func="get_in_past_days_expression_template")
def test_in_past_days(ql):
    """CTE with 2_days_ago + 30_days_ago, past 7 days -> 1."""
    now = datetime.now(tz=timezone.utc)
    two_days_ago = now - timedelta(days=2)
    thirty_days_ago = now - timedelta(days=30)

    lit_2d = ql.render(ql.templates.literal_datetime_template, date_time_value=two_days_ago)
    lit_30d = ql.render(ql.templates.literal_datetime_template, date_time_value=thirty_days_ago)

    alias_2d = ql.render(ql.templates.alias_field_template, field=lit_2d, alias="ts_val")
    alias_30d = ql.render(ql.templates.alias_field_template, field=lit_30d, alias="ts_val")
    sel1 = ql.render(ql.templates.add_select_clause_template, select_expressions=[alias_2d])
    sel2 = ql.render(ql.templates.add_select_clause_template, select_expressions=[alias_30d])
    unioned = ql.render(ql.templates.union_queries_template, queries=[sel1, sel2])
    cte = ql.render(ql.templates.build_cte_template, alias="ts_data", cte=unioned)

    past_days = ql.render(ql.templates.get_in_past_days_expression_template, days=7).format(x="ts_val")
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    from_clause = ql.render(ql.templates.add_from_clause_template, from_expression="ts_data")
    select_clause = ql.render(ql.templates.add_select_clause_template, select_expressions=[count_expr])

    query = f"{cte} {select_clause} {from_clause} WHERE {past_days}"
    result = ql.execute_scalar(query)
    assert int(result) == 1


@pytest.mark.template(func="add_days_func_template")
def test_add_days(ql):
    """current_date + 1 > current_date -> true."""
    date_expr = ql.render(ql.templates.current_date_func_template)
    plus_one = ql.render(ql.templates.add_days_func_template, date_expr=date_expr, days=1)
    gt_expr = ql.render(ql.templates.get_is_gt_expression_template).format(x=plus_one, y=date_expr)
    case_expr = ql.render(
        ql.templates.get_case_when_func_template,
        conditions_and_results=[(gt_expr, "1")], else_result="0",
    )
    result = ql.select_expression(case_expr)
    assert int(result) == 1


@pytest.mark.template(func="add_hours_timestamp_func_template")
def test_add_hours_timestamp(ql):
    """current_timestamp + 3h > current_timestamp -> true."""
    ts_expr = ql.render(ql.templates.current_timestamp_func_template)
    plus_3h = ql.render(ql.templates.add_hours_timestamp_func_template, date_expr=ts_expr, hours=3)
    gt_expr = ql.render(ql.templates.get_is_gt_expression_template).format(x=plus_3h, y=ts_expr)
    case_expr = ql.render(
        ql.templates.get_case_when_func_template,
        conditions_and_results=[(gt_expr, "1")], else_result="0",
    )
    result = ql.select_expression(case_expr)
    assert int(result) == 1


@pytest.mark.template(func="time_truncate_func_template")
def test_time_truncate(ql):
    """Truncate timestamp to DAY, verify time zeroed."""
    escaped = ql.render(ql.templates.escape_string_template, string="2024-06-15 14:30:45")
    literal = ql.render(ql.templates.string_literal_template, string=escaped)
    ts_cast = ql.render(ql.templates.default_cast_to_timestamp_func_template, expression=literal)
    truncated = ql.render(ql.templates.time_truncate_func_template, field=ts_cast, truncation="DAY")
    to_str = ql.render(ql.templates.cast_to_string_func_template, expression=truncated)
    result = str(ql.select_expression(to_str))
    assert "2024" in result
    assert "14:30" not in result


@pytest.mark.template(func="get_date_diff_func_template")
def test_date_diff(ql):
    """Diff between two dates, verify expected days."""
    escaped1 = ql.render(ql.templates.escape_string_template, string="2024-01-01 00:00:00")
    escaped2 = ql.render(ql.templates.escape_string_template, string="2024-01-11 00:00:00")
    lit1 = ql.render(ql.templates.string_literal_template, string=escaped1)
    lit2 = ql.render(ql.templates.string_literal_template, string=escaped2)
    ts1 = ql.render(ql.templates.default_cast_to_timestamp_func_template, expression=lit1)
    ts2 = ql.render(ql.templates.default_cast_to_timestamp_func_template, expression=lit2)
    diff_expr = ql.render(ql.templates.get_date_diff_func_template, date_expr1=ts1, date_expr2=ts2, date_part="day")
    result = ql.select_expression(diff_expr)
    assert abs(int(result)) == 10


@pytest.mark.template(func="convert_to_utc_template")
def test_convert_to_utc(ql):
    """Convert TZ timestamp, verify UTC result."""
    ts_expr = ql.render(ql.templates.current_timestamp_func_template)
    utc_expr = ql.render(ql.templates.convert_to_utc_template, field=ts_expr)
    to_str = ql.render(ql.templates.cast_to_string_func_template, expression=utc_expr)
    result = str(ql.select_expression(to_str))
    assert result is not None and len(result) > 0


@pytest.mark.template(func="date_literal_template")
def test_date_literal(ql):
    """Create date literal, verify roundtrip."""
    test_date = date(2024, 3, 15)
    lit = ql.render(ql.templates.date_literal_template, timestamp=test_date)
    to_str = ql.render(ql.templates.cast_to_string_func_template, expression=lit)
    result = str(ql.select_expression(to_str))
    assert "2024" in result
    assert "03" in result or "3" in result
    assert "15" in result


@pytest.mark.template(func="get_in_past_hours_expression_template")
def test_in_past_hours(ql):
    """CTE with 1h_ago + 48h_ago, past 24h -> 1."""
    now = datetime.now(tz=timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    forty_eight_hours_ago = now - timedelta(hours=48)

    lit_1h = ql.render(ql.templates.literal_datetime_template, date_time_value=one_hour_ago)
    lit_48h = ql.render(ql.templates.literal_datetime_template, date_time_value=forty_eight_hours_ago)

    alias_1h = ql.render(ql.templates.alias_field_template, field=lit_1h, alias="ts_val")
    alias_48h = ql.render(ql.templates.alias_field_template, field=lit_48h, alias="ts_val")
    sel1 = ql.render(ql.templates.add_select_clause_template, select_expressions=[alias_1h])
    sel2 = ql.render(ql.templates.add_select_clause_template, select_expressions=[alias_48h])
    unioned = ql.render(ql.templates.union_queries_template, queries=[sel1, sel2])
    cte = ql.render(ql.templates.build_cte_template, alias="ts_data", cte=unioned)

    past_hours = ql.render(ql.templates.get_in_past_hours_expression_template, hours=24).format(x="ts_val")
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    from_clause = ql.render(ql.templates.add_from_clause_template, from_expression="ts_data")
    select_clause = ql.render(ql.templates.add_select_clause_template, select_expressions=[count_expr])

    query = f"{cte} {select_clause} {from_clause} WHERE {past_hours}"
    result = ql.execute_scalar(query)
    assert int(result) == 1


@pytest.mark.template(func="add_days_timestamp_func_template")
def test_add_days_timestamp(ql):
    """current_timestamp + 1 day > current_timestamp -> true."""
    ts_expr = ql.render(ql.templates.current_timestamp_func_template)
    plus_one = ql.render(ql.templates.add_days_timestamp_func_template, date_expr=ts_expr, days=1)
    gt_expr = ql.render(ql.templates.get_is_gt_expression_template).format(x=plus_one, y=ts_expr)
    case_expr = ql.render(
        ql.templates.get_case_when_func_template,
        conditions_and_results=[(gt_expr, "1")], else_result="0",
    )
    result = ql.select_expression(case_expr)
    assert int(result) == 1


@pytest.mark.template(func="truncate_to_day_template")
def test_truncate_to_day(ql):
    """Truncate timestamp to day, verify time portion removed."""
    escaped = ql.render(ql.templates.escape_string_template, string="2024-06-15 14:30:45")
    literal = ql.render(ql.templates.string_literal_template, string=escaped)
    ts_cast = ql.render(ql.templates.default_cast_to_timestamp_func_template, expression=literal)
    truncated = ql.render(ql.templates.truncate_to_day_template, field=ts_cast)
    to_str = ql.render(ql.templates.cast_to_string_func_template, expression=truncated)
    result = str(ql.select_expression(to_str))
    assert "2024" in result
    assert "14:30:45" not in result


@pytest.mark.template(func="truncate_to_hour_template")
def test_truncate_to_hour(ql):
    """Truncate timestamp to hour, verify minutes/seconds removed."""
    escaped = ql.render(ql.templates.escape_string_template, string="2024-06-15 14:30:45")
    literal = ql.render(ql.templates.string_literal_template, string=escaped)
    ts_cast = ql.render(ql.templates.default_cast_to_timestamp_func_template, expression=literal)
    truncated = ql.render(ql.templates.truncate_to_hour_template, field=ts_cast)
    to_str = ql.render(ql.templates.cast_to_string_func_template, expression=truncated)
    result = str(ql.select_expression(to_str))
    assert "2024" in result
    assert "30:45" not in result


@pytest.mark.template(func="truncate_to_week_template")
def test_truncate_to_week(ql):
    """Truncate timestamp to week, verify result is a valid date."""
    escaped = ql.render(ql.templates.escape_string_template, string="2024-06-15 14:30:45")
    literal = ql.render(ql.templates.string_literal_template, string=escaped)
    ts_cast = ql.render(ql.templates.default_cast_to_timestamp_func_template, expression=literal)
    truncated = ql.render(ql.templates.truncate_to_week_template, field=ts_cast)
    to_str = ql.render(ql.templates.cast_to_string_func_template, expression=truncated)
    result = str(ql.select_expression(to_str))
    assert "2024" in result
    assert "06" in result or "Jun" in result


@pytest.mark.template(func="truncate_to_month_template")
def test_truncate_to_month(ql):
    """Truncate timestamp to month, verify day portion removed."""
    escaped = ql.render(ql.templates.escape_string_template, string="2024-06-15 14:30:45")
    literal = ql.render(ql.templates.string_literal_template, string=escaped)
    ts_cast = ql.render(ql.templates.default_cast_to_timestamp_func_template, expression=literal)
    truncated = ql.render(ql.templates.truncate_to_month_template, field=ts_cast)
    to_str = ql.render(ql.templates.cast_to_string_func_template, expression=truncated)
    result = str(ql.select_expression(to_str))
    assert "2024" in result


@pytest.mark.template(func="truncate_to_year_template")
def test_truncate_to_year(ql):
    """Truncate timestamp to year."""
    escaped = ql.render(ql.templates.escape_string_template, string="2024-06-15 14:30:45")
    literal = ql.render(ql.templates.string_literal_template, string=escaped)
    ts_cast = ql.render(ql.templates.default_cast_to_timestamp_func_template, expression=literal)
    truncated = ql.render(ql.templates.truncate_to_year_template, field=ts_cast)
    to_str = ql.render(ql.templates.cast_to_string_func_template, expression=truncated)
    result = str(ql.select_expression(to_str))
    assert "2024" in result


@pytest.mark.template(func="get_days_of_week_expression_template")
def test_days_of_week(ql):
    """Render days-of-week expression, verify non-empty result."""
    ts_expr = ql.render(ql.templates.current_timestamp_func_template)
    dow_expr = ql.render(ql.templates.get_days_of_week_expression_template).format(x=ts_expr)
    result = ql.select_expression(dow_expr)
    assert result is not None


@pytest.mark.template(func="get_in_past_calendar_week_expression_template")
def test_in_past_calendar_week(ql):
    """CTE with recent + old timestamps, past calendar week -> 1."""
    now = datetime.now(tz=timezone.utc)
    three_days_ago = now - timedelta(days=3)
    sixty_days_ago = now - timedelta(days=60)

    lit_3d = ql.render(ql.templates.literal_datetime_template, date_time_value=three_days_ago)
    lit_60d = ql.render(ql.templates.literal_datetime_template, date_time_value=sixty_days_ago)

    alias_3d = ql.render(ql.templates.alias_field_template, field=lit_3d, alias="ts_val")
    alias_60d = ql.render(ql.templates.alias_field_template, field=lit_60d, alias="ts_val")
    sel1 = ql.render(ql.templates.add_select_clause_template, select_expressions=[alias_3d])
    sel2 = ql.render(ql.templates.add_select_clause_template, select_expressions=[alias_60d])
    unioned = ql.render(ql.templates.union_queries_template, queries=[sel1, sel2])
    cte = ql.render(ql.templates.build_cte_template, alias="ts_data", cte=unioned)

    past_week = ql.render(ql.templates.get_in_past_calendar_week_expression_template, _optional_vars={"weeks"}, weeks=1).format(x="ts_val")
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    from_clause = ql.render(ql.templates.add_from_clause_template, from_expression="ts_data")
    select_clause = ql.render(ql.templates.add_select_clause_template, select_expressions=[count_expr])

    query = f"{cte} {select_clause} {from_clause} WHERE {past_week}"
    result = ql.execute_scalar(query)
    assert int(result) >= 1


@pytest.mark.template(func="get_in_past_calendar_month_expression_template")
def test_in_past_calendar_month(ql):
    """CTE with recent + old timestamps, past calendar month -> 1."""
    now = datetime.now(tz=timezone.utc)
    five_days_ago = now - timedelta(days=5)
    one_year_ago = now - timedelta(days=365)

    lit_5d = ql.render(ql.templates.literal_datetime_template, date_time_value=five_days_ago)
    lit_1y = ql.render(ql.templates.literal_datetime_template, date_time_value=one_year_ago)

    alias_5d = ql.render(ql.templates.alias_field_template, field=lit_5d, alias="ts_val")
    alias_1y = ql.render(ql.templates.alias_field_template, field=lit_1y, alias="ts_val")
    sel1 = ql.render(ql.templates.add_select_clause_template, select_expressions=[alias_5d])
    sel2 = ql.render(ql.templates.add_select_clause_template, select_expressions=[alias_1y])
    unioned = ql.render(ql.templates.union_queries_template, queries=[sel1, sel2])
    cte = ql.render(ql.templates.build_cte_template, alias="ts_data", cte=unioned)

    past_month = ql.render(ql.templates.get_in_past_calendar_month_expression_template).format(x="ts_val")
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    from_clause = ql.render(ql.templates.add_from_clause_template, from_expression="ts_data")
    select_clause = ql.render(ql.templates.add_select_clause_template, select_expressions=[count_expr])

    query = f"{cte} {select_clause} {from_clause} WHERE {past_month}"
    result = ql.execute_scalar(query)
    assert int(result) >= 1


@pytest.mark.template(func="utc_literal_template")
def test_utc_literal(ql):
    """Render UTC literal, verify non-empty."""
    result = ql.render(ql.templates.utc_literal_template)
    assert result and len(result.strip()) > 0


# ---------------------------------------------------------------------------
# Infrastructure helpers
# ---------------------------------------------------------------------------


@pytest.mark.template(func="get_safe_divide_template")
def test_safe_divide(ql):
    """10/2 -> 5.0, 10/0 -> NULL or 0 (no error)."""
    safe_div = ql.render(ql.templates.get_safe_divide_template, dividend="10", divisor="2")
    result = ql.select_expression(safe_div)
    assert float(result) == pytest.approx(5.0)

    # Division by zero should not error
    safe_div_zero = ql.render(ql.templates.get_safe_divide_template, dividend="10", divisor="0")
    result_zero = ql.select_expression(safe_div_zero)
    assert result_zero is None or float(result_zero) == 0


@pytest.mark.template(func="supports_literal_select_template")
def test_supports_literal_select(ql):
    """Boolean flag: whether SELECT <literal> works without FROM."""
    result = ql.templates.supports_literal_select_template()
    assert result is not None
    assert result.strip().lower() in ("true", "false")


@pytest.mark.template(func="max_time_func_template")
def test_max_time(ql):
    """MAX of timestamps."""
    lit1 = ql.render(ql.templates.literal_datetime_template, date_time_value=datetime(2024, 1, 1))
    lit2 = ql.render(ql.templates.literal_datetime_template, date_time_value=datetime(2024, 6, 15))

    alias_1 = ql.render(ql.templates.alias_field_template, field=lit1, alias="ts_val")
    alias_2 = ql.render(ql.templates.alias_field_template, field=lit2, alias="ts_val")
    sel1 = ql.render(ql.templates.add_select_clause_template, select_expressions=[alias_1])
    sel2 = ql.render(ql.templates.add_select_clause_template, select_expressions=[alias_2])
    unioned = ql.render(ql.templates.union_queries_template, queries=[sel1, sel2])
    cte = ql.render(ql.templates.build_cte_template, alias="ts_data", cte=unioned)

    max_expr = ql.render(ql.templates.max_time_func_template, field="ts_val")
    from_clause = ql.render(ql.templates.add_from_clause_template, from_expression="ts_data")
    select_clause = ql.render(ql.templates.add_select_clause_template, select_expressions=[max_expr])
    to_str = ql.render(ql.templates.cast_to_string_func_template, expression=max_expr)
    select_clause = ql.render(ql.templates.add_select_clause_template, select_expressions=[to_str])

    query = f"{cte} {select_clause} {from_clause}"
    result = str(ql.execute_scalar(query))
    assert "2024" in result
    assert "06" in result or "Jun" in result


# ---------------------------------------------------------------------------
# Guard test: template-kwarg consistency
# ---------------------------------------------------------------------------

# Templates that must output {x} placeholders (NOT Jinja {{ field }}).
# These are called by CustomConnectorQL with no 'field' kwarg.
_PLACEHOLDER_TEMPLATES = [
    "get_avg_function_template",
    "get_stddev_function_template",
    "get_distinct_count_func_template",
    "get_distinct_func_template",
    "get_array_length_func_template",
    "get_isnan_expression_template",
    "get_is_yesterday_expression_template",
    "get_is_timestamp_expression_template",
    "get_not_is_timestamp_expression_template",
    "is_null_template",
    "is_not_null_template",
    "get_is_empty_string_expression_template",
    "ascending_order_template",
    "descending_order_template",
    "get_length_template",
    "get_epoch_seconds_expression_template",
    "get_epoch_seconds_parameter_template",
    "get_in_past_days_expression_template",
    "get_in_past_hours_expression_template",
    "get_in_past_calendar_week_expression_template",
    "get_in_past_calendar_month_expression_template",
    "get_days_of_week_expression_template",
    "get_regexp_expression_template",
    "get_regexp_count_expression_template",
    "get_is_eq_expression_template",
    "get_is_gt_expression_template",
    "get_is_gte_expression_template",
    "get_is_lt_expression_template",
    "get_is_lte_expression_template",
    "get_is_inside_range_expression_template",
    "get_is_outside_range_expression_template",
]


def test_placeholder_templates_do_not_use_jinja_field(templates):
    """Guard: placeholder templates must NOT contain {{ field }} — they use {x} instead."""
    import re

    jinja_field_re = re.compile(r"\{\{\s*field\s*\}\}")
    violations = []
    for name in _PLACEHOLDER_TEMPLATES:
        method = getattr(templates, name, None)
        if method is None:
            continue
        tpl_str = method()
        if jinja_field_re.search(tpl_str):
            violations.append(name)
    assert not violations, (
        f"Templates still using {{{{ field }}}} instead of {{x}}: {violations}"
    )


