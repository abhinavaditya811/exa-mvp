import sys

from research_assistant.synthesize import SearchResult


def render(
    result: SearchResult,
    verbose: bool = False,
    raw_results: list[object] | None = None,
) -> None:
    if not result.answer:
        print("No answer returned.", file=sys.stderr)
        return

    print(result.answer)

    if result.citations:
        print()
        for cite in result.citations:
            print(f"[{cite.index}] {cite.url}")

    if verbose and raw_results:
        print()
        print("─" * 60)
        for i, r in enumerate(raw_results, start=1):
            title: str = getattr(r, "title", "") or ""
            url: str = getattr(r, "url", "") or ""
            highlights: list[str] = getattr(r, "highlights", []) or []
            print(f"\n[{i}] {title}")
            print(f"    {url}")
            for h in highlights:
                print(f"    › {h.strip()}")
