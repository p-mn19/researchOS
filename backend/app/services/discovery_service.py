import asyncio
import os
import httpx
import arxiv
from typing import List
from app.models.schemas import PaperMetadata
from app.config import settings  # Or use os.getenv directly

class LiteratureDiscoveryService:
    def __init__(self):
        self.openalex_api_key = getattr(settings, "OPENALEX_API_KEY", os.getenv("OPENALEX_API_KEY", None))
        self.email = getattr(settings, "OPENALEX_EMAIL", os.getenv("OPENALEX_EMAIL", "developer@researchos.local"))
        
        self.arxiv_client = arxiv.Client(
            page_size=20,
            delay_seconds=5.0,  # <-- Increase this from 3.0 to 5.0
            num_retries=3
            )

    async def fetch_openalex(self, query: str, limit: int = 5) -> List[PaperMetadata]:
        url = "https://api.openalex.org/works"
        params = {"search": query, "per_page": limit, "mailto": self.email}
        if self.openalex_api_key:
            params["api_key"] = self.openalex_api_key

        papers = []
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    for work in data.get("results", []):
                        abstract = None
                        inv_index = work.get("abstract_inverted_index")
                        if inv_index:
                            word_positions = []
                            for word, positions in inv_index.items():
                                for pos in positions:
                                    word_positions.append((pos, word))
                            word_positions.sort(key=lambda x: x[0])
                            abstract = " ".join([w[1] for w in word_positions])

                        authors = [
                            a.get("author", {}).get("display_name", "")
                            for a in work.get("authorships", [])
                            if a.get("author", {}).get("display_name")
                        ]

                        papers.append(PaperMetadata(
                            source="OpenAlex",
                            source_id=work.get("id", ""),
                            title=work.get("title", "Untitled").strip(),
                            abstract=abstract or "No abstract available",
                            authors=authors,
                            year=work.get("publication_year"),
                            doi=work.get("doi"),
                            pdf_url=work.get("open_access", {}).get("oa_url"),
                            citation_count=work.get("cited_by_count", 0),
                            venue=work.get("primary_location", {}).get("source", {}).get("display_name", "Academic Venue")
                        ))
        except Exception as e:
            print(f"[OpenAlex Service Error]: {e}")
        return papers

    def _sync_fetch_arxiv(self, query: str, limit: int = 5) -> List[PaperMetadata]:
        search = arxiv.Search(
            query=query,
            max_results=limit,
            sort_by=arxiv.SortCriterion.Relevance
        )
        papers = []
        try:
            for result in self.arxiv_client.results(search):
                papers.append(PaperMetadata(
                    source="arXiv",
                    source_id=result.get_short_id(),
                    title=result.title.strip().replace("\n", " "),
                    abstract=result.summary.strip().replace("\n", " "),
                    authors=[a.name for a in result.authors],
                    year=result.published.year if result.published else None,
                    doi=result.doi,
                    pdf_url=result.pdf_url,
                    citation_count=0,
                    venue="arXiv Preprint"
                ))
        except Exception as e:
            print(f"[arXiv Service Error]: {e}")
        return papers

    async def fetch_arxiv(self, query: str, limit: int = 5) -> List[PaperMetadata]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_fetch_arxiv, query, limit)

    async def search_all(self, query: str, limit_per_source: int = 5) -> List[PaperMetadata]:
        openalex_task = self.fetch_openalex(query, limit=limit_per_source)
        arxiv_task = self.fetch_arxiv(query, limit=limit_per_source)

        openalex_results, arxiv_results = await asyncio.gather(openalex_task, arxiv_task)
        combined = openalex_results + arxiv_results

        unique_papers = []
        seen_titles = set()
        for p in combined:
            normalized_title = "".join(filter(str.isalnum, p.title.lower()))
            if normalized_title and normalized_title not in seen_titles:
                seen_titles.add(normalized_title)
                unique_papers.append(p)

        return unique_papers