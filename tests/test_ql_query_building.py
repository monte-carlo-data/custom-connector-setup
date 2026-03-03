import pytest

pytestmark = [pytest.mark.query_language]


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
    from_clause = ql.render(ql.templates.add_from_clause_template, table=alias)
    select_clause = ql.render(ql.templates.add_select_clause_template, fields="col_a, col_b")
    order = ql.render(ql.templates.ascending_order_template, field="col_a")
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
    from_clause = ql.render(ql.templates.add_from_clause_template, table=alias)
    select_clause = ql.render(ql.templates.add_select_clause_template, fields="val")

    # ASC
    asc_order = ql.render(ql.templates.ascending_order_template, field="val")
    query_asc = f"{cte} {select_clause} {from_clause} ORDER BY {asc_order}"
    rows_asc = ql.execute(query_asc)
    assert [r[0] for r in rows_asc] == [1, 2, 3]

    # DESC
    desc_order = ql.render(ql.templates.descending_order_template, field="val")
    query_desc = f"{cte} {select_clause} {from_clause} ORDER BY {desc_order}"
    rows_desc = ql.execute(query_desc)
    assert [r[0] for r in rows_desc] == [3, 2, 1]


@pytest.mark.template(func="string_literal_template")
@pytest.mark.template(func="escape_string_template")
def test_string_literal_with_escaping(ql):
    """SELECT literal with single quote, verify "it's a test"."""
    escaped = ql.render(ql.templates.escape_string_template, value="it's a test")
    literal = ql.render(ql.templates.string_literal_template, value=escaped)
    result = ql.select_expression(literal)
    assert result == "it's a test"


@pytest.mark.template(func="get_case_when_func_template")
def test_case_when(ql):
    """CASE WHEN val > 5 THEN 'big' ELSE 'small', verify."""
    data = [{"val": 10}, {"val": 2}]
    gt_expr = ql.render(ql.templates.get_is_gt_expression_template, field1="val", field2="5")
    case_expr = ql.render(
        ql.templates.get_case_when_func_template,
        condition=gt_expr,
        true_value="'big'",
        false_value="'small'",
    )
    cte, alias = ql.make_data_source(data)
    from_clause = ql.render(ql.templates.add_from_clause_template, table=alias)
    select_clause = ql.render(ql.templates.add_select_clause_template, fields=case_expr)
    order = ql.render(ql.templates.descending_order_template, field="val")
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
    from_clause = ql.render(ql.templates.add_from_clause_template, table=alias)
    select_clause = ql.render(ql.templates.add_select_clause_template, fields=aliased)
    query = f"{cte} {select_clause} {from_clause}"
    rows = ql.execute(query)
    assert rows[0][0] == 1


@pytest.mark.template(func="negate_expression_template")
def test_negate_expression(ql):
    """NOT(TRUE) -> false."""
    negated = ql.render(ql.templates.negate_expression_template, expression="TRUE")
    case_expr = ql.render(
        ql.templates.get_case_when_func_template,
        condition=negated,
        true_value="1",
        false_value="0",
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
    from_clause = ql.render(ql.templates.add_from_clause_template, table=alias)
    select_clause = ql.render(ql.templates.add_select_clause_template, fields=all_fields)
    query = f"{cte} {select_clause} {from_clause}"
    rows = ql.execute(query)
    assert len(rows) == 1
    assert len(rows[0]) >= 2


@pytest.mark.template(func="get_field_or_alias_template")
def test_field_or_alias(ql):
    """Render get_field_or_alias_template, verify non-empty output."""
    result = ql.render(ql.templates.get_field_or_alias_template, field="my_col", alias="my_alias")
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
