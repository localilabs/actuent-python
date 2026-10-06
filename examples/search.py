"""Search the live web the way an AI assistant does. Run: python examples/search.py "cafes in brooklyn open now" """
import sys
from actuent import Actuent

answer = Actuent().search(sys.argv[1] if len(sys.argv) > 1 else "does notion have a free plan")
for r in answer["results"][:3]:
    print(f"- {r['name']} ({r['domain']})" + (" · open now" if r.get("open_now") else ""))
if answer.get("answer"):
    print("Answer:", answer["answer"]["sentences"][0]["text"])
sys.exit(0 if answer["results"] else 1)
