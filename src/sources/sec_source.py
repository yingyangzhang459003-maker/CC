from __future__ import annotations

import requests

from src.sources.base_source import BaseSource, SourceMessage
from src.utils import utc_now_iso


class SECSource(BaseSource):
    def __init__(self, cik: str, watched_forms: list[str], user_agent: str, limit: int = 20):
        self.cik = cik.zfill(10)
        self.watched_forms = set(watched_forms)
        self.user_agent = user_agent
        self.limit = limit

    def fetch(self) -> list[SourceMessage]:
        url = f"https://data.sec.gov/submissions/CIK{self.cik}.json"
        headers = {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        accession_numbers = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        messages: list[SourceMessage] = []
        for idx, form in enumerate(forms[: self.limit]):
            if form not in self.watched_forms:
                continue
            accession = accession_numbers[idx]
            accession_no_dash = accession.replace("-", "")
            primary_doc = primary_docs[idx] if idx < len(primary_docs) else ""
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(self.cik)}/{accession_no_dash}/{primary_doc}"
            title = f"NVIDIA SEC filing: {form} filed on {filing_dates[idx]}"
            messages.append(SourceMessage(
                source="sec_edgar",
                source_account="SEC EDGAR NVIDIA",
                title=title,
                content=f"NVIDIA filed {form} with SEC EDGAR. Accession number: {accession}.",
                url=filing_url,
                published_at=filing_dates[idx] if idx < len(filing_dates) else utc_now_iso(),
                entities=["NVIDIA", "SEC", form],
                keywords=["NVIDIA", "SEC", form],
                metadata={"source_quality": "official", "accession_number": accession, "form": form},
            ))
        return messages
