import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    from .banks import bank_registry
    # Windows redirected terminals often default to cp1252, which cannot display
    # the Unicode bullets and punctuation in public financial exhibits.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Investor Relations Document Intelligence Assistant")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Download official sources and extract inspectable blocks")
    prepare.add_argument("--sources", type=Path)
    index = commands.add_parser("index", help="Chunk, embed, and build persistent Chroma indexes")
    index.add_argument("--strategy", choices=["fixed", "semantic", "both"], default="both")
    ask = commands.add_parser("ask", help="Retrieve evidence or generate a cited answer")
    ask.add_argument("question")
    ask.add_argument("--strategy", choices=["fixed", "semantic"], default="fixed")
    ask.add_argument("--rerank", action="store_true")
    ask.add_argument("--generate", action="store_true", help="Call the configured hosted model")
    ask.add_argument("--base-bank", choices=list(bank_registry()), help="Base bank for automatic peer comparisons")
    inspect = commands.add_parser("inspect", help="Export text/table blocks for manual source validation")
    inspect.add_argument("--bank", choices=list(bank_registry()))
    inspect.add_argument("--contains", default="consumer")
    inspect.add_argument("--limit", type=int, default=12)
    evaluate = commands.add_parser("evaluate", help="Run all four retrieval experiment configurations")
    evaluate.add_argument("--questions", type=Path, required=True)
    evaluate.add_argument("--generate", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            from .ingest import prepare
            print(json.dumps(prepare(args.sources) if args.sources else prepare(), indent=2))
        elif args.command == "index":
            from .retrieval import build_index
            for strategy in (["fixed", "semantic"] if args.strategy == "both" else [args.strategy]):
                print(json.dumps(build_index(strategy), indent=2))
        elif args.command == "ask":
            from .workflow import Application
            answer, _ = Application(args.strategy, args.rerank, args.generate).ask(args.question, base_bank=args.base_bank)
            print(f"Status: {answer.status}\n\n{answer.text}\n\nElapsed: {answer.elapsed_seconds}s")
        elif args.command == "inspect":
            from .models import Block
            from .settings import DATA
            from .storage import read_jsonl
            blocks = read_jsonl(DATA / "processed" / "blocks.jsonl", Block)
            found = [b for b in blocks if (not args.bank or b.bank == args.bank) and args.contains.lower() in b.text.lower()]
            for block in found[:args.limit]:
                print(block.model_dump_json(indent=2))
            print(f"Matched {len(found)} blocks; displayed up to {args.limit}.")
        elif args.command == "evaluate":
            from .evaluation import evaluate
            print(evaluate(args.questions, args.generate))
        return 0
    except ModuleNotFoundError as exc:
        print(f"Missing dependency {exc.name}. Install requirements.txt in the project virtual environment.", file=sys.stderr)
        return 2
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
