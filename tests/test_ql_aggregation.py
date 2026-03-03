import pytest

pytestmark = [pytest.mark.query_language]


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


@pytest.mark.template(func="get_safe_divide_template")
def test_safe_divide(ql):
    """10/2 -> 5.0, 10/0 -> NULL or 0 (no error)."""
    safe_div = ql.render(ql.templates.get_safe_divide_template, numerator="10", denominator="2")
    result = ql.select_expression(safe_div)
    assert float(result) == pytest.approx(5.0)

    # Division by zero should not error
    safe_div_zero = ql.render(ql.templates.get_safe_divide_template, numerator="10", denominator="0")
    result_zero = ql.select_expression(safe_div_zero)
    assert result_zero is None or float(result_zero) == 0


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


@pytest.mark.template(func="any_value_template")
def test_any_value(ql):
    """CTE [42,42,42], ANY_VALUE -> 42."""
    data = [{"val": 42}, {"val": 42}, {"val": 42}]
    any_val_expr = ql.render(ql.templates.any_value_template, field="val")
    result = ql.select_from_data_source(data, any_val_expr)
    assert int(result) == 42
