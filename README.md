# Actuent for Python

Search the web as structured data. [Actuent](https://actuent.ai) is a search engine for AI agents: it returns websites as **LAWP** (clean JSON with each site's pages and the actions a visitor can take) and products with prices, instead of raw HTML.

```bash
pip install actuent
```

```python
from actuent import Actuent

client = Actuent()                       # free tier; Actuent(api_key="ak_...") for Pro
site = client.get_site("stripe.com")      # pages + actions for one site
results = client.search("barber amsterdam")["results"]
shoes = client.products("running shoes under €100")   # products with prices, in English
```

Searches work in any language and always come back in English. Free: 20 requests/minute. Pro keys from [actuent.ai](https://actuent.ai): full results and 60/minute. Rate-limit info is in `client.rate_limit`; a `RateLimitError` has `retry_after`.

## LangChain

```bash
pip install "actuent[langchain]"
```

```python
from actuent.langchain import get_tools
tools = get_tools()          # [ActuentSearchTool]
```

## LlamaIndex

```bash
pip install "actuent[llamaindex]"
```

```python
from actuent.llama_index import get_tools
tools = get_tools()          # [FunctionTool actuent_search]
```

## More

- `client.check_site("yoursite.com")`: validate your `/.well-known/lawp.json` and action endpoints
- `client.register({...})`: list your own site (Pro, verified domain)
- `client.state()`: live "State of the AI web" numbers

Docs: [docs.actuent.ai](https://docs.actuent.ai) · MCP server for Claude and ChatGPT: `https://agents.actuent.ai/api/mcp`

Made by [localilabs](https://localilabs.com). MIT licensed.
