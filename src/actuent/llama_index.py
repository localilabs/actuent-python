"""LlamaIndex tools for Actuent.

    from actuent.llama_index import get_tools
    agent = ReActAgent.from_tools(get_tools(), llm=llm)

Requires: pip install "actuent[llamaindex]"
"""

import json
from typing import List, Optional

from llama_index.core.tools import FunctionTool

from . import Actuent


def get_tools(api_key: Optional[str] = None) -> List[FunctionTool]:
    """Actuent tools for a LlamaIndex agent."""
    client = Actuent(api_key=api_key)

    def actuent_search(query: str) -> str:
        """Search websites and products. Returns each site's pages in plain English, the actions a visitor
        can take (book, contact, buy), and for shopping searches, products with prices. Accepts a topic,
        domain, page (domain/path) or product search like 'running shoes under €100'."""
        return json.dumps(client.search(query), ensure_ascii=False)

    return [FunctionTool.from_defaults(fn=actuent_search)]
