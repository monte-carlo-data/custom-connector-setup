from typing import Callable, List, Any

from jinja2 import Environment

from integration.integration import BaseIntegration


class TestIntegration(BaseIntegration):
    def __init__(self):
        self.env = Environment(
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.connection = self.create_connection()
        self.cursor = self.create_cursor()

    def render_template(self, template_func: Callable, **kwargs) -> str:
        query_template = template_func()
        if not query_template:
            raise Exception(f"Template {template_func.__name__} Not Implemented")
        template = self.env.from_string(query_template)
        return template.render(kwargs)

    def execute_and_fetch_all(self, query: str) -> List[Any]:
        self.execute_query(query)
        return self.fetch_all_results()
