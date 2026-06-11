import os

import requests
from requests.auth import HTTPBasicAuth


class VindiAPI:
    """Cliente simples (somente leitura) da API da Vindi.

    Autenticação: HTTP Basic com a chave privada como usuário e senha vazia.
    A chave vem do .env (VINDI_API_KEY) e nunca é versionada.
    """

    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or os.getenv("VINDI_API_KEY", "")
        self.base_url = (
            base_url or os.getenv("VINDI_API_URL") or "https://app.vindi.com.br/api/v1"
        ).rstrip("/")
        self.auth = HTTPBasicAuth(self.api_key, "")

    def _get(self, path, params=None):
        resp = requests.get(f"{self.base_url}{path}", auth=self.auth, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def listar(self, recurso, params=None, max_paginas=200):
        """Percorre todas as páginas de um recurso e devolve a lista completa."""
        params = dict(params or {})
        params.setdefault("per_page", 50)
        itens = []
        pagina = 1
        while pagina <= max_paginas:
            params["page"] = pagina
            dados = self._get(f"/{recurso}", params)
            lote = dados.get(recurso, [])
            itens.extend(lote)
            if len(lote) < params["per_page"]:
                break
            pagina += 1
        return itens
