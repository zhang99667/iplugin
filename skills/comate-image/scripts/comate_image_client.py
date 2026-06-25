#!/usr/bin/env python3
"""Stdlib-only Comate image generation client used by the comate-image skill."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request


DEFAULT_BASE_URL = "https://oneapi-comate.baidu-int.com"
DEFAULT_MODELS = {
    "images": "gpt-image-2",
    "responses": "gpt-5.5",
    "banana": "gemini-3.1-flash-image-preview",
}
AUTH_STATUS_CODES = {401, 403}


@dataclass
class GeneratedImage:
    image_bytes: bytes
    mime_type: str
    response_path: str
    raw: dict[str, Any]


class ComateImageError(RuntimeError):
    pass


class ComateAuthError(ComateImageError):
    pass


class ComateImageClient:
    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL, timeout: int = 180):
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def images_generations(
        self,
        prompt: str,
        model: str = DEFAULT_MODELS["images"],
        size: str = "1024x1024",
        n: int = 1,
    ) -> GeneratedImage:
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": n,
        }
        data = self._post_json("/v1/images/generations", payload)
        try:
            b64 = data["data"][0]["b64_json"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ComateImageError("missing data[0].b64_json in images/generations response") from exc
        output_format = data.get("output_format") or "png"
        return self._decode_image(b64, f"image/{output_format}", "data[0].b64_json", data)

    def responses_image_generation(
        self,
        prompt: str,
        model: str = DEFAULT_MODELS["responses"],
    ) -> GeneratedImage:
        payload = {
            "model": model,
            "input": prompt,
            "tools": [{"type": "image_generation"}],
        }
        data = self._post_json("/v1/responses", payload)
        for idx, item in enumerate(data.get("output") or []):
            if isinstance(item, dict) and item.get("type") == "image_generation_call":
                b64 = item.get("result")
                if isinstance(b64, str) and b64:
                    output_format = item.get("output_format") or "png"
                    return self._decode_image(
                        b64,
                        f"image/{output_format}",
                        f"output[{idx}].result",
                        data,
                    )
        raise ComateImageError("missing image_generation_call result in responses output")

    def banana_generate_content(
        self,
        prompt: str,
        model: str = DEFAULT_MODELS["banana"],
    ) -> GeneratedImage:
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
            },
        }
        path = f"/v1beta/models/{model}:generateContent"
        data = self._post_json(path, payload)
        for img_path, mime_type, b64 in _iter_inline_images(data):
            return self._decode_image(b64, mime_type, img_path, data)
        raise ComateImageError("missing inlineData.data image in generateContent response")

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(self.base_url + path, data=body, method="POST")
        req.add_header("Authorization", "Bearer " + self.api_key)
        req.add_header("Content-Type", "application/json")
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
        except error.HTTPError as exc:
            raw = exc.read()
            message = raw.decode("utf-8", errors="replace")[:2000]
            if exc.code in AUTH_STATUS_CODES:
                raise ComateAuthError(f"HTTP {exc.code}: API key is missing, invalid, or expired") from exc
            raise ComateImageError(f"HTTP {exc.code}: {message}") from exc
        except error.URLError as exc:
            raise ComateImageError(str(exc)) from exc

        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ComateImageError("unexpected non-JSON response") from exc
        if isinstance(data, dict) and data.get("error") is not None:
            raise ComateImageError(json.dumps(data["error"], ensure_ascii=False))
        if not isinstance(data, dict):
            raise ComateImageError("unexpected non-object JSON response")
        return data

    @staticmethod
    def _decode_image(b64: str, mime_type: str, response_path: str, raw: dict[str, Any]) -> GeneratedImage:
        return GeneratedImage(
            image_bytes=base64.b64decode(b64),
            mime_type=mime_type,
            response_path=response_path,
            raw=raw,
        )


def _iter_inline_images(value: Any, path: str = "$"):
    if isinstance(value, dict):
        inline = value.get("inlineData") or value.get("inline_data")
        if isinstance(inline, dict):
            data = inline.get("data")
            mime_type = inline.get("mimeType") or inline.get("mime_type") or "application/octet-stream"
            if isinstance(data, str) and data:
                yield path + ".inlineData.data", mime_type, data
        for key, child in value.items():
            yield from _iter_inline_images(child, path + "." + str(key))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            yield from _iter_inline_images(child, f"{path}[{idx}]")


def _extension_for_mime(mime_type: str) -> str:
    guessed = mimetypes.guess_extension(mime_type) or ".bin"
    return ".jpg" if guessed == ".jpe" else guessed


def _path_with_extension(path: Path, mime_type: str) -> Path:
    if path.suffix:
        return path
    return path.with_suffix(_extension_for_mime(mime_type))


def _safe_stem(text: str, fallback: str = "comate-image") -> str:
    normalized = unicodedata.normalize("NFKC", text).strip().lower()
    normalized = re.sub(
        r"(不要文字|无文字|不要水印|无水印|no text|no watermark|写实风格|高清|细节丰富)",
        " ",
        normalized,
        flags=re.IGNORECASE,
    )
    tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", normalized)
    if not tokens:
        return fallback

    parts: list[str] = []
    for token in tokens:
        if re.fullmatch(r"[\u4e00-\u9fff]+", token):
            parts.append(token[:18])
        elif token not in {"a", "an", "the", "and", "with", "for", "of", "in", "on"}:
            parts.append(token)
        if len("-".join(parts)) >= 48:
            break

    stem = "-".join(parts).strip("-")
    return stem[:64].strip("-") or fallback


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for index in range(2, 1000):
        candidate = parent / f"{stem}-{index}{suffix}"
        if not candidate.exists():
            return candidate
    raise ComateImageError(f"could not find unused output path for {path}")


def _read_api_key(api_key_file: str | None) -> str:
    env_key = os.environ.get("COMATE_API_KEY", "").strip()
    if env_key:
        return env_key

    key_file = api_key_file or os.environ.get("COMATE_API_KEY_FILE", "").strip()
    if not key_file:
        return ""

    path = Path(key_file).expanduser()
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ComateAuthError(f"could not read API key file: {path}") from exc


def _generate_image(client: ComateImageClient, backend: str, prompt: str, model: str, size: str) -> GeneratedImage:
    if backend == "images":
        return client.images_generations(prompt=prompt, model=model, size=size)
    if backend == "responses":
        return client.responses_image_generation(prompt=prompt, model=model)
    return client.banana_generate_content(prompt=prompt, model=model)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate images through Comate-compatible APIs.")
    parser.add_argument("backend", nargs="?", choices=sorted(DEFAULT_MODELS), default="images")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--out", help="Full output path. Extension is inferred from MIME when omitted.")
    parser.add_argument("--out-dir", default=".", help="Directory used when --out is omitted.")
    parser.add_argument("--stem", help="Semantic output basename without extension.")
    parser.add_argument("--model")
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--api-key-file", help="Path to a local file that contains COMATE_API_KEY.")
    args = parser.parse_args()

    try:
        api_key = _read_api_key(args.api_key_file)
        if not api_key:
            raise ComateAuthError("COMATE_API_KEY or COMATE_API_KEY_FILE is required")

        model = args.model or DEFAULT_MODELS[args.backend]
        client = ComateImageClient(api_key=api_key, base_url=args.base_url, timeout=args.timeout)
        image = _generate_image(client, args.backend, args.prompt, model, args.size)

        if args.out:
            out_path = _path_with_extension(Path(args.out).expanduser(), image.mime_type)
        else:
            stem = _safe_stem(args.stem or args.prompt)
            out_path = Path(args.out_dir).expanduser() / f"{stem}{_extension_for_mime(image.mime_type)}"
        out_path = _unique_path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(image.image_bytes)

        print(f"saved: {out_path}")
        print(f"mime: {image.mime_type}")
        print(f"bytes: {len(image.image_bytes)}")
        print(f"response_path: {image.response_path}")
        return 0
    except ComateAuthError as exc:
        print(f"auth_error: {exc}", file=sys.stderr)
        return 2
    except ComateImageError as exc:
        print(f"comate_image_error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
