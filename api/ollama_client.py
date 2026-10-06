"""
Ollama HTTP client for Quantum Portal API.
All methods are async, use httpx with proper timeouts and error handling.
Base URL: http://localhost:11434
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_OLLAMA_BASE = "http://localhost:11434"
_TIMEOUT_S = 60.0
_EMBED_TIMEOUT_S = 30.0
_HEALTH_TIMEOUT_S = 5.0


class OllamaClient:
    """Async Ollama HTTP client. No model loading at import time."""

    base_url: str = _OLLAMA_BASE

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    @staticmethod
    async def health() -> Dict[str, Any]:
        """Return Ollama health status and available models.

        Returns dict with keys: available (bool), models (list[str]), error (str|None).
        Never raises — errors are captured in the return value.
        """
        try:
            async with httpx.AsyncClient(timeout=_HEALTH_TIMEOUT_S) as client:
                resp = await client.get(f"{_OLLAMA_BASE}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                return {"available": True, "models": models, "error": None}
        except httpx.ConnectError:
            return {"available": False, "models": [], "error": "Connection refused — is Ollama running?"}
        except httpx.TimeoutException:
            return {"available": False, "models": [], "error": "Timeout connecting to Ollama"}
        except Exception as exc:
            return {"available": False, "models": [], "error": str(exc)}

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------

    @staticmethod
    async def list_models() -> List[str]:
        """Return list of model names available in Ollama.

        Returns empty list on any error.
        """
        try:
            async with httpx.AsyncClient(timeout=_HEALTH_TIMEOUT_S) as client:
                resp = await client.get(f"{_OLLAMA_BASE}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception as exc:
            logger.warning("OllamaClient.list_models failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    @staticmethod
    async def chat(
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = False,
    ) -> str:
        """Send a chat request to Ollama and return the assistant's reply text.

        Args:
            model: Ollama model name, e.g. "llama3.2", "mistral".
            messages: List of {"role": "user"|"assistant"|"system", "content": "..."} dicts.
            stream: Must be False — streaming is not supported by this method.

        Returns:
            Assistant reply as a plain string, or an error string prefixed with "[ERROR]".
        """
        payload = {"model": model, "messages": messages, "stream": False}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
                resp = await client.post(f"{_OLLAMA_BASE}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("message", {}).get("content", "")
        except httpx.ConnectError:
            return "[ERROR] Ollama not available — connection refused"
        except httpx.TimeoutException:
            return "[ERROR] Ollama request timed out"
        except httpx.HTTPStatusError as exc:
            return f"[ERROR] Ollama HTTP {exc.response.status_code}: {exc.response.text[:200]}"
        except Exception as exc:
            logger.warning("OllamaClient.chat failed: %s", exc)
            return f"[ERROR] {exc}"

    # ------------------------------------------------------------------
    # Embed
    # ------------------------------------------------------------------

    @staticmethod
    async def embed(model: str, text: str) -> List[float]:
        """Get an embedding vector for text from Ollama.

        Args:
            model: Embedding model name, e.g. "nomic-embed-text".
            text: Text to embed.

        Returns:
            List of floats (embedding vector), or empty list on error.
        """
        payload = {"model": model, "prompt": text}
        try:
            async with httpx.AsyncClient(timeout=_EMBED_TIMEOUT_S) as client:
                resp = await client.post(f"{_OLLAMA_BASE}/api/embeddings", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("embedding", [])
        except httpx.ConnectError:
            logger.warning("OllamaClient.embed: Ollama not available")
            return []
        except httpx.TimeoutException:
            logger.warning("OllamaClient.embed: timed out")
            return []
        except Exception as exc:
            logger.warning("OllamaClient.embed failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------

    @staticmethod
    async def generate(model: str, prompt: str, system: str = "") -> str:
        """Send a /api/generate request (single-turn, non-streaming).

        Args:
            model: Ollama model name.
            prompt: User prompt text.
            system: Optional system prompt.

        Returns:
            Generated text, or error string prefixed with "[ERROR]".
        """
        payload: Dict[str, Any] = {"model": model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
                resp = await client.post(f"{_OLLAMA_BASE}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "")
        except httpx.ConnectError:
            return "[ERROR] Ollama not available — connection refused"
        except httpx.TimeoutException:
            return "[ERROR] Ollama request timed out"
        except httpx.HTTPStatusError as exc:
            return f"[ERROR] Ollama HTTP {exc.response.status_code}: {exc.response.text[:200]}"
        except Exception as exc:
            logger.warning("OllamaClient.generate failed: %s", exc)
            return f"[ERROR] {exc}"
