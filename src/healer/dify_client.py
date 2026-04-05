"""Zone 4 — Healer: Dify Knowledge Base Ingestion API client."""

from __future__ import annotations

import csv
import io
import os

import httpx


class DifyKBClient:
    """Thin wrapper around Dify's self-hosted Knowledge Base API."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("DIFY_BASE_URL", "http://localhost")).rstrip("/")
        self.api_key = api_key or os.getenv("DIFY_API_KEY", "")
        self._client = httpx.Client(
            base_url=f"{self.base_url}/v1",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0,
        )

    def create_document_by_text(
        self,
        dataset_id: str,
        text: str,
        name: str = "healed_data.csv",
    ) -> dict:
        """Upload text content as a document to a Dify Knowledge Base.

        POST /v1/datasets/{dataset_id}/document/create-by-text
        """
        payload = {
            "name": name,
            "text": text,
            "data_source": {
                "type": "upload_file",
            },
        }
        resp = self._client.post(
            f"/datasets/{dataset_id}/document/create-by-text",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    def list_documents(self, dataset_id: str) -> dict:
        """List documents in a Knowledge Base."""
        resp = self._client.get(f"/datasets/{dataset_id}/documents")
        resp.raise_for_status()
        return resp.json()

    def upload_csv(
        self,
        dataset_id: str,
        csv_data: list[dict],
        name: str = "healed_data.csv",
    ) -> dict:
        """Serialize rows to CSV text and upload to a Dify Knowledge Base."""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=csv_data[0].keys())
        writer.writeheader()
        writer.writerows(csv_data)
        return self.create_document_by_text(dataset_id, output.getvalue(), name)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "DifyKBClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
