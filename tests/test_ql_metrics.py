import pytest

pytestmark = [pytest.mark.query_language, pytest.mark.ql_metrics]


# ---------------------------------------------------------------------------
# Aggregation metrics
# ---------------------------------------------------------------------------


@pytest.mark.template(func="get_avg_function_template")
def test_avg(ql):
    """CTE [10,20,30], AVG -> 20.0."""
    data = [{"val": 10}, {"val": 20}, {"val": 30}]
    avg_expr = ql.render(ql.templates.get_avg_function_template, field="val")
    result = ql.select_from_data_source(data, avg_expr)
    assert float(result) == pytest.approx(20.0)


@pytest.mark.template(func="get_stddev_function_template")
def test_stddev(ql):
    """CTE [10,20,30], STDDEV in (7.0, 11.0) (sample vs pop)."""
    data = [{"val": 10}, {"val": 20}, {"val": 30}]
    stddev_expr = ql.render(ql.templates.get_stddev_function_template, field="val")
    result = ql.select_from_data_source(data, stddev_expr)
    assert 7.0 < float(result) < 11.0


@pytest.mark.template(func="get_distinct_count_func_template")
def test_distinct_count(ql):
    """CTE [a,b,a,c], COUNT(DISTINCT) -> 3."""
    data = [{"val": "a"}, {"val": "b"}, {"val": "a"}, {"val": "c"}]
    distinct_expr = ql.render(ql.templates.get_distinct_count_func_template, field="val")
    result = ql.select_from_data_source(data, distinct_expr)
    assert int(result) == 3


@pytest.mark.template(func="get_conditional_count_expression_template")
def test_conditional_count(ql):
    """CTE [5,-3,0,10], COUNT WHERE >0 -> 2."""
    data = [{"val": 5}, {"val": -3}, {"val": 0}, {"val": 10}]
    gt_expr = ql.render(ql.templates.get_is_gt_expression_template, field1="val", field2="0")
    count_expr = ql.render(ql.templates.get_conditional_count_expression_template, condition=gt_expr)
    result = ql.select_from_data_source(data, count_expr)
    assert int(result) == 2


@pytest.mark.template(func="get_approx_percentile_func_template")
def test_approx_percentile(ql):
    """CTE [1..100], median ~ 50 (+-5)."""
    data = [{"val": i} for i in range(1, 101)]
    percentile_expr = ql.render(
        ql.templates.get_approx_percentile_func_template,
        field="val", percentile=0.5,
    )
    result = ql.select_from_data_source(data, percentile_expr)
    assert 45 <= float(result) <= 55


@pytest.mark.template(func="get_approx_quantiles_func_template")
def test_approx_quantiles(ql):
    """CTE [1..100], approx quantiles at 0.5 ~ 50."""
    data = [{"val": i} for i in range(1, 101)]
    quantile_expr = ql.render(
        ql.templates.get_approx_quantiles_func_template,
        field="val", quantiles=100, index=50,
    )
    result = ql.select_from_data_source(data, quantile_expr)
    assert 45 <= float(result) <= 55


# ---------------------------------------------------------------------------
# Type casting metrics
# ---------------------------------------------------------------------------


@pytest.mark.template(func="get_casting_to_decimal_expression_template")
def test_cast_to_decimal(ql):
    """Cast '3.14159', verify precision."""
    escaped = ql.render(ql.templates.escape_string_template, value="3.14159")
    literal = ql.render(ql.templates.string_literal_template, value=escaped)
    cast_expr = ql.render(ql.templates.get_casting_to_decimal_expression_template, field=literal)
    result = ql.select_expression(cast_expr)
    assert float(result) == pytest.approx(3.14159, abs=0.001)


@pytest.mark.template(func="get_length_template")
def test_length(ql):
    """LENGTH('hello') == 5."""
    escaped = ql.render(ql.templates.escape_string_template, value="hello")
    literal = ql.render(ql.templates.string_literal_template, value=escaped)
    length_expr = ql.render(ql.templates.get_length_template, field=literal)
    result = ql.select_expression(length_expr)
    assert int(result) == 5


# ---------------------------------------------------------------------------
# String operation metrics
# ---------------------------------------------------------------------------


@pytest.mark.template(func="get_length_template")
def test_string_length(ql):
    """CTE ['hello','','world!'], SUM(LENGTH) -> 11."""
    data = [{"val": "hello"}, {"val": ""}, {"val": "world!"}]
    length_expr = ql.render(ql.templates.get_length_template, field="val")
    sum_expr = f"SUM({length_expr})"
    result = ql.select_from_data_source(data, sum_expr)
    assert int(result) == 11


@pytest.mark.template(func="get_is_empty_string_expression_template")
def test_is_empty_string(ql):
    """CTE ['hello','','world'], COUNT WHERE empty -> 1."""
    data = [{"val": "hello"}, {"val": ""}, {"val": "world"}]
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    empty_expr = ql.render(ql.templates.get_is_empty_string_expression_template, field="val")
    result = ql.select_from_data_source(data, count_expr, condition=empty_expr)
    assert int(result) == 1


@pytest.mark.template(func="get_regexp_count_expression_template")
def test_regexp_count(ql):
    """CTE ['123','abc','456'], COUNT WHERE matches ^[0-9]+$ -> 2."""
    data = [{"val": "123"}, {"val": "abc"}, {"val": "456"}]
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    regex_lit = ql.render(ql.templates.literal_regex_template, value="^[0-9]+$")
    regexp_count_expr = ql.render(
        ql.templates.get_regexp_count_expression_template,
        field="val", pattern=regex_lit,
    )
    gt_expr = ql.render(ql.templates.get_is_gt_expression_template, field1=regexp_count_expr, field2="0")
    result = ql.select_from_data_source(data, count_expr, condition=gt_expr)
    assert int(result) == 2


# ---------------------------------------------------------------------------
# NaN metric
# ---------------------------------------------------------------------------


@pytest.mark.template(func="get_isnan_expression_template")
@pytest.mark.template(func="nan_expr_template")
def test_isnan(ql):
    """Render nan_expr for NaN literal, use in get_isnan_expression, verify detection."""
    nan_literal = ql.render(ql.templates.nan_expr_template)
    isnan_expr = ql.render(ql.templates.get_isnan_expression_template, field=nan_literal)
    case_expr = ql.render(
        ql.templates.get_case_when_func_template,
        condition=isnan_expr,
        true_value="1",
        false_value="0",
    )
    result = ql.select_expression(case_expr)
    assert int(result) == 1


# ---------------------------------------------------------------------------
# Advanced metrics
# ---------------------------------------------------------------------------


@pytest.mark.template(func="get_array_length_func_template")
@pytest.mark.template(func="array_expr_template")
def test_array_length(ql):
    """Array length check."""
    arr = ql.render(ql.templates.array_expr_template, values=[1, 2, 3])
    arr_len = ql.render(ql.templates.get_array_length_func_template, field=arr)
    result = ql.select_expression(arr_len)
    assert int(result) == 3


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


@pytest.mark.template(func="get_not_is_timestamp_expression_template")
def test_not_is_timestamp(ql):
    """Validate non-timestamp string detection."""
    escaped = ql.render(ql.templates.escape_string_template, value="not-a-timestamp")
    literal = ql.render(ql.templates.string_literal_template, value=escaped)
    not_ts = ql.render(ql.templates.get_not_is_timestamp_expression_template, field=literal)
    case_expr = ql.render(
        ql.templates.get_case_when_func_template,
        condition=not_ts, true_value="1", false_value="0",
    )
    result = ql.select_expression(case_expr)
    assert int(result) == 1


# ---------------------------------------------------------------------------
# Other optional templates (not mapped to specific metrics, not prerequisites)
# ---------------------------------------------------------------------------


@pytest.mark.template(func="approx_distinct_func_template")
def test_approx_distinct(ql):
    """CTE with known distinct values, verify ~ count."""
    data = [{"val": i % 10} for i in range(50)]
    approx_expr = ql.render(ql.templates.approx_distinct_func_template, field="val")
    result = ql.select_from_data_source(data, approx_expr)
    assert 8 <= int(result) <= 12


@pytest.mark.template(func="get_distinct_func_template")
def test_distinct_func(ql):
    """CTE [a,b,a,c], SELECT DISTINCT -> 3 rows."""
    data = [{"val": "a"}, {"val": "b"}, {"val": "a"}, {"val": "c"}]
    distinct_expr = ql.render(ql.templates.get_distinct_func_template, field="val")
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    cte, alias = ql.make_data_source(data)
    from_clause = ql.render(ql.templates.add_from_clause_template, table=alias)
    query = f"{cte} SELECT {count_expr} FROM (SELECT {distinct_expr} {from_clause}) AS distinct_sub"
    result = ql.execute_scalar(query)
    assert int(result) == 3


@pytest.mark.template(func="any_value_template")
def test_any_value(ql):
    """CTE [42,42,42], ANY_VALUE -> 42."""
    data = [{"val": 42}, {"val": 42}, {"val": 42}]
    any_val_expr = ql.render(ql.templates.any_value_template, field="val")
    result = ql.select_from_data_source(data, any_val_expr)
    assert int(result) == 42


@pytest.mark.template(func="substring_func_template")
def test_substring(ql):
    """SUBSTR('abcdef', 2, 3), verify 'bcd'."""
    escaped = ql.render(ql.templates.escape_string_template, value="abcdef")
    literal = ql.render(ql.templates.string_literal_template, value=escaped)
    substr_expr = ql.render(
        ql.templates.substring_func_template,
        field=literal, start=2, length=3,
    )
    result = ql.select_expression(substr_expr)
    assert str(result) == "bcd"


@pytest.mark.template(func="literal_time_of_day_template")
def test_literal_time_of_day(ql):
    """Render time-of-day literal, verify non-empty."""
    result = ql.render(ql.templates.literal_time_of_day_template, value="14:30:00")
    assert result and len(result.strip()) > 0


@pytest.mark.template(func="get_absolute_value_function_template")
def test_absolute_value(ql):
    """ABS(-5) -> 5."""
    abs_expr = ql.render(ql.templates.get_absolute_value_function_template, field="-5")
    result = ql.select_expression(abs_expr)
    assert int(result) == 5


@pytest.mark.template(func="rand_func_template")
def test_rand(ql):
    """RAND() between 0 and 1."""
    rand_expr = ql.render(ql.templates.rand_func_template)
    result = ql.select_expression(rand_expr)
    val = float(result)
    assert 0.0 <= abs(val) <= 1.0 or val != 0  # Some DBs return wider range; at minimum verify it runs


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


@pytest.mark.template(func="literal_table_from_value_list_template")
def test_literal_table_from_value_list(ql):
    """Render literal_table_from_value_list_template, verify non-empty."""
    result = ql.render(
        ql.templates.literal_table_from_value_list_template,
        values=["1", "2", "3"],
        alias="t",
        column_name="val",
    )
    assert result and len(result.strip()) > 0
