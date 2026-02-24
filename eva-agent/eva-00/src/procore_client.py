"""Procore API client with automatic token refresh."""

import json
import time
import requests
from pathlib import Path

CREDS_DIR = Path("/home/moby/.openclaw/workspace/.credentials")
TOKEN_PATH = CREDS_DIR / "procore_token.json"
ENV_PATH = CREDS_DIR / "procore.env"

# Sandbox endpoints
AUTH_URL = "https://login-sandbox.procore.com/oauth/token"
API_BASE = "https://sandbox.procore.com"


def _load_env():
    """Load client ID and secret from env file."""
    env = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k] = v
    return env


def _load_token():
    """Load saved token."""
    with open(TOKEN_PATH) as f:
        return json.load(f)


def _save_token(token_data):
    """Save token to disk."""
    token_data['saved_at'] = time.time()
    with open(TOKEN_PATH, 'w') as f:
        json.dump(token_data, f, indent=2)


class ProcoreClient:
    """Procore API client with auto-refresh."""

    def __init__(self, company_id: int = 4281379):
        self.company_id = company_id
        env = _load_env()
        self.client_id = env['PROCORE_CLIENT_ID']
        self.client_secret = env['PROCORE_CLIENT_SECRET']
        self.token = _load_token()
        self._ensure_fresh_token()

    def _ensure_fresh_token(self):
        """Refresh token if expired or close to expiry."""
        saved_at = self.token.get('saved_at', 0)
        expires_in = self.token.get('expires_in', 5400)
        if time.time() - saved_at > (expires_in - 300):  # refresh 5 min early
            self._refresh_token()

    def _refresh_token(self):
        """Refresh the OAuth token."""
        resp = requests.post(AUTH_URL, data={
            'grant_type': 'refresh_token',
            'refresh_token': self.token['refresh_token'],
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        })
        resp.raise_for_status()
        self.token = resp.json()
        _save_token(self.token)

    def _headers(self):
        return {
            'Authorization': f'Bearer {self.token["access_token"]}',
            'Procore-Company-Id': str(self.company_id),
        }

    def get(self, path: str, params: dict = None) -> requests.Response:
        """GET request with auto-refresh on 401."""
        self._ensure_fresh_token()
        resp = requests.get(f'{API_BASE}{path}', headers=self._headers(), params=params)
        if resp.status_code == 401:
            self._refresh_token()
            resp = requests.get(f'{API_BASE}{path}', headers=self._headers(), params=params)
        return resp

    def get_json(self, path: str, params: dict = None) -> list | dict:
        """GET request, return JSON."""
        resp = self.get(path, params)
        resp.raise_for_status()
        return resp.json()

    def get_all(self, path: str, params: dict = None, per_page: int = 100) -> list:
        """GET all pages of a paginated endpoint."""
        params = params or {}
        params['per_page'] = per_page
        all_items = []
        page = 1
        while True:
            params['page'] = page
            data = self.get_json(path, params)
            if not data:
                break
            all_items.extend(data)
            if len(data) < per_page:
                break
            page += 1
        return all_items

    def download(self, url: str, dest: Path) -> Path:
        """Download a file from a Procore URL."""
        self._ensure_fresh_token()
        resp = requests.get(url, headers=self._headers(), stream=True)
        resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return dest

    # Convenience methods
    def list_projects(self) -> list:
        return self.get_all(f'/rest/v1.1/projects', {'company_id': self.company_id})

    def list_drawing_areas(self, project_id: int) -> list:
        return self.get_json(f'/rest/v1.0/projects/{project_id}/drawing_areas')

    def list_drawing_revisions(self, project_id: int) -> list:
        return self.get_all(f'/rest/v1.0/projects/{project_id}/drawing_revisions')

    def list_drawing_sets(self, project_id: int) -> list:
        return self.get_json(f'/rest/v1.0/projects/{project_id}/drawing_sets')

    def list_submittals(self, project_id: int) -> list:
        return self.get_all(f'/rest/v1.1/projects/{project_id}/submittals')

    def list_rfis(self, project_id: int) -> list:
        return self.get_all(f'/rest/v1.0/projects/{project_id}/rfis')

    def list_documents(self, project_id: int) -> list:
        return self.get_json(f'/rest/v1.0/projects/{project_id}/documents')
