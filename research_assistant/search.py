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
) -> object:
    api_key = os.environ.get("EXA_API_KEY")
    if not api_key:
        print("Error: EXA_API_KEY not set. Add it to .env", file=sys.stderr)
        sys.exit(1)

    exa = Exa(api_key)
    contents: dict[str, object] = {"highlights": True}
    if full_text:
        contents["text"] = {"max_characters": 5000}

    return exa.search(
        query,
        type=search_type,
        num_results=num_results,
        contents=contents,
        output_schema=OUTPUT_SCHEMA,
    )
