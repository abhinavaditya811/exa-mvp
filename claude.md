# Exa Research Assistant (CLI)

A command-line research assistant built on the Exa search API. Given a question, it searches the web via Exa, pulls relevant excerpts, and synthesizes an answer with citations.

## Status

Greenfield. Nothing has been built yet. Treat the first task as scaffolding the project.

## Commands

```bash
# Setup (run once)
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run
python -m research_assistant "your question here"
python -m research_assistant "your question" --num-results 5 --verbose

# Dev
pytest                             # run tests
ruff check .                       # lint
ruff format .                      # format
```

The API key lives in a local `.env` file as `EXA_API_KEY=...`. Never commit `.env` — it must be in `.gitignore` from the first commit.

## Architecture

Single Python package, one entry point. Keep it small until there's a reason not to.

```
research_assistant/
  __init__.py
  __main__.py        # CLI entry: argparse, calls run()
  search.py          # instantiates Exa client + runs search, returns SearchResponse
  synthesize.py      # extracts (answer_text, citations) from SearchResponse — no LLM
  formatting.py      # terminal output (plain text first, rich later if needed)
tests/
  conftest.py        # shared mock Exa client fixture
  test_search.py
  test_synthesize.py
.env                 # gitignored
.env.example         # committed, shows required keys
requirements.txt     # exa-py, python-dotenv, pytest, ruff
README.md
```

Flow: `__main__` parses args → `search.run_search(query)` calls Exa with `output_schema` → `synthesize.extract(response)` pulls `(answer, citations)` from the structured result → `formatting.render()` prints to stdout.

No LLM involved. Synthesis is entirely Exa-driven via `output_schema` on `/search`.

## Exa usage conventions

The full Exa reference is in the project root as `exa-setup.md` — read it before changing how the API is called. Key rules baked into this project:

- **Default search type is `"deep"`**, not `"auto"`. `output_schema` only works with deep variants (`deep-lite`, `deep`, `deep-reasoning`). Expose `--type` on the CLI to override; warn if the user passes `fast` or `instant` with synthesis enabled.
- **Always** request `contents={"highlights": True}`. Highlights power `--verbose` output. Never omit `contents` — the default fetches 10k chars of text per result, which is wasteful.
- **Always** use the text-type `output_schema` for synthesis (defined in `search.py` as a module-level constant). No object schema, no hand-rolled synthesis, no LLM calls.
  ```python
  OUTPUT_SCHEMA = {"type": "text", "description": "A comprehensive answer to the research question"}
  ```
- Citations come from `response.output.grounding[0].citations` (text schema puts everything under one `"content"` field). Each citation has `.url` and `.title`.
- Use the Python SDK (`exa-py`), not raw HTTP. Python SDK uses **snake_case** (`num_results`, `output_schema`, `max_characters`) even inside nested dicts. Do not mix in camelCase from the JSON docs.
- Load the API key with `python-dotenv` + `os.environ.get("EXA_API_KEY")`. Call `load_dotenv()` in `__main__.py` (the entry point only — not inside library functions like `run_search`). Fail loudly with a clear message if the key is missing — do not fall back to a hardcoded key, ever.

### Parameter mistakes to avoid (from the Exa docs)

- `useAutoprompt` is deprecated — omit it.
- `includeUrls` / `excludeUrls` do not exist — use `include_domains` / `exclude_domains`.
- On `/search`, content options must be **nested** under `contents={...}`. On `/contents` they are top-level. Don't confuse the two.
- `livecrawl="always"` is deprecated — use `max_age_hours=0` instead.
- Never pass `text=True` without a `max_characters` cap — it can blow up the context.

## Conventions

- Python 3.11+. Type hints on every public function. No `Any` — use `object` or a Protocol.
- Format with `ruff format`, lint with `ruff check`. No black, no flake8.
- Test with `pytest`. Mock the Exa client in unit tests (don't hit the real API in CI).
- One responsibility per module. If `search.py` starts handling formatting, split it.
- CLI errors print to stderr and exit non-zero. Stack traces only with `--verbose`.
- Print citations inline as `[1]`, `[2]`, etc., with a numbered source list at the end. URLs only — no markdown link syntax in terminal output.

## Gotchas

- The Exa Python SDK takes `num_results`, not `numResults`. The doc samples sometimes mix conventions.
- Iterate results as `for r in response.results:` — NOT `response.results.results`. The doubled form was an older SDK version.
- `output.content` is the synthesized answer string (text schema); `output.grounding[0].citations` has the citation list. Don't confuse `output` (synthesis) with `results` (raw hits).
- `max_age_hours=-1` means "never livecrawl, cache only" — fast but can return stale data. Default behavior (omit the param) is usually right.
- Streaming mode (`stream=True`) returns SSE chunks, not a single JSON response. If we add streaming later, it needs its own code path.

## What not to do

- Don't add a web UI, FastAPI server, or database. This is a CLI.
- Don't add LangChain, LlamaIndex, or other orchestration frameworks. The Exa SDK + a synthesis call is enough.
- Don't cache results to disk yet. If we need it, we'll add it deliberately.
- Don't paste full text from search results into terminal output by default — highlights only.