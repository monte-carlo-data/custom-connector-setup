from datetime import datetime, timedelta, timezone, date

import pytest

pytestmark = [pytest.mark.query_language]


@pytest.mark.tier("standard")
@pytest.mark.template(func="current_timestamp_func_template")
def test_current_timestamp(ql):
    """SELECT current_timestamp, verify within 120s of Python now."""
    ts_expr = ql.render(ql.templates.current_timestamp_func_template)
    epoch_expr = ql.render(ql.templates.convert_to_unix_timestamp_func_template, field=ts_expr)
    result = ql.select_expression(epoch_expr)
    now_epoch = datetime.now(tz=timezone.utc).timestamp()
    assert abs(float(result) - now_epoch) < 120


@pytest.mark.tier("standard")
@pytest.mark.template(func="current_date_func_template")
def test_current_date(ql):
    """SELECT current_date, verify matches today (+-1 day for TZ)."""
    date_expr = ql.render(ql.templates.current_date_func_template)
    to_str = ql.render(ql.templates.cast_to_string_func_template, field=date_expr)
    result = str(ql.select_expression(to_str))
    today = date.today()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    assert any(d.isoformat() in result for d in [yesterday, today, tomorrow])


@pytest.mark.tier("standard")
@pytest.mark.template(func="get_is_yesterday_expression_template")
def test_is_yesterday(ql):
    """CTE with yesterday_noon + today_noon timestamps, COUNT WHERE is_yesterday -> 1."""
    now = datetime.now(tz=timezone.utc)
    yesterday_noon = (now - timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    today_noon = now.replace(hour=12, minute=0, second=0, microsecond=0)

    yesterday_lit = ql.render(ql.templates.literal_datetime_template, value=yesterday_noon)
    today_lit = ql.render(ql.templates.literal_datetime_template, value=today_noon)

    # Build inline values with actual timestamps
    ts_alias_1 = ql.render(ql.templates.alias_field_template, field=yesterday_lit, alias="ts_val")
    ts_alias_2 = ql.render(ql.templates.alias_field_template, field=today_lit, alias="ts_val")
    sel1 = ql.render(ql.templates.add_select_clause_template, fields=ts_alias_1)
    sel2 = ql.render(ql.templates.add_select_clause_template, fields=ts_alias_2)
    unioned = ql.render(ql.templates.union_queries_template, queries=[sel1, sel2])
    ts_cte = ql.render(ql.templates.build_cte_template, alias="ts_data", query=unioned)

    is_yesterday = ql.render(ql.templates.get_is_yesterday_expression_template, field="ts_val")
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    ts_from = ql.render(ql.templates.add_from_clause_template, table="ts_data")
    ts_select = ql.render(ql.templates.add_select_clause_template, fields=count_expr)

    query = f"{ts_cte} {ts_select} {ts_from} WHERE {is_yesterday}"
    result = ql.execute_scalar(query)
    assert int(result) == 1


@pytest.mark.tier("standard")
@pytest.mark.template(func="get_in_past_days_expression_template")
def test_in_past_days(ql):
    """CTE with 2_days_ago + 30_days_ago, past 7 days -> 1."""
    now = datetime.now(tz=timezone.utc)
    two_days_ago = now - timedelta(days=2)
    thirty_days_ago = now - timedelta(days=30)

    lit_2d = ql.render(ql.templates.literal_datetime_template, value=two_days_ago)
    lit_30d = ql.render(ql.templates.literal_datetime_template, value=thirty_days_ago)

    alias_2d = ql.render(ql.templates.alias_field_template, field=lit_2d, alias="ts_val")
    alias_30d = ql.render(ql.templates.alias_field_template, field=lit_30d, alias="ts_val")
    sel1 = ql.render(ql.templates.add_select_clause_template, fields=alias_2d)
    sel2 = ql.render(ql.templates.add_select_clause_template, fields=alias_30d)
    unioned = ql.render(ql.templates.union_queries_template, queries=[sel1, sel2])
    cte = ql.render(ql.templates.build_cte_template, alias="ts_data", query=unioned)

    past_days = ql.render(ql.templates.get_in_past_days_expression_template, field="ts_val", days=7)
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    from_clause = ql.render(ql.templates.add_from_clause_template, table="ts_data")
    select_clause = ql.render(ql.templates.add_select_clause_template, fields=count_expr)

    query = f"{cte} {select_clause} {from_clause} WHERE {past_days}"
    result = ql.execute_scalar(query)
    assert int(result) == 1


@pytest.mark.tier("standard")
@pytest.mark.template(func="add_days_func_template")
def test_add_days(ql):
    """current_date + 1 > current_date -> true."""
    date_expr = ql.render(ql.templates.current_date_func_template)
    plus_one = ql.render(ql.templates.add_days_func_template, field=date_expr, days=1)
    gt_expr = ql.render(ql.templates.get_is_gt_expression_template, field1=plus_one, field2=date_expr)
    case_expr = ql.render(
        ql.templates.get_case_when_func_template,
        condition=gt_expr, true_value="1", false_value="0",
    )
    result = ql.select_expression(case_expr)
    assert int(result) == 1


@pytest.mark.tier("standard")
@pytest.mark.template(func="add_hours_timestamp_func_template")
def test_add_hours_timestamp(ql):
    """current_timestamp + 3h > current_timestamp -> true."""
    ts_expr = ql.render(ql.templates.current_timestamp_func_template)
    plus_3h = ql.render(ql.templates.add_hours_timestamp_func_template, field=ts_expr, hours=3)
    gt_expr = ql.render(ql.templates.get_is_gt_expression_template, field1=plus_3h, field2=ts_expr)
    case_expr = ql.render(
        ql.templates.get_case_when_func_template,
        condition=gt_expr, true_value="1", false_value="0",
    )
    result = ql.select_expression(case_expr)
    assert int(result) == 1


@pytest.mark.tier("standard")
@pytest.mark.template(func="time_truncate_func_template")
def test_time_truncate(ql):
    """Truncate timestamp to DAY, verify time zeroed."""
    escaped = ql.render(ql.templates.escape_string_template, value="2024-06-15 14:30:45")
    literal = ql.render(ql.templates.string_literal_template, value=escaped)
    ts_cast = ql.render(ql.templates.default_cast_to_timestamp_func_template, field=literal)
    truncated = ql.render(ql.templates.time_truncate_func_template, field=ts_cast, truncation="DAY")
    to_str = ql.render(ql.templates.cast_to_string_func_template, field=truncated)
    result = str(ql.select_expression(to_str))
    assert "2024" in result
    assert "14:30" not in result


@pytest.mark.tier("standard")
@pytest.mark.template(func="get_date_diff_func_template")
def test_date_diff(ql):
    """Diff between two dates, verify expected days."""
    escaped1 = ql.render(ql.templates.escape_string_template, value="2024-01-01 00:00:00")
    escaped2 = ql.render(ql.templates.escape_string_template, value="2024-01-11 00:00:00")
    lit1 = ql.render(ql.templates.string_literal_template, value=escaped1)
    lit2 = ql.render(ql.templates.string_literal_template, value=escaped2)
    ts1 = ql.render(ql.templates.default_cast_to_timestamp_func_template, field=lit1)
    ts2 = ql.render(ql.templates.default_cast_to_timestamp_func_template, field=lit2)
    diff_expr = ql.render(ql.templates.get_date_diff_func_template, field1=ts1, field2=ts2, unit="day")
    result = ql.select_expression(diff_expr)
    assert abs(int(result)) == 10


@pytest.mark.tier("standard")
@pytest.mark.template(func="convert_to_utc_template")
def test_convert_to_utc(ql):
    """Convert TZ timestamp, verify UTC result."""
    ts_expr = ql.render(ql.templates.current_timestamp_func_template)
    utc_expr = ql.render(ql.templates.convert_to_utc_template, field=ts_expr)
    to_str = ql.render(ql.templates.cast_to_string_func_template, field=utc_expr)
    result = str(ql.select_expression(to_str))
    assert result is not None and len(result) > 0


@pytest.mark.tier("standard")
@pytest.mark.template(func="date_literal_template")
def test_date_literal(ql):
    """Create date literal, verify roundtrip."""
    test_date = date(2024, 3, 15)
    lit = ql.render(ql.templates.date_literal_template, value=test_date)
    to_str = ql.render(ql.templates.cast_to_string_func_template, field=lit)
    result = str(ql.select_expression(to_str))
    assert "2024" in result
    assert "03" in result or "3" in result
    assert "15" in result


@pytest.mark.tier("standard")
@pytest.mark.template(func="get_in_past_hours_expression_template")
def test_in_past_hours(ql):
    """CTE with 1h_ago + 48h_ago, past 24h -> 1."""
    now = datetime.now(tz=timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    forty_eight_hours_ago = now - timedelta(hours=48)

    lit_1h = ql.render(ql.templates.literal_datetime_template, value=one_hour_ago)
    lit_48h = ql.render(ql.templates.literal_datetime_template, value=forty_eight_hours_ago)

    alias_1h = ql.render(ql.templates.alias_field_template, field=lit_1h, alias="ts_val")
    alias_48h = ql.render(ql.templates.alias_field_template, field=lit_48h, alias="ts_val")
    sel1 = ql.render(ql.templates.add_select_clause_template, fields=alias_1h)
    sel2 = ql.render(ql.templates.add_select_clause_template, fields=alias_48h)
    unioned = ql.render(ql.templates.union_queries_template, queries=[sel1, sel2])
    cte = ql.render(ql.templates.build_cte_template, alias="ts_data", query=unioned)

    past_hours = ql.render(ql.templates.get_in_past_hours_expression_template, field="ts_val", hours=24)
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    from_clause = ql.render(ql.templates.add_from_clause_template, table="ts_data")
    select_clause = ql.render(ql.templates.add_select_clause_template, fields=count_expr)

    query = f"{cte} {select_clause} {from_clause} WHERE {past_hours}"
    result = ql.execute_scalar(query)
    assert int(result) == 1
