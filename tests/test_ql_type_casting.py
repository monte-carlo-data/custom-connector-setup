import pytest

pytestmark = [pytest.mark.query_language]


@pytest.mark.template(func="get_casting_to_numeric_expression_template")
def test_cast_to_numeric(ql):
    """Cast '42.5' to numeric, verify 42.5."""
    escaped = ql.render(ql.templates.escape_string_template, value="42.5")
    literal = ql.render(ql.templates.string_literal_template, value=escaped)
    cast_expr = ql.render(ql.templates.get_casting_to_numeric_expression_template, field=literal)
    result = ql.select_expression(cast_expr)
    assert float(result) == pytest.approx(42.5)


@pytest.mark.template(func="cast_to_string_func_template")
def test_cast_to_string(ql):
    """Cast 123 to string, verify '123'."""
    cast_expr = ql.render(ql.templates.cast_to_string_func_template, field="123")
    result = ql.select_expression(cast_expr)
    assert str(result).strip() == "123"


@pytest.mark.template(func="get_casting_to_decimal_expression_template")
def test_cast_to_decimal(ql):
    """Cast '3.14159', verify precision."""
    escaped = ql.render(ql.templates.escape_string_template, value="3.14159")
    literal = ql.render(ql.templates.string_literal_template, value=escaped)
    cast_expr = ql.render(ql.templates.get_casting_to_decimal_expression_template, field=literal)
    result = ql.select_expression(cast_expr)
    assert float(result) == pytest.approx(3.14159, abs=0.001)


@pytest.mark.template(func="default_cast_to_timestamp_func_template")
def test_cast_to_timestamp(ql):
    """Cast string to timestamp, verify date parts."""
    escaped = ql.render(ql.templates.escape_string_template, value="2024-06-15 10:30:00")
    literal = ql.render(ql.templates.string_literal_template, value=escaped)
    cast_expr = ql.render(ql.templates.default_cast_to_timestamp_func_template, field=literal)
    to_str = ql.render(ql.templates.cast_to_string_func_template, field=cast_expr)
    result = str(ql.select_expression(to_str))
    assert "2024" in result
    assert "06" in result or "Jun" in result
    assert "15" in result


@pytest.mark.template(func="literal_value_template")
def test_literal_value_int(ql):
    """SELECT literal(42), verify 42."""
    literal = ql.render(ql.templates.literal_value_template, value="42")
    result = ql.select_expression(literal)
    assert int(result) == 42


@pytest.mark.template(func="get_length_template")
def test_length(ql):
    """LENGTH('hello') == 5."""
    escaped = ql.render(ql.templates.escape_string_template, value="hello")
    literal = ql.render(ql.templates.string_literal_template, value=escaped)
    length_expr = ql.render(ql.templates.get_length_template, field=literal)
    result = ql.select_expression(length_expr)
    assert int(result) == 5


@pytest.mark.template(func="cast_string_to_timestamp_template")
def test_cast_string_to_timestamp(ql):
    """Cast string to timestamp, verify date parts."""
    escaped = ql.render(ql.templates.escape_string_template, value="2024-06-15 10:30:00")
    literal = ql.render(ql.templates.string_literal_template, value=escaped)
    cast_expr = ql.render(ql.templates.cast_string_to_timestamp_template, field=literal)
    to_str = ql.render(ql.templates.cast_to_string_func_template, field=cast_expr)
    result = str(ql.select_expression(to_str))
    assert "2024" in result
    assert "15" in result


@pytest.mark.template(func="cast_numeric_to_timestamp_template")
def test_cast_numeric_to_timestamp(ql):
    """Cast numeric epoch to timestamp, verify result contains date parts."""
    # 1718438400 = 2024-06-15 08:00:00 UTC
    cast_expr = ql.render(ql.templates.cast_numeric_to_timestamp_template, field="1718438400")
    to_str = ql.render(ql.templates.cast_to_string_func_template, field=cast_expr)
    result = str(ql.select_expression(to_str))
    assert "2024" in result


@pytest.mark.template(func="cast_date_to_timestamp_template")
def test_cast_date_to_timestamp(ql):
    """Cast date to timestamp."""
    date_expr = ql.render(ql.templates.current_date_func_template)
    cast_expr = ql.render(ql.templates.cast_date_to_timestamp_template, field=date_expr)
    to_str = ql.render(ql.templates.cast_to_string_func_template, field=cast_expr)
    result = str(ql.select_expression(to_str))
    assert result is not None and len(result) > 0


@pytest.mark.template(func="cast_default_to_timestamp_template")
def test_cast_default_to_timestamp(ql):
    """Cast value to timestamp using default method."""
    escaped = ql.render(ql.templates.escape_string_template, value="2024-06-15 10:30:00")
    literal = ql.render(ql.templates.string_literal_template, value=escaped)
    cast_expr = ql.render(ql.templates.cast_default_to_timestamp_template, field=literal)
    to_str = ql.render(ql.templates.cast_to_string_func_template, field=cast_expr)
    result = str(ql.select_expression(to_str))
    assert "2024" in result


@pytest.mark.template(func="cast_timestamp_to_date_template")
def test_cast_timestamp_to_date(ql):
    """Cast timestamp to date, verify date parts."""
    ts_expr = ql.render(ql.templates.current_timestamp_func_template)
    cast_expr = ql.render(ql.templates.cast_timestamp_to_date_template, field=ts_expr)
    to_str = ql.render(ql.templates.cast_to_string_func_template, field=cast_expr)
    result = str(ql.select_expression(to_str))
    assert result is not None and len(result) > 0


@pytest.mark.template(func="cast_timestamp_to_timestamp_ntz_template")
def test_cast_timestamp_to_timestamp_ntz(ql):
    """Cast timestamp to timestamp without timezone."""
    ts_expr = ql.render(ql.templates.current_timestamp_func_template)
    cast_expr = ql.render(ql.templates.cast_timestamp_to_timestamp_ntz_template, field=ts_expr)
    to_str = ql.render(ql.templates.cast_to_string_func_template, field=cast_expr)
    result = str(ql.select_expression(to_str))
    assert result is not None and len(result) > 0


@pytest.mark.template(func="cast_timestamp_to_timestamp_tz_template")
def test_cast_timestamp_to_timestamp_tz(ql):
    """Cast timestamp to timestamp with timezone."""
    ts_expr = ql.render(ql.templates.current_timestamp_func_template)
    cast_expr = ql.render(ql.templates.cast_timestamp_to_timestamp_tz_template, field=ts_expr)
    to_str = ql.render(ql.templates.cast_to_string_func_template, field=cast_expr)
    result = str(ql.select_expression(to_str))
    assert result is not None and len(result) > 0


@pytest.mark.template(func="cast_to_timestamp_with_tz_template")
def test_cast_to_timestamp_with_tz(ql):
    """Render cast_to_timestamp_with_tz_template, verify non-empty."""
    result = ql.templates.cast_to_timestamp_with_tz_template()
    assert result is not None and len(result.strip()) > 0


@pytest.mark.template(func="cast_to_timestamp_without_tz_template")
def test_cast_to_timestamp_without_tz(ql):
    """Render cast_to_timestamp_without_tz_template, verify non-empty."""
    result = ql.templates.cast_to_timestamp_without_tz_template()
    assert result is not None and len(result.strip()) > 0
