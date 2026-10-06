"""What's on tonight in a city. Run: python examples/whats_on.py Copenhagen"""
import sys
from actuent import Actuent

city = sys.argv[1] if len(sys.argv) > 1 else "Copenhagen"
answer = Actuent().tool("actuent_events", {"location": city, "when": "tonight"})
events = answer.get("events", [])
print(f"{answer.get('events_found', 0)} events in {city} tonight")
for e in events[:5]:
    print(f"- {e['start_date'][11:16]} {e['name']} @ {e.get('venue', '')}" + (f" ({e['genre']})" if e.get("genre") else ""))
sys.exit(0 if events else 1)
