import pytest

pytestmark = [pytest.mark.query_language]


@pytest.mark.tier("standard")
@pytest.mark.template(func="get_is_eq_expression_template")
def test_equality(ql):
    """CTE [{x:10,y:10},{x:10,y:20}], COUNT WHERE x=y -> 1."""
    data = [{"x": 10, "y": 10}, {"x": 10, "y": 20}]
    eq_expr = ql.render(ql.templates.get_is_eq_expression_template, field1="x", field2="y")
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    result = ql.select_from_data_source(data, count_expr, condition=eq_expr)
    assert int(result) == 1


@pytest.mark.tier("standard")
@pytest.mark.template(func="get_is_gt_expression_template")
def test_gt_and_lt(ql):
    """CTE [5,10,15], COUNT WHERE >8 -> 2, <8 -> 1."""
    data = [{"val": 5}, {"val": 10}, {"val": 15}]
    count_expr = ql.render(ql.templates.get_count_all_expression_template)

    gt_expr = ql.render(ql.templates.get_is_gt_expression_template, field1="val", field2="8")
    result_gt = ql.select_from_data_source(data, count_expr, condition=gt_expr)
    assert int(result_gt) == 2

    lt_expr = ql.render(ql.templates.get_is_lt_expression_template, field1="val", field2="8")
    result_lt = ql.select_from_data_source(data, count_expr, condition=lt_expr)
    assert int(result_lt) == 1


@pytest.mark.tier("standard")
@pytest.mark.template(func="get_is_gte_expression_template")
def test_gte_and_lte(ql):
    """Similar with boundary values."""
    data = [{"val": 5}, {"val": 10}, {"val": 15}]
    count_expr = ql.render(ql.templates.get_count_all_expression_template)

    gte_expr = ql.render(ql.templates.get_is_gte_expression_template, field1="val", field2="10")
    result_gte = ql.select_from_data_source(data, count_expr, condition=gte_expr)
    assert int(result_gte) == 2

    lte_expr = ql.render(ql.templates.get_is_lte_expression_template, field1="val", field2="10")
    result_lte = ql.select_from_data_source(data, count_expr, condition=lte_expr)
    assert int(result_lte) == 2


@pytest.mark.tier("standard")
@pytest.mark.template(func="get_is_inside_range_expression_template")
def test_inside_range(ql):
    """CTE [1,5,10,15], range 5-10 -> 2."""
    data = [{"val": 1}, {"val": 5}, {"val": 10}, {"val": 15}]
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    range_expr = ql.render(
        ql.templates.get_is_inside_range_expression_template,
        field="val", lower="5", upper="10",
    )
    result = ql.select_from_data_source(data, count_expr, condition=range_expr)
    assert int(result) == 2


@pytest.mark.tier("standard")
@pytest.mark.template(func="get_is_outside_range_expression_template")
def test_outside_range(ql):
    """Same data, outside 5-10 -> 2."""
    data = [{"val": 1}, {"val": 5}, {"val": 10}, {"val": 15}]
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    range_expr = ql.render(
        ql.templates.get_is_outside_range_expression_template,
        field="val", lower="5", upper="10",
    )
    result = ql.select_from_data_source(data, count_expr, condition=range_expr)
    assert int(result) == 2


@pytest.mark.tier("standard")
@pytest.mark.template(func="is_null_template")
def test_null_checks(ql):
    """CTE [1,NULL,3], IS NULL -> 1, IS NOT NULL -> 2."""
    data = [{"val": 1}, {"val": None}, {"val": 3}]
    count_expr = ql.render(ql.templates.get_count_all_expression_template)

    null_expr = ql.render(ql.templates.is_null_template, field="val")
    result_null = ql.select_from_data_source(data, count_expr, condition=null_expr)
    assert int(result_null) == 1

    not_null_expr = ql.render(ql.templates.is_not_null_template, field="val")
    result_not_null = ql.select_from_data_source(data, count_expr, condition=not_null_expr)
    assert int(result_not_null) == 2
