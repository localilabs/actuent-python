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


class _AskInput(BaseModel):
    domain: str = Field(description="The site, e.g. basecamp.com")
    question: str = Field(description="The question, in plain words, e.g. 'is there a free plan?'")


class ActuentAskSiteTool(BaseTool):
    """Answer a question from one website's own pages."""

    name: str = "actuent_ask_site"
    description: str = (
        "Answer a question from one website's own pages ('does basecamp have a free plan?', 'is there parking?'). "
        "Returns matching sentences with the page each came from."
    )
    args_schema: Type[BaseModel] = _AskInput
    client: Actuent = Field(default_factory=Actuent, exclude=True)

    model_config = {"arbitrary_types_allowed": True}

    def _run(self, domain: str, question: str, run_manager=None) -> str:
        return json.dumps(self.client.ask(domain, question), ensure_ascii=False)


class _SimilarInput(BaseModel):
    domain: str = Field(description="The site to find alternatives to, e.g. notion.so")


class ActuentSimilarTool(BaseTool):
    """Find websites like a given one."""

    name: str = "actuent_similar"
    description: str = "Find websites like a given one ('alternatives to mailchimp.com'), with why each is similar."
    args_schema: Type[BaseModel] = _SimilarInput
    client: Actuent = Field(default_factory=Actuent, exclude=True)

    model_config = {"arbitrary_types_allowed": True}

    def _run(self, domain: str, run_manager=None) -> str:
        return json.dumps(self.client.similar(domain), ensure_ascii=False)


def get_tools(api_key: Optional[str] = None) -> List[BaseTool]:
    """Actuent tools for a LangChain agent: search, ask a site, similar sites."""
    client = Actuent(api_key=api_key)
    return [ActuentSearchTool(client=client), ActuentAskSiteTool(client=client), ActuentSimilarTool(client=client)]
