<p align="center"><img src="https://api.actuent.ai/assets/lawpy/lawpy-dance.gif" width="108" height="72" alt="Lawpy, the Actuent mascot, dancing"></p>

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


## Plans, services and more (0.2)

```python
client.plan("Nørreport, Copenhagen", stops=["dinner", "drinks"], start_time="19:00")
client.trip("Lisbon", days=3)
client.find_service("skin fade under €30", location="Amsterdam")
client.nearby("cafe", "Jordaan, Amsterdam", filters=["vegan", "wifi"], open_now=True)
client.events(location="Copenhagen", query="jazz")
client.ask_site("nike.com", "free returns?")
client.compare_products([url_a, url_b])
client.score("yoursite.com")                     # agent-readiness 0–100
client.watch_price(url, notify="both")           # Pro: price drops and back in stock
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

## When Actuent is busy

Limited or empty search results include a plain-English `message` (and `notices`) you can show the user. If Actuent is very busy (HTTP 429 or 503) the client waits as long as the server asks and tries once more (`Actuent(retries=0)` turns that off); after that it raises `RateLimitError` or `BusyError`, whose message is written for people and whose `retry_after` says how many seconds to wait. See [Errors & busy times](https://docs.actuent.ai/#errors).
