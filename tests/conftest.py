import importlib
import os
from datetime import datetime, date
from typing import Callable, List, Any, Optional

import pytest
from dotenv import load_dotenv
from jinja2.sandbox import ImmutableSandboxedEnvironment

pytest_plugins = ["tests.capabilities_plugin"]


def pytest_addoption(parser):
    parser.addoption(
        "--connector",
        default=None,
        help="Connector name to test (e.g. postgres, teradata)",
    )


def _resolve_connector_name(config):
    """Resolve connector name: --connector flag > CONNECTOR env var > auto-detect."""
    name = config.getoption("--connector", default=None)
    if name:
        return name

    name = os.environ.get("CONNECTOR")
    if name:
        return name

    connectors_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "connectors")
    if not os.path.isdir(connectors_dir):
        return None

    dirs = [
        d for d in os.listdir(connectors_dir)
        if not d.startswith("_") and not d.startswith(".")
        and os.path.isdir(os.path.join(connectors_dir, d))
    ]
    if len(dirs) == 1:
        return dirs[0]
    return None


def pytest_configure(config):
    """Validate connector selection early so we fail once, not per-test."""
    name = _resolve_connector_name(config)
    if name:
        return

    connectors_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "connectors")
    if not os.path.isdir(connectors_dir):
        raise pytest.UsageError("No connectors/ directory found")

    dirs = [
        d for d in os.listdir(connectors_dir)
        if not d.startswith("_") and not d.startswith(".")
        and os.path.isdir(os.path.join(connectors_dir, d))
    ]
    if len(dirs) == 0:
        raise pytest.UsageError(
            "No connectors found. Run: python scripts/create_connector.py <name>"
        )
    raise pytest.UsageError(
        f"Multiple connectors found ({', '.join(sorted(dirs))}). "
        "Specify one with --connector=<name> or CONNECTOR=<name> env var."
    )


_connector_cache = {}


def _get_connector(config):
    """Load and cache the connector module."""
    if "module" not in _connector_cache:
        name = _resolve_connector_name(config)
        if not name:
            raise RuntimeError("No connector specified")
        config._connector_name = name

        connectors_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "connectors")
        env_path = os.path.join(connectors_dir, name, ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)

        module = importlib.import_module(f"connectors.{name}.connector")
        _connector_cache["name"] = name
        _connector_cache["module"] = module

    return _connector_cache["name"], _connector_cache["module"]


class TestConnector:
    """Wraps a loaded connector module's BaseConnector via delegation."""

    def __init__(self, module):
        self._delegate = module.BaseConnector()
        self._delegate.credentials = self._load_credentials_from_env()
        self._delegate.connection = self._delegate.create_connection()
        self._delegate.cursor = self._delegate.create_cursor()

    def _load_credentials_from_env(self) -> dict[str, str]:
        creds = {}
        for key, env_var in self._delegate.credential_env_vars().items():
            val = os.environ.get(env_var)
            if val is not None:
                creds[key] = val
        return creds

    def execute_and_fetch_all(self, query: str) -> List[Any]:
        self._delegate.execute_query(query)
        return self._delegate.fetch_all_results()

    def execute_only(self, query: str) -> None:
        self._delegate.execute_query(query)
        commit = getattr(self._delegate.connection, "commit", None)
        if callable(commit):
            commit()

    def close_connection(self):
        self._delegate.close_connection()

    def __getattr__(self, name):
        return getattr(self._delegate, name)


def _make_templates_class(module):
    """Dynamically create a Templates class from the connector module's template classes."""
    bases = (
        module.MetadataQueryTemplates,
        module.QueryLogCollectionTemplates,
        module.CustomSQLMonitorTemplates,
        module.QueryLanguageTemplates,
    )
    functional_cls = getattr(module, "FunctionalTestOperations", None)
    if functional_cls is not None:
        bases = bases + (functional_cls,)

    def templates_init(self):
        self.env = ImmutableSandboxedEnvironment(
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_template(self, template_func: Callable, **kwargs) -> str:
        query_template = template_func()
        if not query_template:
            raise Exception(f"Template {template_func.__name__} Not Implemented")
        template = self.env.from_string(query_template)
        return template.render(kwargs)

    return type("Templates", bases, {
        "__init__": templates_init,
        "render_template": render_template,
    })


class QueryTestHelper:
    def __init__(self, connector: TestConnector, templates):
        self.connector = connector
        self.templates = templates

    def render(self, template_method: Callable, **kwargs) -> str:
        return self.templates.render_template(template_method, **kwargs)

    def execute(self, query: str) -> List[tuple]:
        return self.connector.execute_and_fetch_all(query)

    def execute_scalar(self, query: str) -> Any:
        rows = self.execute(query)
        return rows[0][0]

    def make_data_source(self, values: list[dict], alias: str = "test_data") -> tuple[str, str]:
        """Build a CTE from test data using the customer's templates.

        Takes a list of dicts (each dict is a row), builds individual SELECT
        statements with aliased fields, unions them, and wraps in a CTE.

        Returns (cte_sql, alias).
        """
        if not values:
            raise ValueError("values must be a non-empty list of dicts")

        keys = list(values[0].keys())
        select_queries = []
        for row in values:
            field_exprs = []
            for key in keys:
                sql_val = self._python_value_to_sql_literal(row[key])
                aliased = self.render(self.templates.alias_field_template, field=sql_val, alias=key)
                field_exprs.append(aliased)
            select_clause = self.render(self.templates.add_select_clause_template, fields=", ".join(field_exprs))
            select_queries.append(select_clause)

        unioned = self.render(self.templates.union_queries_template, queries=select_queries)
        cte = self.render(self.templates.build_cte_template, alias=alias, query=unioned)
        return cte, alias

    def select_from_data_source(self, values: list[dict], expression: str, condition: Optional[str] = None) -> Any:
        """Build CTE + SELECT expression FROM alias [WHERE condition], return scalar."""
        cte, alias = self.make_data_source(values)
        from_clause = self.render(self.templates.add_from_clause_template, table=alias)
        select_clause = self.render(self.templates.add_select_clause_template, fields=expression)
        query = f"{cte} {select_clause} {from_clause}"
        if condition:
            query += f" WHERE {condition}"
        return self.execute_scalar(query)

    def select_expression(self, expression: str) -> Any:
        """SELECT <expression> with no table, or FROM single-row CTE if DB doesn't support literal select."""
        supports = self.templates.supports_literal_select_template()
        if supports and supports.strip().lower() == "true":
            query = self.render(self.templates.add_select_clause_template, fields=expression)
        else:
            cte, alias = self.make_data_source([{"_dummy": 1}])
            from_clause = self.render(self.templates.add_from_clause_template, table=alias)
            select_clause = self.render(self.templates.add_select_clause_template, fields=expression)
            query = f"{cte} {select_clause} {from_clause}"
        return self.execute_scalar(query)

    def _python_value_to_sql_literal(self, value) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            escaped = self.render(self.templates.escape_string_template, value=value)
            return self.render(self.templates.string_literal_template, value=escaped)
        if isinstance(value, datetime):
            return self.render(self.templates.literal_datetime_template, value=value)
        if isinstance(value, date):
            return self.render(self.templates.date_literal_template, value=value)
        raise TypeError(f"Unsupported type for SQL literal: {type(value)}")


@pytest.fixture(scope="session")
def connector(request):
    _, module = _get_connector(request.config)
    tc = TestConnector(module)
    yield tc
    tc.close_connection()


@pytest.fixture(scope="session")
def templates(request):
    _, module = _get_connector(request.config)
    TemplatesClass = _make_templates_class(module)
    t = TemplatesClass()
    request.config._templates_instance = t
    return t


@pytest.fixture(scope="session")
def ql(connector, templates) -> QueryTestHelper:
    return QueryTestHelper(connector, templates)


@pytest.fixture(scope="session")
def functional_ops(request):
    """Load the connector's FunctionalTestOperations, or None if not implemented."""
    _, module = _get_connector(request.config)
    cls = getattr(module, "FunctionalTestOperations", None)
    if cls is None:
        return None
    ops = cls()
    try:
        ops.get_test_table_identifier()
    except NotImplementedError:
        return None
    return ops
