import pytest

pytestmark = [pytest.mark.query_language]


@pytest.mark.tier("standard")
@pytest.mark.template(func="get_isnan_expression_template")
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
