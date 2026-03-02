import pytest

pytestmark = [pytest.mark.query_language]


@pytest.mark.tier("standard")
@pytest.mark.template(func="get_length_template")
def test_string_length(ql):
    """CTE ['hello','','world!'], SUM(LENGTH) -> 11."""
    data = [{"val": "hello"}, {"val": ""}, {"val": "world!"}]
    length_expr = ql.render(ql.templates.get_length_template, field="val")
    sum_expr = f"SUM({length_expr})"
    result = ql.select_from_data_source(data, sum_expr)
    assert int(result) == 11


@pytest.mark.tier("standard")
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


@pytest.mark.tier("standard")
@pytest.mark.template(func="get_is_empty_string_expression_template")
def test_is_empty_string(ql):
    """CTE ['hello','','world'], COUNT WHERE empty -> 1."""
    data = [{"val": "hello"}, {"val": ""}, {"val": "world"}]
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    empty_expr = ql.render(ql.templates.get_is_empty_string_expression_template, field="val")
    result = ql.select_from_data_source(data, count_expr, condition=empty_expr)
    assert int(result) == 1


@pytest.mark.tier("standard")
@pytest.mark.template(func="get_regexp_expression_template")
def test_regexp_match(ql):
    """CTE emails, COUNT WHERE matches email pattern -> 2."""
    data = [
        {"val": "user@example.com"},
        {"val": "not-an-email"},
        {"val": "admin@test.org"},
    ]
    count_expr = ql.render(ql.templates.get_count_all_expression_template)
    regex_lit = ql.render(ql.templates.literal_regex_template, value="[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}")
    regexp_expr = ql.render(
        ql.templates.get_regexp_expression_template,
        field="val", pattern=regex_lit,
    )
    result = ql.select_from_data_source(data, count_expr, condition=regexp_expr)
    assert int(result) == 2


@pytest.mark.tier("standard")
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
