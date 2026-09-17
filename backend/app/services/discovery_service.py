import asyncio
import os
import re
from typing import Any, Dict, List, Tuple

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

    # ---------------------------------------------------------
    # TEXT HELPERS
    # ---------------------------------------------------------

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

        for word, positions in inverted_index.items():
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

    # ---------------------------------------------------------
    # QUERY PROCESSING
    # ---------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """
        Convert text into meaningful search tokens.
        """

        stop_words = {
            "this",
            "that",
            "these",
            "those",
            "with",
            "from",
            "using",
            "used",
            "into",
            "their",
            "they",
            "them",
            "were",
            "have",
            "has",
            "been",
            "being",
            "which",
            "where",
            "when",
            "than",
            "such",
            "also",
            "paper",
            "study",
            "research",
            "method",
            "methods",
            "approach",
            "based",
            "results",
            "result",
            "data",
            "dataset",
            "model",
            "models",
            "performance",
            "analysis",
            "using",
            "proposed",
            "developed",
            "development",
            "investigate",
            "investigates",
            "investigating",
            "explore",
            "explores",
            "exploring",
            "assess",
            "assessing",
            "observation",
            "observations",
            "classification",
            "classifying",
            "evaluate",
            "evaluated",
            "evaluation",
        }

        tokens = re.findall(
            r"[a-zA-Z0-9]+",
            text.lower(),
        )

        meaningful = []

        for token in tokens:
            if len(token) < 4:
                continue

            if token in stop_words:
                continue

            meaningful.append(token)

        return list(dict.fromkeys(meaningful))

    @staticmethod
    def _build_search_query(
        query: str,
    ) -> str:
        """
        Keep the external API query compact.

        The discovery endpoint accepts a maximum of
        300 characters.
        """

        cleaned = LiteratureDiscoveryService._clean_text(
            query
        )

        return cleaned[:300]

    # ---------------------------------------------------------
    # OPENALEX
    # ---------------------------------------------------------

    async def fetch_openalex(
        self,
        query: str,
        limit: int = 20,
    ) -> List[PaperMetadata]:

        url = "https://api.openalex.org/works"

        params = {
            "search": self._build_search_query(query),
            "per-page": min(limit, 50),
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

    # ---------------------------------------------------------
    # ARXIV
    # ---------------------------------------------------------

    def _fetch_arxiv_sync(
        self,
        query: str,
        limit: int = 20,
    ) -> List[PaperMetadata]:

        search = arxiv.Search(
            query=self._build_search_query(query),
            max_results=min(limit, 50),
            sort_by=arxiv.SortCriterion.Relevance,
        )

        papers = []

        try:
            for result in self.arxiv_client.results(
                search
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
                        pdf_url=result.pdf_url,
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
        limit: int = 20,
    ) -> List[PaperMetadata]:

        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(
            None,
            self._fetch_arxiv_sync,
            query,
            limit,
        )

    # ---------------------------------------------------------
    # RELEVANCE SCORING
    # ---------------------------------------------------------

    def _score_paper(
        self,
        paper: PaperMetadata,
        query_tokens: List[str],
    ) -> Tuple[float, List[str]]:
        """
        Calculate relevance using the paper title
        and abstract.

        Title matches are weighted much more heavily
        than abstract matches.
        """

        if not query_tokens:
            return 0.0, []

        title = (
            paper.title or ""
        ).lower()

        abstract = (
            paper.abstract or ""
        ).lower()

        title_tokens = set(
            self._tokenize(title)
        )

        abstract_tokens = set(
            self._tokenize(abstract)
        )

        matched_terms = []

        title_score = 0.0
        abstract_score = 0.0

        for token in query_tokens:

            if token in title_tokens:
                title_score += 5.0
                matched_terms.append(token)

            elif token in abstract_tokens:
                abstract_score += 1.0
                matched_terms.append(token)

        # Exact phrase bonus.
        query_phrase = " ".join(
            query_tokens[:4]
        )

        if (
            query_phrase
            and query_phrase in title
        ):
            title_score += 8.0

        total_score = (
            title_score
            + abstract_score
        )

        # Small bonus for having multiple
        # independent research concepts.
        unique_matches = list(
            dict.fromkeys(
                matched_terms
            )
        )

        if len(unique_matches) >= 3:
            total_score += 4.0

        if len(unique_matches) >= 5:
            total_score += 3.0

        return (
            total_score,
            unique_matches,
        )

    # ---------------------------------------------------------
    # FILTERING
    # ---------------------------------------------------------

    @staticmethod
    def _is_likely_english(
        title: str,
    ) -> bool:

        cleaned = title.replace(
            " ",
            "",
        )

        if not cleaned:
            return False

        latin_count = len(
            re.findall(
                r"[A-Za-zÀ-ÿ]",
                cleaned,
            )
        )

        non_latin_count = len(
            re.findall(
                r"[^\x00-\x7FÀ-ÿ]",
                cleaned,
            )
        )

        if (
            non_latin_count > 0
            and latin_count
            / max(len(cleaned), 1)
            < 0.55
        ):
            return False

        return True

    # ---------------------------------------------------------
    # MAIN SEARCH
    # ---------------------------------------------------------

    async def search_all(
        self,
        query: str,
        limit_per_source: int = 5,
    ) -> List[PaperMetadata]:

        query = self._build_search_query(
            query
        )

        if not query:
            return []

        # Extract meaningful research concepts.
        query_tokens = self._tokenize(
            query
        )

        if not query_tokens:
            return []

        # Fetch more candidates than we finally display.
        candidate_limit = max(
            20,
            limit_per_source * 4,
        )

        print(
            f"[Discovery] Query: {query}"
        )

        print(
            f"[Discovery] Concepts: {query_tokens}"
        )

        openalex_task = self.fetch_openalex(
            query,
            limit=candidate_limit,
        )

        arxiv_task = self.fetch_arxiv(
            query,
            limit=candidate_limit,
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

        # -----------------------------------------------------
        # DEDUPLICATION
        # -----------------------------------------------------

        unique = []
        seen_titles = set()

        for paper in combined:

            title = (
                paper.title or ""
            ).strip()

            if not title:
                continue

            if not self._is_likely_english(
                title
            ):
                continue

            normalized_title = (
                self._normalise_title(
                    title
                )
            )

            if not normalized_title:
                continue

            if normalized_title in seen_titles:
                continue

            seen_titles.add(
                normalized_title
            )

            unique.append(paper)

        # -----------------------------------------------------
        # RELEVANCE RANKING
        # -----------------------------------------------------

        scored = []

        for paper in unique:

            score, matched_terms = (
                self._score_paper(
                    paper,
                    query_tokens,
                )
            )

            scored.append(
                (
                    score,
                    matched_terms,
                    paper,
                )
            )

        scored.sort(
            key=lambda item: (
                item[0],
                item[2].citation_count or 0,
            ),
            reverse=True,
        )

        # -----------------------------------------------------
        # RELEVANCE THRESHOLD
        # -----------------------------------------------------

        results = []

        for (
            score,
            matched_terms,
            paper,
        ) in scored:

            # A paper needs at least:
            #
            #   - 2 meaningful matching concepts
            # OR
            #   - a strong title match
            #
            # This prevents generic words such as
            # "observation", "data", "analysis", etc.
            # from making unrelated papers pass.
            strong_match = (
                len(matched_terms) >= 2
                or score >= 10.0
            )

            if not strong_match:
                continue

            print(
                f"[Discovery] "
                f"{score:.1f} | "
                f"{paper.title} | "
                f"matches={matched_terms}"
            )

            results.append(paper)

            if len(results) >= limit_per_source:
                break

        print(
            f"[Discovery] "
            f"Returning {len(results)} relevant papers"
        )

        return results

    # ---------------------------------------------------------
    # CITATIONS
    # ---------------------------------------------------------

    def paper_metadata_to_citation(
        self,
        paper: "PaperMetadata",
    ) -> Dict[str, Any]:
        """
        Convert a PaperMetadata instance into a
        citation dict for Module 9.
        """

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