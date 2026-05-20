import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from research_assistant import formatting
from research_assistant.search import run_search
from research_assistant.synthesize import extract


def _qa_main() -> None:
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


def _company_main() -> None:
    from research_assistant.intelligence import build_brief

    parser = argparse.ArgumentParser(
        prog="python -m research_assistant company",
        description="Generate a company intelligence brief",
    )
    parser.add_argument("name", help="Company name (e.g. 'Exa AI')")
    parser.add_argument(
        "--focus",
        default="all",
        choices=["all", "profile", "funding", "news", "competitors", "people"],
        help="Limit to a single section (default: all)",
    )
    parser.add_argument(
        "--since",
        default="90d",
        metavar="PERIOD",
        help="How far back to look for news: 30d, 90d, 1y (default: 90d)",
    )
    parser.add_argument(
        "--type",
        dest="search_type",
        default="deep",
        choices=["deep-lite", "deep", "deep-reasoning"],
        metavar="TYPE",
    )
    parser.add_argument(
        "--out",
        default="terminal",
        choices=["terminal", "markdown"],
        help="Output format (default: terminal)",
    )
    args = parser.parse_args()

    since_days = _parse_period(args.since)

    try:
        brief = build_brief(
            args.name,
            search_type=args.search_type,
            since_days=since_days,
            focus=args.focus,
        )
    except SystemExit:
        raise
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.out == "markdown":
        path = formatting.write_markdown(brief, out_dir=Path.cwd())
        print(f"Brief written to: {path}")
    else:
        formatting.render_brief(brief)


def _parse_period(period: str) -> int:
    period = period.strip().lower()
    if period.endswith("y"):
        return int(period[:-1]) * 365
    if period.endswith("m"):
        return int(period[:-1]) * 30
    if period.endswith("d"):
        return int(period[:-1])
    return 90


def main() -> None:
    load_dotenv()
    if len(sys.argv) > 1 and sys.argv[1] == "company":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        _company_main()
    else:
        _qa_main()


if __name__ == "__main__":
    main()
