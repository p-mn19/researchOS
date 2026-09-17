import asyncio
import os
import re
from typing import List

import arxiv
import httpx

from app.config import settings
from app.models.schemas import PaperMetadata


class LiteratureDiscoveryService:
    def __init__(self):
        self.openalex_api_key = getattr(
            settings,
            "OPENALEX_API_KEY",
            os.getenv(
                "OPENALEX_API_KEY",
                "",
            ),
        )

        self.email = getattr(
            settings,
            "OPENALEX_EMAIL",
            os.getenv(
                "OPENALEX_EMAIL",
                "developer@researchos.local",
            ),
        )

        self.arxiv_client = arxiv.Client(
            page_size=20,
            delay_seconds=5.0,
            num_retries=3,
        )

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join(
            str(value or "").split()
        ).strip()

    @staticmethod
    def _abstract_from_inverted_index(
        inverted_index,
    ) -> str:
        if not inverted_index:
            return ""

        words = []

        for word, positions in (
            inverted_index.items()
        ):
            for position in positions:
                words.append(
                    (position, word)
                )

        words.sort(
            key=lambda item: item[0]
        )

        return " ".join(
            word
            for _, word in words
        )

    @staticmethod
    def _normalise_title(
        title: str,
    ) -> str:
        return re.sub(
            r"[^a-z0-9]+",
            "",
            title.lower(),
        )

    async def fetch_openalex(
        self,
        query: str,
        limit: int = 5,
    ) -> List[PaperMetadata]:
        url = "https://api.openalex.org/works"

        params = {
            "search": query,
            "per-page": limit,
            "mailto": self.email,
        }

        if self.openalex_api_key:
            params["api_key"] = (
                self.openalex_api_key
            )

        papers = []

        try:
            async with httpx.AsyncClient(
                timeout=15.0
            ) as client:
                response = await client.get(
                    url,
                    params=params,
                )

                response.raise_for_status()
                data = response.json()

            for work in data.get(
                "results",
                [],
            ):
                abstract = (
                    self._abstract_from_inverted_index(
                        work.get(
                            "abstract_inverted_index"
                        )
                    )
                )

                authors = [
                    author.get(
                        "author",
                        {},
                    ).get(
                        "display_name",
                        "",
                    )
                    for author in work.get(
                        "authorships",
                        [],
                    )
                    if author.get(
                        "author",
                        {},
                    ).get(
                        "display_name"
                    )
                ]

                primary_location = (
                    work.get(
                        "primary_location"
                    )
                    or {}
                )

                source = (
                    primary_location.get(
                        "source"
                    )
                    or {}
                )

                open_access = (
                    work.get(
                        "open_access"
                    )
                    or {}
                )

                papers.append(
                    PaperMetadata(
                        source="OpenAlex",
                        source_id=str(
                            work.get(
                                "id",
                                "",
                            )
                        ),
                        title=self._clean_text(
                            work.get(
                                "title",
                                "Untitled",
                            )
                        ),
                        abstract=(
                            abstract
                            or "No abstract available"
                        ),
                        authors=authors,
                        year=work.get(
                            "publication_year"
                        ),
                        doi=work.get("doi"),
                        pdf_url=open_access.get(
                            "oa_url"
                        ),
                        citation_count=work.get(
                            "cited_by_count",
                            0,
                        ),
                        venue=source.get(
                            "display_name",
                            "Academic venue",
                        ),
                    )
                )

        except Exception as exc:
            print(
                f"[OpenAlex discovery error] {exc}"
            )

        return papers

    def _fetch_arxiv_sync(
        self,
        query: str,
        limit: int = 5,
    ) -> List[PaperMetadata]:
        search = arxiv.Search(
            query=query,
            max_results=limit,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        papers = []

        try:
            for result in (
                self.arxiv_client.results(search)
            ):
                papers.append(
                    PaperMetadata(
                        source="arXiv",
                        source_id=(
                            result.get_short_id()
                        ),
                        title=self._clean_text(
                            result.title
                        ),
                        abstract=self._clean_text(
                            result.summary
                        ),
                        authors=[
                            author.name
                            for author in (
                                result.authors
                            )
                        ],
                        year=(
                            result.published.year
                            if result.published
                            else None
                        ),
                        doi=result.doi,
                        pdf_url=(
                            result.pdf_url
                        ),
                        citation_count=0,
                        venue="arXiv preprint",
                    )
                )

        except Exception as exc:
            print(
                f"[arXiv discovery error] {exc}"
            )

        return papers

    async def fetch_arxiv(
        self,
        query: str,
        limit: int = 5,
    ) -> List[PaperMetadata]:
        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(
            None,
            self._fetch_arxiv_sync,
            query,
            limit,
        )

    async def search_all(
        self,
        query: str,
        limit_per_source: int = 5,
    ) -> List[PaperMetadata]:
        query = query.strip()

        if not query:
            return []

        openalex_task = self.fetch_openalex(
            query,
            limit=limit_per_source,
        )

        arxiv_task = self.fetch_arxiv(
            query,
            limit=limit_per_source,
        )

        openalex_results, arxiv_results = (
            await asyncio.gather(
                openalex_task,
                arxiv_task,
            )
        )

        combined = (
            openalex_results
            + arxiv_results
        )

        unique = []
        seen_titles = set()

        for paper in combined:
            normalized_title = (
                self._normalise_title(
                    paper.title
                )
            )

            if not normalized_title:
                continue

            if normalized_title in seen_titles:
                continue

            seen_titles.add(normalized_title)
            unique.append(paper)

        return unique

    def paper_metadata_to_citation(
        self,
        paper: "PaperMetadata",
    ) -> Dict[str, Any]:
        """Convert a PaperMetadata instance into a citation dict for Module 9."""
        return {
            "source": paper.source,
            "source_id": paper.source_id,
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.year,
            "doi": paper.doi,
            "venue": paper.venue,
            "pdf_url": paper.pdf_url,
        }