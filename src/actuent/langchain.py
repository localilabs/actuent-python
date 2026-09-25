"""LangChain tools for Actuent.

    from actuent.langchain import get_tools
    tools = get_tools()              # or get_tools(api_key="ak_...")
    agent = create_react_agent(llm, tools)

Requires: pip install "actuent[langchain]"
"""

import json
from typing import List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from . import Actuent


class _SearchInput(BaseModel):
    query: str = Field(description="What to find: a topic ('barber amsterdam'), a domain ('nike.com'), "
                                   "a page ('stripe.com/pricing') or a product search ('running shoes under €100').")


class ActuentSearchTool(BaseTool):
    """Search the web as structured data with Actuent."""

    name: str = "actuent_search"
    description: str = (
        "Search websites and products for the user. Returns each site's pages summarised in plain English, "
        "the actions a visitor can take (book, contact, buy), and for shopping searches, products with prices. "
        "Use it instead of browsing raw web pages. Works in any language; results are in English."
    )
    args_schema: Type[BaseModel] = _SearchInput
    client: Actuent = Field(default_factory=Actuent, exclude=True)

    model_config = {"arbitrary_types_allowed": True}

    def _run(self, query: str, run_manager=None) -> str:
        return json.dumps(self.client.search(query), ensure_ascii=False)


def get_tools(api_key: Optional[str] = None) -> List[BaseTool]:
    """Actuent tools for a LangChain agent."""
    return [ActuentSearchTool(client=Actuent(api_key=api_key))]
