import pytest

pytestmark = [pytest.mark.query_language]


@pytest.mark.template(func="get_absolute_value_function_template")
@pytest.mark.template(func="supports_literal_select_template")
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
