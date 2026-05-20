import os
import sys

from exa_py import Exa

OUTPUT_SCHEMA: dict[str, str] = {
    "type": "text",
    "description": "A comprehensive answer to the research question",
}


def run_search(
    query: str,
    num_results: int = 10,
    search_type: str = "deep",
    full_text: bool = False,
    output_schema: dict | None = None,
    category: str | None = None,
    include_domains: list[str] | None = None,
    start_published_date: str | None = None,
) -> object:
    api_key = os.environ.get("EXA_API_KEY")
    if not api_key:
        print("Error: EXA_API_KEY not set. Add it to .env", file=sys.stderr)
        sys.exit(1)

    exa = Exa(api_key)
    contents: dict[str, object] = {"highlights": True}
    if full_text:
        contents["text"] = {"max_characters": 5000}

    kwargs: dict[str, object] = {
        "type": search_type,
        "num_results": num_results,
        "contents": contents,
        "output_schema": output_schema if output_schema is not None else OUTPUT_SCHEMA,
    }
    if category is not None:
        kwargs["category"] = category
    if include_domains is not None:
        kwargs["include_domains"] = include_domains
    if start_published_date is not None:
        kwargs["start_published_date"] = start_published_date

    return exa.search(query, **kwargs)
