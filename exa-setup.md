# Exa API Reference

Authoritative reference for this project. When in doubt about a parameter or response shape, check here first. Based on exa-py SDK docs as of May 2026.

---

## search() signature

```python
exa.search(
    query: str,
    type: str | None = None,           # see Search types below
    num_results: int | None = None,    # default 10
    contents: dict | False | None = None,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    start_published_date: str | None = None,  # ISO 8601
    end_published_date: str | None = None,
    include_text: list[str] | None = None,
    exclude_text: list[str] | None = None,
    output_schema: dict | None = None,
    system_prompt: str | None = None,
    category: str | None = None,
    max_age_hours: int | None = None,
) -> SearchResponse
```

---

## Search types

| Value | Latency | Notes |
|---|---|---|
| `"auto"` | varies | Picks best method; does NOT guarantee output_schema support |
| `"instant"` | ~250ms | No synthesis |
| `"fast"` | low | No synthesis |
| `"deep-lite"` | medium | Supports output_schema |
| `"deep"` | medium | Supports output_schema — **project default** |
| `"deep-reasoning"` | 12–40s | Supports output_schema, highest quality |

**Rule:** `output_schema` requires a deep variant (`deep-lite`, `deep`, or `deep-reasoning`). Never pair `output_schema` with `auto`, `fast`, or `instant`.

---

## contents options

```python
contents = {
    "highlights": True,                    # relevant excerpts per result
    "text": {"max_characters": 5000},       # full page text (always cap it)
    "summary": {"query": "optional hint"}, # per-page summary
}
```

- Omitting `contents` defaults to `{"text": {"maxCharacters": 10000}}` — expensive; always be explicit.
- Pass `contents=False` to skip all content retrieval (faster, cheaper).
- On `/search`, these must be **nested under `contents={...}`**. On `/contents` they are top-level.

---

## output_schema

Used for server-side synthesis across all results. Two forms:

### Text schema (project default)
```python
output_schema = {
    "type": "text",
    "description": "A comprehensive answer to the research question",
}
```
`output.content` → `str` (narrative answer).  
`output.grounding` → list with one item, `field="content"`, holding all citations.

### Object schema (for structured extraction)
```python
output_schema = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "key_points": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer"],
}
```
`output.content` → `dict` matching the schema.  
`output.grounding` → per-field citations (e.g., `field="answer"`, `field="key_points[0]"`).

**Constraints:** max nesting depth 2, max 10 properties. Do not include citation or confidence fields in your schema — they come back automatically via `grounding`.

---

## SearchResponse shape

```python
response.results          # list[Result] — raw search hits
response.output           # DeepSearchOutput | None — synthesis (deep only)
response.resolved_search_type  # "neural" | "keyword"
response.cost_dollars     # {"total": float, ...}
```

### Result

```python
result.title              # str
result.url                # str
result.published_date     # str | None (ISO 8601)
result.author             # str | None
result.score              # float 0–1 (similarity)
result.highlights         # list[str] | None
result.highlight_scores   # list[float] | None
result.text               # str | None
result.summary            # str | None
```

Iterate as: `for r in response.results:` — **not** `response.results.results`.

### DeepSearchOutput

```python
response.output.content    # str (text schema) | dict (object schema)
response.output.grounding  # list[GroundingItem]
```

### GroundingItem

```python
item.field       # str — "content" for text schema, "fieldname" for object schema
item.citations   # list[Citation]
item.confidence  # "low" | "medium" | "high"
```

### Citation

```python
citation.url     # str
citation.title   # str
```

---

## Project-specific output_schema

This project always uses the text schema:

```python
OUTPUT_SCHEMA = {
    "type": "text",
    "description": "A comprehensive answer to the research question",
}
```

Pulling citations from a text-schema response:

```python
citations = response.output.grounding[0].citations  # all citations under "content" field
```

---

## Parameter gotchas

- `useAutoprompt` — deprecated, omit it.
- `includeUrls` / `excludeUrls` — do not exist; use `include_domains` / `exclude_domains`.
- `livecrawl="always"` — deprecated; use `max_age_hours=0` for always-fresh.
- `max_age_hours=-1` — cache only, no live crawl. Fast but can be stale.
- `text=True` without `maxCharacters` — blows up context. Always cap it.
- Default `contents` (when omitted) fetches up to 10k chars of text per result — always pass `contents` explicitly.
