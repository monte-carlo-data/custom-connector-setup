from datetime import datetime

import pytest

pytestmark = [pytest.mark.query_language]


@pytest.mark.template(func="unpivot_template")
def test_unpivot(ql):
    """Columns to rows transformation."""
    data = [{"a": 1, "b": 2, "c": 3}]
    cte, alias = ql.make_data_source(data)
    from_clause = ql.render(ql.templates.add_from_clause_template, table=alias)
    select_clause = ql.render(ql.templates.add_select_clause_template, fields="a, b, c")
    inner_query = f"{select_clause} {from_clause}"

    unpivot_expr = ql.render(
        ql.templates.unpivot_template,
        query=inner_query,
        columns=["a", "b", "c"],
        name_column="metric_name",
        value_column="metric_value",
    )
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    query = f"{cte} SELECT {count_expr} FROM ({unpivot_expr}) AS unpivoted"
    result = ql.execute_scalar(query)
    assert int(result) == 3


@pytest.mark.template(func="get_array_length_func_template")
def test_array_length(ql):
    """Array length check."""
    arr = ql.render(ql.templates.array_expr_template, values=[1, 2, 3])
    arr_len = ql.render(ql.templates.get_array_length_func_template, field=arr)
    result = ql.select_expression(arr_len)
    assert int(result) == 3


@pytest.mark.template(func="max_time_func_template")
def test_max_time(ql):
    """MAX of timestamps."""
    lit1 = ql.render(ql.templates.literal_datetime_template, value=datetime(2024, 1, 1))
    lit2 = ql.render(ql.templates.literal_datetime_template, value=datetime(2024, 6, 15))

    alias_1 = ql.render(ql.templates.alias_field_template, field=lit1, alias="ts_val")
    alias_2 = ql.render(ql.templates.alias_field_template, field=lit2, alias="ts_val")
    sel1 = ql.render(ql.templates.add_select_clause_template, fields=alias_1)
    sel2 = ql.render(ql.templates.add_select_clause_template, fields=alias_2)
    unioned = ql.render(ql.templates.union_queries_template, queries=[sel1, sel2])
    cte = ql.render(ql.templates.build_cte_template, alias="ts_data", query=unioned)

    max_expr = ql.render(ql.templates.max_time_func_template, field="ts_val")
    from_clause = ql.render(ql.templates.add_from_clause_template, table="ts_data")
    select_clause = ql.render(ql.templates.add_select_clause_template, fields=max_expr)
    to_str = ql.render(ql.templates.cast_to_string_func_template, field=max_expr)
    select_clause = ql.render(ql.templates.add_select_clause_template, fields=to_str)

    query = f"{cte} {select_clause} {from_clause}"
    result = str(ql.execute_scalar(query))
    assert "2024" in result
    assert "06" in result or "Jun" in result


@pytest.mark.template(func="get_is_timestamp_expression_template")
def test_is_timestamp_expression(ql):
    """Validate timestamp string detection."""
    escaped_valid = ql.render(ql.templates.escape_string_template, value="2024-01-15 10:30:00")
    valid_lit = ql.render(ql.templates.string_literal_template, value=escaped_valid)
    is_ts = ql.render(ql.templates.get_is_timestamp_expression_template, field=valid_lit)
    case_expr = ql.render(
        ql.templates.get_case_when_func_template,
        condition=is_ts, true_value="1", false_value="0",
    )
    result = ql.select_expression(case_expr)
    assert int(result) == 1


@pytest.mark.template(func="get_epoch_seconds_expression_template")
def test_epoch_seconds(ql):
    """Verify epoch seconds conversion."""
    escaped = ql.render(ql.templates.escape_string_template, value="2024-01-01 00:00:00")
    literal = ql.render(ql.templates.string_literal_template, value=escaped)
    ts_cast = ql.render(ql.templates.default_cast_to_timestamp_func_template, field=literal)
    epoch_expr = ql.render(ql.templates.get_epoch_seconds_expression_template, field=ts_cast)
    result = ql.select_expression(epoch_expr)
    # 2024-01-01 00:00:00 UTC = 1704067200 epoch seconds
    assert abs(int(float(result)) - 1704067200) < 86400  # within 1 day tolerance for TZ
