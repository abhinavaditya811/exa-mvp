import argparse
import sys

from dotenv import load_dotenv

from research_assistant import formatting
from research_assistant.search import run_search
from research_assistant.synthesize import extract


def main() -> None:
    parser = argparse.ArgumentParser(description="Research assistant powered by Exa")
    parser.add_argument("query", help="Question to research")
    parser.add_argument("--num-results", type=int, default=10, metavar="N")
    parser.add_argument(
        "--type",
        dest="search_type",
        default="deep",
        choices=["deep-lite", "deep", "deep-reasoning"],
        metavar="TYPE",
        help="Search depth: deep-lite, deep (default), deep-reasoning",
    )
    parser.add_argument("--full-text", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    load_dotenv()

    try:
        response = run_search(
            args.query,
            num_results=args.num_results,
            search_type=args.search_type,
            full_text=args.full_text,
        )
        result = extract(response)
        raw = getattr(response, "results", None) if args.verbose else None
        formatting.render(result, verbose=args.verbose, raw_results=raw)
    except SystemExit:
        raise
    except Exception as e:
        if args.verbose:
            raise
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
