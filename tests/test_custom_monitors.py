import pytest

pytestmark = [pytest.mark.custom_monitors, pytest.mark.capability("supports_custom_sql_monitor")]


def test_execute_simple_query(integration):
    """Test that a simple query can be executed and returns results."""
    results = integration.execute_and_fetch_all("SELECT 1")
    assert len(results) > 0, "Simple query returned no results."
    assert results[0][0] == 1


@pytest.mark.template(func="transform_into_count_query_template")
def test_transform_into_count_query(ql):
    """Wrap a SELECT in COUNT(*), execute, verify count."""
    data = [{"val": 1}, {"val": 2}, {"val": 3}]
    cte, alias = ql.make_data_source(data)
    all_fields = ql.render(ql.templates.all_fields_expression_template)
    from_clause = ql.render(ql.templates.add_from_clause_template, table=alias)
    select_clause = ql.render(ql.templates.add_select_clause_template, fields=all_fields)
    inner_query = f"{select_clause} {from_clause}"

    count_query = ql.render(
        ql.templates.transform_into_count_query_template,
        query=inner_query,
    )
    query = f"{cte} {count_query}"
    result = ql.execute_scalar(query)
    assert int(result) == 3


@pytest.mark.template(func="add_row_limit_template")
def test_add_row_limit(ql):
    """Add LIMIT to query, verify row count capped."""
    data = [{"val": i} for i in range(10)]
    cte, alias = ql.make_data_source(data)
    all_fields = ql.render(ql.templates.all_fields_expression_template)
    from_clause = ql.render(ql.templates.add_from_clause_template, table=alias)
    select_clause = ql.render(ql.templates.add_select_clause_template, fields=all_fields)
    inner_query = f"{select_clause} {from_clause}"

    limited_query = ql.render(
        ql.templates.add_row_limit_template,
        query=inner_query,
        limit=5,
    )
    query = f"{cte} {limited_query}"
    rows = ql.execute(query)
    assert len(rows) == 5


@pytest.mark.template(func="get_count_all_expression_template")
def test_count_all_expression(ql):
    """COUNT(*) on CTE, verify row count."""
    data = [{"val": 1}, {"val": 2}, {"val": 3}, {"val": 4}]
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    result = ql.select_from_data_source(data, count_expr)
    assert int(result) == 4
