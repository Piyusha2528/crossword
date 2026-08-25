from __future__ import annotations
import argparse, json
from pathlib import Path
from .agent import SupportAgent

def main() -> None:
    p = argparse.ArgumentParser(description="Aster & Row local support agent")
    p.add_argument("--session", default="cli")
    p.add_argument("--trace", action="store_true")
    args = p.parse_args()
    agent = SupportAgent()
    print("Aster & Row support (type 'quit' to exit)")
    while (msg := input("You: ").strip()) not in {"quit", "exit"}:
        r = agent.respond(msg, args.session)
        print(f"Agent: {r.answer}")
        if r.sources: print("Sources: " + "; ".join(r.sources))
        if r.handoff: print("Handoff: recommended")
        if args.trace: print(json.dumps(r.trace, indent=2))
if __name__ == "__main__": main()
