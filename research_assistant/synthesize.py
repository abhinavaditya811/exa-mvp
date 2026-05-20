from dataclasses import dataclass, field


@dataclass
class Citation:
    index: int
    url: str
    title: str


@dataclass
class SearchResult:
    answer: str
    citations: list[Citation] = field(default_factory=list)


def extract(response: object) -> SearchResult:
    output = getattr(response, "output", None)
    if output is None:
        return SearchResult(answer="")

    answer: str = getattr(output, "content", "") or ""
    grounding: list[object] = getattr(output, "grounding", []) or []

    citations: list[Citation] = []
    if grounding:
        raw = getattr(grounding[0], "citations", []) or []
        for i, cite in enumerate(raw, start=1):
            citations.append(
                Citation(
                    index=i,
                    url=getattr(cite, "url", ""),
                    title=getattr(cite, "title", ""),
                )
            )

    return SearchResult(answer=answer, citations=citations)
