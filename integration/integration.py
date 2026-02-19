from typing import Any, List


class BaseIntegration:
    ########################################
    # Connection Related Methods
    ########################################
    def create_connection(self) -> Any:
        pass

    def create_cursor(self) -> Any:
        pass

    def close_connection(self):
        pass

    ########################################
    # Execution Related Methods
    ########################################
    def execute_query(self, query: str) -> None:
        pass

    def fetch_all_results(self) -> List[Any]:
        pass

    ########################################
    # Metadata Job Related Methods
    ########################################
    def get_databases_query_template(self) -> str:
        pass

    def get_schemas_query_template(self) -> str:
        pass

    def get_tables_query_template(self) -> str:
        pass

    def get_columns_query_template(self) -> str:
        pass

    ########################################
    # Query Log Job Related Methods
    ########################################
    def get_query_logs_query_template(self) -> str:
        pass

    ###################################################
    # Custom SQL Monitors Related Methods
    ###################################################
    def transform_into_count_query_template(self) -> str:
        pass

    def add_row_limit_template(self) -> str:
        pass

    def get_count_all_expression_template(self) -> str:
        pass

    ###################################################
    # QueryLanguage Related Methods
    ###################################################
    def get_casting_to_numeric_expression_template(self) -> str:
        pass

    def build_cte_template(self) -> str:
        pass

    def add_select_clause_template(self) -> str:
        pass

    def add_from_clause_template(self) -> str:
        pass

    def convert_to_utc_template(self) -> str:
        pass

    def current_date_func_template(self) -> str:
        pass

    def current_timestamp_func_template(self) -> str:
        pass

    def default_cast_to_timestamp_func_template(self) -> str:
        pass

    def add_days_func_template(self) -> str:
        pass

    def add_days_timestamp_func_template(self) -> str:
        pass

    def add_hours_timestamp_func_template(self) -> str:
        pass

    def get_table_identifier_template(self) -> str:
        pass

    def convert_to_unix_timestamp_func_template(self) -> str:
        pass

    def cast_to_string_func_template(self) -> str:
        pass

    def get_is_yesterday_expression_template(self) -> str:
        pass

    def get_in_past_days_expression_template(self) -> str:
        pass

    def get_in_past_hours_expression_template(self) -> str:
        pass

    def get_in_past_calendar_week_expression_template(self) -> str:
        pass

    def get_in_past_calendar_month_expression_template(self) -> str:
        pass

    def union_queries_template(self) -> str:
        pass

    def time_truncate_func_template(self) -> str:
        pass

    def escape_string_template(self) -> str:
        pass

    def supports_literal_select(self) -> bool:
        pass

    def supports_literal_group_by(self) -> bool:
        pass

    def supports_group_by_on_subquery(self) -> bool:
        pass

    def get_case_when_func_template(self) -> str:
        pass

    def get_arbitrary_where_clause_template(self) -> str:
        pass

    def ascending_order_template(self) -> str:
        pass

    def descending_order_template(self) -> str:
        pass

    def is_null_template(self) -> str:
        pass

    def is_not_null_template(self) -> str:
        pass

    def get_safe_divide_template(self) -> str:
        pass

    def get_days_of_week_expression_template(self) -> str:
        pass


    ###################################################
    # QueryLanguage: Metric Monitor Related Methods
    ###################################################
    def get_casting_to_decimal_expression_template(self) -> str:
        pass

    def get_approx_quantiles_func_template(self) -> str:
        pass

    def get_approx_percentile_func_template(self) -> str:
        pass

    def get_stddev_function_template(self) -> str:
        pass

    def get_avg_function_template(self) -> str:
        pass

    def get_regexp_count_expression_template(self) -> str:
        pass

    def get_regexp_expression_template(self) -> str:
        pass

    def get_array_length_func_template(self) -> str:
        pass

    def get_is_timestamp_expression_template(self) -> str:
        pass

    def get_epoch_seconds_expression_template(self) -> str:
        pass

    def get_length_template(self) -> str:
        pass

    def get_not_is_timestamp_expression_template(self) -> str:
        pass

    def get_isnan_expression_template(self) -> str:
        pass

    def get_distinct_count_func_template(self) -> str:
        pass

    def get_distinct_func_template(self) -> str:
        pass

    def string_literal_template(self) -> str:
        pass

    def literal_value_template(self) -> str:
        pass

    def literal_datetime_template(self) -> str:
        pass

    def literal_time_of_day_template(self) -> str:
        pass

    def literal_regex_template(self) -> str:
        pass

    def literal_table_from_value_list_template(self) -> str:
        pass

    def date_literal_template(self) -> str:
        pass

    def utc_literal_template(self) -> str:
        pass

    def substring_func_template(self) -> str:
        pass

    def alias_field_template(self) -> str:
        pass

    def all_fields_expression_template(self) -> str:
        pass

    def get_epoch_seconds_parameter_template(self) -> str:
        pass

    def get_is_empty_string_expression_template(self) -> str:
        pass

    ###################################################
    # QueryLanguage: RCA Related Methods
    ###################################################
    def rand_func_template(self) -> str:
        pass

    def max_time_func_template(self) -> str:
        pass

    def get_absolute_value_function_template(self) -> str:
        pass

    ###################################################
    # QueryLanguage: Comparison Monitor
    ###################################################
    def get_is_eq_expression_template(self) -> str:
        pass

    def get_is_gt_expression_template(self) -> str:
        pass

    def get_is_gte_expression_template(self) -> str:
        pass

    def get_is_lt_expression_template(self) -> str:
        pass

    def get_is_lte_expression_template(self) -> str:
        pass

    def get_is_inside_range_expression_template(self) -> str:
        pass

    def get_is_outside_range_expression_template(self) -> str:
        pass

    def get_date_diff_func_template(self) -> str:
        pass

    def any_value_template(self) -> str:
        pass

    def unpivot_template(self) -> str:
        pass

    ###################################################
    # QueryLanguage (Custom Monitors) Related Methods
    ###################################################
    def nan_expr(self) -> str:
        pass

    def array_expr(self, values: list[Any]) -> str:
        pass

    def parses_timestamp_with_trailing_text(self) -> bool:
        pass

    def _truncate_functions(self) -> dict:
        pass

    def _cast_to_timestamp_functions(self) -> dict:
        pass

    def _cast_to_timestamp_with_tz(self) -> str:
        pass

    def _cast_to_timestamp_without_tz(self) -> str:
        pass

    def _cast_timestamp_to_field(self) -> dict:
        pass

    def approx_distinct_func_template(self) -> str:
        pass

    def get_conditional_count_expression_template(self) -> str:
        pass

    def get_field_or_alias_template(self) -> str:
        pass

    def escape_field_name_template(self) -> str:
        pass

    def negate_expression_template(self) -> str:
        pass
