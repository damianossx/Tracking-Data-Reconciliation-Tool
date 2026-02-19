# src/ups_rma_reconciliation/graph_client.py

"""
Microsoft Graph API client (portfolio-ready skeleton).

This module demonstrates how the project could integrate with Microsoft 365 via
the Microsoft Graph API, for example to:
- upload the reconciled Excel report to SharePoint,
- download the latest baseline from a document library.

SECURITY NOTE:
- This GitHub version does NOT include secrets.
- Client credentials (tenant_id, client_id, client_secret) should be provided
  via environment variables or a secure store (e.g. Azure Key Vault).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os

import requests  # type: ignore[import-untyped]


@dataclass
class GraphConfig:
    """
    Configuration for the Graph client.

    Attributes
    ----------
    tenant_id:
        Azure AD tenant id.
    client_id:
        Application (client) id registered in Azure AD.
    client_secret:
        Client secret (NEVER commit this to source control).
    scope:
        Scope for client credentials; for Graph: 'https://graph.microsoft.com/.default'
    """

    tenant_id: str
    client_id: str
    client_secret: str
    scope: str = "https://graph.microsoft.com/.default"

    @classmethod
    def from_env(cls) -> "GraphConfig":
        """
        Build GraphConfig from environment variables:

        - GRAPH_TENANT_ID
        - GRAPH_CLIENT_ID
        - GRAPH_CLIENT_SECRET
        """
        return cls(
            tenant_id=os.environ.get("GRAPH_TENANT_ID", ""),
            client_id=os.environ.get("GRAPH_CLIENT_ID", ""),
            client_secret=os.environ.get("GRAPH_CLIENT_SECRET", ""),
        )


class GraphClient:
    """
    Minimal Graph API client for file upload/download.

    For brevity, only the upload scenario is implemented, but the pattern
    is the same for downloads.
    """

    def __init__(self, config: GraphConfig) -> None:
        if not config.tenant_id or not config.client_id or not config.client_secret:
            raise ValueError(
                "GraphConfig is incomplete. "
                "Make sure tenant_id, client_id, and client_secret are provided."
            )
        self.config = config
        self._access_token: Optional[str] = None

    def _acquire_token(self) -> str:
        """
        Acquire an access token using the OAuth2 client credentials flow.

        In production code, it is recommended to use the 'msal' library.
        """
        token_url = (
            f"https://login.microsoftonline.com/{self.config.tenant_id}/oauth2/v2.0/token"
        )
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": self.config.scope,
            "grant_type": "client_credentials",
        }

        response = requests.post(token_url, data=data, timeout=30)
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise RuntimeError("Could not obtain access token from Graph.")
        self._access_token = token
        return token

    @property
    def access_token(self) -> str:
        """
        Lazy-loaded access token property.
        """
        if not self._access_token:
            return self._acquire_token()
        return self._access_token

    def upload_file_to_sharepoint(
        self,
        site_id: str,
        drive_id: str,
        folder_path: str,
        local_file_path: Path,
    ) -> dict:
        """
        Upload a local file to a SharePoint document library using Graph.

        Parameters
        ----------
        site_id:
            SharePoint site id.
        drive_id:
            Drive (document library) id.
        folder_path:
            Folder path inside the drive (e.g. 'Shared Documents/UPS Reports').
        local_file_path:
            Local file path to upload.

        Returns
        -------
        dict
            Graph API JSON response.
        """
        if not local_file_path.exists():
            raise FileNotFoundError(local_file_path)

        url = (
            "https://graph.microsoft.com/v1.0/"
            f"sites/{site_id}/drives/{drive_id}/root:/{folder_path}/{local_file_path.name}:/content"
        )

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/octet-stream",
        }

        with open(local_file_path, "rb") as f:
            data = f.read()

        resp = requests.put(url, headers=headers, data=data, timeout=60)
        resp.raise_for_status()
        return resp.json()