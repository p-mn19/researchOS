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

    # =========================================================
    # TEXT HELPERS
    # =========================================================

    @staticmethod
    def _clean_text(
        value: str,
    ) -> str:

        return (
            " ".join(
                str(value or "").split()
            )
            .strip()
        )

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
                    (
                        position,
                        word,
                    )
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

    @staticmethod
    def _tokenize(
        text: str,
    ) -> List[str]:

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

            meaningful.append(
                token
            )

        return list(
            dict.fromkeys(
                meaningful
            )
        )

    @staticmethod
    def _build_search_query(
        query: str,
    ) -> str:

        cleaned = (
            LiteratureDiscoveryService
            ._clean_text(query)
        )

        return cleaned[:300]

    # =========================================================
    # OPENALEX
    # =========================================================

    async def fetch_openalex(
        self,
        query: str,
        limit: int = 20,
    ) -> List[PaperMetadata]:

        url = (
            "https://api.openalex.org/works"
        )

        params = {
            "search": (
                self._build_search_query(
                    query
                )
            ),
            "per-page": min(
                limit,
                50,
            ),
            "mailto": self.email,
        }

        if self.openalex_api_key:

            params[
                "api_key"
            ] = self.openalex_api_key

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
                        doi=work.get(
                            "doi"
                        ),
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
                "[OpenAlex discovery error]"
                f" {exc}"
            )

        print(
            "[Discovery]"
            f" OpenAlex candidates:"
            f" {len(papers)}"
        )

        return papers

    # =========================================================
    # ARXIV
    # =========================================================

    def _fetch_arxiv_sync(
        self,
        query: str,
        limit: int = 20,
    ) -> List[PaperMetadata]:

        search = arxiv.Search(
            query=(
                self._build_search_query(
                    query
                )
            ),
            max_results=min(
                limit,
                50,
            ),
            sort_by=(
                arxiv.SortCriterion.Relevance
            ),
        )

        papers = []

        try:

            for result in (
                self.arxiv_client.results(
                    search
                )
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
                            for author
                            in result.authors
                        ],
                        year=(
                            result.published.year
                            if result.published
                            else None
                        ),
                        doi=result.doi,
                        pdf_url=result.pdf_url,
                        citation_count=0,
                        venue=(
                            "arXiv preprint"
                        ),
                    )
                )

        except Exception as exc:

            print(
                "[arXiv discovery error]"
                f" {exc}"
            )

        print(
            "[Discovery]"
            f" arXiv candidates:"
            f" {len(papers)}"
        )

        return papers

    async def fetch_arxiv(
        self,
        query: str,
        limit: int = 20,
    ) -> List[PaperMetadata]:

        loop = (
            asyncio.get_running_loop()
        )

        return await loop.run_in_executor(
            None,
            self._fetch_arxiv_sync,
            query,
            limit,
        )

    # =========================================================
    # RELEVANCE SCORING
    # =========================================================

    def _score_paper(
        self,
        paper: PaperMetadata,
        query_tokens: List[str],
    ) -> Tuple[
        float,
        List[str],
    ]:

        if not query_tokens:

            return (
                0.0,
                [],
            )

        title = (
            paper.title or ""
        ).lower()

        abstract = (
            paper.abstract or ""
        ).lower()

        title_tokens = set(
            self._tokenize(
                title
            )
        )

        abstract_tokens = set(
            self._tokenize(
                abstract
            )
        )

        matched_terms = []

        title_score = 0.0

        abstract_score = 0.0

        for token in query_tokens:

            if token in title_tokens:

                title_score += 5.0

                matched_terms.append(
                    token
                )

            elif token in abstract_tokens:

                abstract_score += 1.0

                matched_terms.append(
                    token
                )

        query_phrase = (
            " ".join(
                query_tokens[:4]
            )
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

        unique_matches = list(
            dict.fromkeys(
                matched_terms
            )
        )

        if len(
            unique_matches
        ) >= 3:

            total_score += 4.0

        if len(
            unique_matches
        ) >= 5:

            total_score += 3.0

        return (
            total_score,
            unique_matches,
        )

    # =========================================================
    # LANGUAGE FILTER
    # =========================================================

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
            / max(
                len(cleaned),
                1,
            )
            < 0.55
        ):

            return False

        return True

    # =========================================================
    # SOURCE-SPECIFIC PREPARATION
    # =========================================================

    def _prepare_source_results(
        self,
        papers: List[PaperMetadata],
    ) -> List[PaperMetadata]:

        prepared = []

        seen_titles = set()

        for paper in papers:

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

            # Deduplicate ONLY within this source.
            #
            # Do NOT deduplicate OpenAlex against arXiv here.
            # The same work may legitimately exist in both
            # sources and the user requested N results
            # from EACH source.

            if (
                normalized_title
                in seen_titles
            ):
                continue

            seen_titles.add(
                normalized_title
            )

            prepared.append(
                paper
            )

        return prepared

    # =========================================================
    # SOURCE-AWARE RESULT SELECTION
    # =========================================================

    def _select_source_aware_results(
        self,
        scored,
        limit: int,
    ) -> List[PaperMetadata]:

        if (
            not scored
            or limit <= 0
        ):

            return []

        # -----------------------------------------------------
        # Separate candidates by source.
        # -----------------------------------------------------

        openalex = [
            item
            for item in scored
            if item[2].source
            == "OpenAlex"
        ]

        arxiv = [
            item
            for item in scored
            if item[2].source
            == "arXiv"
        ]

        # -----------------------------------------------------
        # Sort each source independently.
        # -----------------------------------------------------

        openalex.sort(
            key=lambda item: (
                item[0],
                item[2].citation_count
                or 0,
            ),
            reverse=True,
        )

        arxiv.sort(
            key=lambda item: (
                item[0],
                item[2].citation_count
                or 0,
            ),
            reverse=True,
        )

        # -----------------------------------------------------
        # IMPORTANT:
        #
        # `limit` means RESULTS PER SOURCE.
        #
        # limit=3:
        #   3 OpenAlex
        #   3 arXiv
        #
        # limit=5:
        #   5 OpenAlex
        #   5 arXiv
        #
        # limit=10:
        #   10 OpenAlex
        #   10 arXiv
        # -----------------------------------------------------

        def select_from_source(
            candidates,
            source_limit: int,
        ):

            selected = []

            seen_titles = set()

            for item in candidates:

                if (
                    len(selected)
                    >= source_limit
                ):
                    break

                paper = item[2]

                title = (
                    paper.title or ""
                ).strip()

                if not title:
                    continue

                normalized_title = (
                    self._normalise_title(
                        title
                    )
                )

                if not normalized_title:
                    continue

                # Deduplicate within this source.
                if (
                    normalized_title
                    in seen_titles
                ):
                    continue

                seen_titles.add(
                    normalized_title
                )

                selected.append(
                    item
                )

            return selected

        openalex_selected = (
            select_from_source(
                openalex,
                limit,
            )
        )

        arxiv_selected = (
            select_from_source(
                arxiv,
                limit,
            )
        )

        # -----------------------------------------------------
        # Combine the two sources.
        #
        # NO cross-source deduplication.
        # -----------------------------------------------------

        selected = (
            openalex_selected
            + arxiv_selected
        )

        # -----------------------------------------------------
        # Final relevance ordering.
        # -----------------------------------------------------

        selected.sort(
            key=lambda item: (
                item[0],
                item[2].citation_count
                or 0,
            ),
            reverse=True,
        )

        print(
            "[Discovery]"
            " Source-aware selection:"
            f" OpenAlex="
            f"{len(openalex_selected)}"
            f" | arXiv="
            f"{len(arxiv_selected)}"
            f" | Total="
            f"{len(selected)}"
        )

        return [
            item[2]
            for item in selected
        ]

    # =========================================================
    # GLOBAL SEARCH
    # =========================================================

    async def search_all(
        self,
        query: str,
        limit_per_source: int = 5,
    ) -> List[PaperMetadata]:

        query = (
            self._build_search_query(
                query
            )
        )

        if not query:
            return []

        query_tokens = (
            self._tokenize(
                query
            )
        )

        if not query_tokens:
            return []

        # -----------------------------------------------------
        # Fetch enough candidates from EACH source.
        #
        # We intentionally fetch more than requested because
        # relevance filtering happens after fetching.
        #
        # Example:
        # 3 per source
        # -> fetch at least 20 from each
        # -> score/filter
        # -> return best 3 from each
        # -----------------------------------------------------

        candidate_limit = max(
            20,
            limit_per_source * 4,
        )

        print(
            "\n"
            + "=" * 70
        )

        print(
            "[Discovery]"
            f" Query: {query}"
        )

        print(
            "[Discovery]"
            f" Concepts: {query_tokens}"
        )

        print(
            "[Discovery]"
            f" Requested per source:"
            f" {limit_per_source}"
        )

        print(
            "[Discovery]"
            f" Candidate fetch limit:"
            f" {candidate_limit}"
        )

        print(
            "=" * 70
        )

        # -----------------------------------------------------
        # Fetch OpenAlex and arXiv concurrently.
        # -----------------------------------------------------

        openalex_task = (
            self.fetch_openalex(
                query,
                limit=candidate_limit,
            )
        )

        arxiv_task = (
            self.fetch_arxiv(
                query,
                limit=candidate_limit,
            )
        )

        (
            openalex_results,
            arxiv_results,
        ) = await asyncio.gather(
            openalex_task,
            arxiv_task,
        )

        # -----------------------------------------------------
        # Prepare each source independently.
        #
        # This is important:
        #
        # We do NOT combine OpenAlex + arXiv and then globally
        # deduplicate, because that could remove one source's
        # result before source balancing happens.
        # -----------------------------------------------------

        openalex_unique = (
            self._prepare_source_results(
                openalex_results
            )
        )

        arxiv_unique = (
            self._prepare_source_results(
                arxiv_results
            )
        )

        print(
            "[Discovery]"
            f" OpenAlex unique:"
            f" {len(openalex_unique)}"
        )

        print(
            "[Discovery]"
            f" arXiv unique:"
            f" {len(arxiv_unique)}"
        )

        # -----------------------------------------------------
        # Score both sources.
        # -----------------------------------------------------

        scored = []

        for paper in (
            openalex_unique
            + arxiv_unique
        ):

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

        # -----------------------------------------------------
        # Sort by relevance first.
        #
        # Source-aware selection below will then take the
        # requested number from EACH source.
        # -----------------------------------------------------

        scored.sort(
            key=lambda item: (
                item[0],
                item[2].citation_count
                or 0,
            ),
            reverse=True,
        )

        print(
            "[Discovery]"
            f" Scored candidates:"
            f" {len(scored)}"
        )

        # -----------------------------------------------------
        # Remove weak matches BEFORE source selection.
        #
        # This means we won't return irrelevant papers just
        # to satisfy the requested count.
        # -----------------------------------------------------

        strong_scored = []

        for (
            score,
            matched_terms,
            paper,
        ) in scored:

            strong_match = (
                len(matched_terms) >= 2
                or score >= 10.0
            )

            if not strong_match:
                continue

            print(
                "[Discovery]"
                f" {score:.1f}"
                f" | {paper.source}"
                f" | {paper.title}"
                f" | matches="
                f"{matched_terms}"
            )

            strong_scored.append(
                (
                    score,
                    matched_terms,
                    paper,
                )
            )

        print(
            "[Discovery]"
            f" Strong candidates:"
            f" {len(strong_scored)}"
        )

        # -----------------------------------------------------
        # Select N relevant papers FROM EACH SOURCE.
        # -----------------------------------------------------

        results = (
            self._select_source_aware_results(
                strong_scored,
                limit_per_source,
            )
        )

        print(
            "[Discovery]"
            f" Returning:"
            f" {len(results)} papers"
        )

        source_counts = {}

        for paper in results:

            source_counts[
                paper.source
            ] = (
                source_counts.get(
                    paper.source,
                    0,
                )
                + 1
            )

        print(
            "[Discovery]"
            f" Final source counts:"
            f" {source_counts}"
        )

        print(
            "=" * 70
            + "\n"
        )

        return results

    # =========================================================
    # CITATION FORMATTER
    # =========================================================

    def paper_metadata_to_citation(
        self,
        paper: "PaperMetadata",
    ) -> Dict[str, Any]:

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