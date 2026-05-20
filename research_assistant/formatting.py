import sys
from datetime import date
from pathlib import Path

from research_assistant.synthesize import SearchResult

W = 62  # terminal width for separators

# ---------------------------------------------------------------------------
# Q&A rendering (existing)
# ---------------------------------------------------------------------------


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
        print("─" * W)
        for i, r in enumerate(raw_results, start=1):
            title: str = getattr(r, "title", "") or ""
            url: str = getattr(r, "url", "") or ""
            highlights: list[str] = getattr(r, "highlights", []) or []
            print(f"\n[{i}] {title}")
            print(f"    {url}")
            for h in highlights:
                print(f"    › {h.strip()}")


# ---------------------------------------------------------------------------
# Company brief — terminal rendering
# ---------------------------------------------------------------------------


def _section(label: str, lines: list[str]) -> None:
    if not lines:
        return
    pad = " " * (14 - len(label))
    print(f"\n{label}{pad}", end="")
    for i, line in enumerate(lines):
        if i == 0:
            print(line)
        else:
            print(" " * 14 + line)


def render_brief(brief) -> None:  # brief: CompanyBrief
    print(f"\n{brief.name}")
    print("═" * W)

    if brief.profile:
        p = brief.profile
        _section("Overview", [p.overview] if p.overview else [])
        meta = "  ·  ".join(filter(None, [
            f"Founded {p.founded_year}" if p.founded_year else None,
            p.headquarters,
            p.employee_count,
        ]))
        if meta:
            print(" " * 14 + meta)
        if p.key_products:
            print(" " * 14 + f"Products: {p.key_products}")
        leads = "  ·  ".join(filter(None, [
            f"CEO: {p.ceo}" if p.ceo else None,
            f"CTO: {p.cto}" if p.cto else None,
        ]))
        if leads:
            _section("Leadership", [leads])

    if brief.funding:
        f = brief.funding
        print("\n" + "─" * W)
        round_line = "  ·  ".join(filter(None, [
            f.latest_round, f.latest_amount, f.latest_date
        ]))
        lines = [round_line] if round_line else []
        if f.total_raised:
            lines.append(f"Total raised: {f.total_raised}")
        if f.key_investors:
            lines.append(f"Investors: {', '.join(f.key_investors)}")
        if f.valuation:
            lines.append(f"Valuation: {f.valuation}")
        _section("Funding", lines)

    if brief.news:
        print("\n" + "─" * W)
        items = [f"› {h}" for h in brief.news.headlines]
        items += [f"› [launch] {l}" for l in brief.news.product_launches]
        _section("Recent News", items)

    if brief.competitors:
        print("\n" + "─" * W)
        _section("Competitors", ["  ·  ".join(brief.competitors)])
        if brief.competitive_landscape:
            print(" " * 14 + brief.competitive_landscape)

    # Flatten and deduplicate all citations
    seen: set[str] = set()
    all_cites: list[tuple[str, str]] = []
    for cites in brief.citations.values():
        for url, title in cites:
            if url not in seen:
                seen.add(url)
                all_cites.append((url, title))

    if all_cites:
        print("\n" + "─" * W)
        print("Sources")
        for i, (url, _) in enumerate(all_cites, start=1):
            print(f"[{i}] {url}")

    if brief.thin_sections:
        print(f"\n[!] Thin data in: {', '.join(brief.thin_sections)}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Company brief — markdown writer
# ---------------------------------------------------------------------------


def _md_list(items: list[str], prefix: str = "-") -> str:
    return "\n".join(f"{prefix} {item}" for item in items) if items else "_No data found._"


def write_markdown(brief, out_dir: Path = Path(".")) -> Path:  # brief: CompanyBrief
    slug = brief.name.lower().replace(" ", "-").replace("/", "-")
    path = out_dir / f"{slug}-brief.md"

    lines: list[str] = [
        f"# {brief.name} — Company Intelligence Brief",
        f"*Generated: {date.today().isoformat()}*",
        "",
        "---",
        "",
    ]

    # Overview
    if brief.profile:
        p = brief.profile
        lines += ["## Overview", ""]
        if p.overview:
            lines.append(p.overview)
            lines.append("")
        meta_items = [
            f"**Founded:** {p.founded_year}" if p.founded_year else None,
            f"**HQ:** {p.headquarters}" if p.headquarters else None,
            f"**Size:** {p.employee_count}" if p.employee_count else None,
        ]
        meta = "  |  ".join(filter(None, meta_items))
        if meta:
            lines += [meta, ""]
        if p.key_products:
            lines += [f"**Key products:** {p.key_products}", ""]
        lines += ["### Leadership", ""]
        leads = [
            f"**CEO:** {p.ceo}" if p.ceo else None,
            f"**CTO:** {p.cto}" if p.cto else None,
        ]
        for lead in filter(None, leads):
            lines.append(f"- {lead}")
        lines += ["", "---", ""]
    else:
        lines += ["## Overview", "", "_No profile data found._", "", "---", ""]

    # Funding
    lines += ["## Funding", ""]
    if brief.funding:
        f = brief.funding
        table_rows = []
        if f.latest_round or f.latest_amount or f.latest_date:
            table_rows.append(
                f"| {f.latest_round or '—'} | {f.latest_amount or '—'} | {f.latest_date or '—'} |"
            )
        if table_rows:
            lines += [
                "| Round | Amount | Date |",
                "|---|---|---|",
                *table_rows,
                "",
            ]
        if f.total_raised:
            lines.append(f"**Total raised:** {f.total_raised}  ")
        if f.key_investors:
            lines.append(f"**Key investors:** {', '.join(f.key_investors)}  ")
        if f.valuation:
            lines.append(f"**Valuation:** {f.valuation}  ")
        lines += ["", "---", ""]
    else:
        lines += ["_No funding data found._", "", "---", ""]

    # News
    lines += ["## Recent News", ""]
    if brief.news:
        if brief.news.headlines:
            lines += [_md_list(brief.news.headlines), ""]
        if brief.news.product_launches:
            lines += ["### Product Launches", "", _md_list(brief.news.product_launches), ""]
    else:
        lines += ["_No recent news found._", ""]
    lines += ["---", ""]

    # Competitors
    lines += ["## Competitors", ""]
    if brief.competitors:
        lines += [_md_list(brief.competitors), ""]
        if brief.competitive_landscape:
            lines += [brief.competitive_landscape, ""]
    else:
        lines += ["_No competitor data found._", ""]
    lines += ["---", ""]

    # Sources
    seen: set[str] = set()
    all_cites: list[tuple[str, str]] = []
    for cites in brief.citations.values():
        for url, title in cites:
            if url not in seen:
                seen.add(url)
                all_cites.append((url, title))

    lines += ["## Sources", ""]
    for i, (url, title) in enumerate(all_cites, start=1):
        label = title if title else url
        lines.append(f"[{i}] [{label}]({url})")
    lines += ["", "---", ""]

    # Brainstorm section — the whole point of the md file
    lines += [
        "## Brainstorm Notes",
        "",
        "> Use this section when opening this file with Claude.",
        "> Ask: *'Review this brief and suggest outreach angles'*,",
        "> *'What questions should I ask their team?'*, or",
        "> *'What's missing from this brief?'*",
        "",
        "<!-- Add your notes here -->",
    ]

    if brief.thin_sections:
        lines += [
            "",
            f"> **Note:** Limited data found for: {', '.join(brief.thin_sections)}. "
            "Consider supplementing manually.",
        ]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
