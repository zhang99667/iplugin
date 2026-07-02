#!/usr/bin/env python3
"""Stdlib-only image generation client used by the generate-image skill."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
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
BACKEND_ALIASES = {
    "gptimg2": "images",
    "gpt-image-2": "images",
    "gpt_image_2": "images",
    "gptimage2": "images",
    "banana2": "banana",
    "gemini": "banana",
    "response": "responses",
}
AUTH_STATUS_CODES = {401, 403}


@dataclass
class GeneratedImage:
    """保存后端返回的已解码图片及其响应定位信息。"""

    image_bytes: bytes
    mime_type: str
    response_path: str
    raw: dict[str, Any]


@dataclass
class GeneratedCandidate:
    """保存一次并发候选请求的序号和生成结果，便于后续人工视觉筛选。"""

    index: int
    image: GeneratedImage


class GenerateImageError(RuntimeError):
    """表示非鉴权类图片生成失败，便于 CLI 统一输出错误。"""


class GenerateImageAuthError(GenerateImageError):
    """表示 API key 缺失、无效或过期，调用方可据此触发刷新流程。"""


@dataclass
class CandidateFailure:
    """保存单个候选请求的失败信息，避免一个请求失败时丢失其他成功候选。"""

    index: int
    error: GenerateImageError


def _default_api_key_file() -> Path:
    """返回默认 API key 缓存路径，避免密钥落入仓库工作区。"""
    config_home = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base_dir = Path(config_home).expanduser() if config_home else Path.home() / ".config"
    return base_dir / "iplugin" / "generate-image-api-key"


class GenerateImageClient:
    """封装兼容 OpenAI / Gemini 风格的图片生成接口。"""

    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL, timeout: int = 180):
        """初始化客户端，并统一规范 base URL，避免后续拼接路径出错。"""
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
        """通过 /v1/images/generations 链路生成图片。"""
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
            raise GenerateImageError("missing data[0].b64_json in images/generations response") from exc
        output_format = data.get("output_format") or "png"
        return self._decode_image(b64, f"image/{output_format}", "data[0].b64_json", data)

    def responses_image_generation(
        self,
        prompt: str,
        model: str = DEFAULT_MODELS["responses"],
    ) -> GeneratedImage:
        """通过 Responses 的 image_generation tool 链路生成图片。"""
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
        raise GenerateImageError("missing image_generation_call result in responses output")

    def banana_generate_content(
        self,
        prompt: str,
        model: str = DEFAULT_MODELS["banana"],
    ) -> GeneratedImage:
        """通过 Gemini 兼容的 generateContent 链路生成图片。"""
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
        raise GenerateImageError("missing inlineData.data image in generateContent response")

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """发送 JSON 请求并返回对象响应，同时把鉴权错误分流出来。"""
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
                raise GenerateImageAuthError(f"HTTP {exc.code}: API key is missing, invalid, or expired") from exc
            raise GenerateImageError(f"HTTP {exc.code}: {message}") from exc
        except error.URLError as exc:
            raise GenerateImageError(str(exc)) from exc

        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise GenerateImageError("unexpected non-JSON response") from exc
        if isinstance(data, dict) and data.get("error") is not None:
            raise GenerateImageError(json.dumps(data["error"], ensure_ascii=False))
        if not isinstance(data, dict):
            raise GenerateImageError("unexpected non-object JSON response")
        return data

    @staticmethod
    def _decode_image(b64: str, mime_type: str, response_path: str, raw: dict[str, Any]) -> GeneratedImage:
        """把 base64 图片解码为 GeneratedImage，保留原始响应用于排查。"""
        return GeneratedImage(
            image_bytes=base64.b64decode(b64),
            mime_type=mime_type,
            response_path=response_path,
            raw=raw,
        )


def _iter_inline_images(value: Any, path: str = "$"):
    """递归扫描 Gemini 风格响应，产出内联图片的位置、类型和数据。"""
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
    """根据 MIME 类型推导文件后缀，保护没有显式扩展名的输出路径。"""
    guessed = mimetypes.guess_extension(mime_type) or ".bin"
    return ".jpg" if guessed == ".jpe" else guessed


def _path_with_extension(path: Path, mime_type: str) -> Path:
    """保留用户显式后缀；未提供时按 MIME 类型自动补齐。"""
    if path.suffix:
        return path
    return path.with_suffix(_extension_for_mime(mime_type))


def _clean_prompt(prompt: str) -> str:
    """剥离路由词和口语化前后缀，避免把工具选择词送进图片 prompt。"""
    cleaned = unicodedata.normalize("NFKC", prompt).strip()
    route_words = (
        r"generate-image|generate_image|comate|oneapi-comate|gptimg2|gpt-image-2|gpt_image_2|gptimage2|"
        r"banana2?|gemini|responses?|image_generation"
    )
    leading_patterns = [
        rf"^(请|帮我|给我)?\s*(用|使用|通过|调用|走)?\s*({route_words})\s*(生成图片|出图|画图|画一张图|画张图)?\s*[,，:：。 ]*",
        r"^(请|帮我|给我)?\s*(生成图片|出图|画图|画一张图|画张图|图片生成)\s*[,，:：。 ]*",
        r"^(prompt|提示词)\s*(是|为)?\s*[,，:： ]*",
    ]
    trailing_patterns = [
        rf"[,，。 ]*(请|帮我|给我)?\s*(用|使用|通过|调用|走)\s*({route_words})\s*(生成图片|出图|画图|画一张图|画张图)?\s*$",
    ]
    previous = None
    while previous != cleaned:
        previous = cleaned
        for pattern in leading_patterns + trailing_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned or prompt.strip()


def _safe_stem(text: str, fallback: str = "generate-image") -> str:
    """从 prompt 中生成安全文件名主干，兼顾中文语义和路径长度。"""
    normalized = _clean_prompt(text).lower()
    normalized = re.sub(
        r"(不要文字|无文字|不要水印|无水印|no text|no watermark|写实风格|高清|细节丰富"
        r"|generate-image|generate_image|comate|gptimg2|gpt-image-2|banana2?)",
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
    """输出路径已存在时追加序号，避免覆盖用户已有图片。"""
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for index in range(2, 1000):
        candidate = parent / f"{stem}-{index}{suffix}"
        if not candidate.exists():
            return candidate
    raise GenerateImageError(f"could not find unused output path for {path}")


def _read_key_file(path: Path, required: bool) -> str:
    """读取本地 API key 文件；必需文件缺失时转为鉴权错误。"""
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        if required:
            raise GenerateImageAuthError(f"could not read API key file: {path}") from None
        return ""
    except OSError as exc:
        raise GenerateImageAuthError(f"could not read API key file: {path}") from exc


def _write_api_key_file(path: Path, api_key: str) -> None:
    """以 0600 权限保存 API key，降低令牌被其他本地用户读取的风险。"""
    key = api_key.strip()
    if not key:
        raise GenerateImageAuthError("empty API key from stdin")
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(key + "\n")
        os.chmod(path, 0o600)
    except OSError as exc:
        raise GenerateImageAuthError(f"could not save API key file: {path}") from exc


def _api_key_file_path(api_key_file: str | None) -> Path:
    """解析 API key 文件路径，显式参数优先于默认缓存位置。"""
    if api_key_file:
        return Path(api_key_file).expanduser()
    return _default_api_key_file()


def _read_api_key(api_key_file: str | None) -> str:
    """按环境变量、显式文件、默认缓存的优先级读取 API key。"""
    for env_name in ("GENERATE_IMAGE_API_KEY", "COMATE_API_KEY"):
        env_key = os.environ.get(env_name, "").strip()
        if env_key:
            return env_key

    key_file = (
        api_key_file
        or os.environ.get("GENERATE_IMAGE_API_KEY_FILE", "").strip()
        or os.environ.get("COMATE_API_KEY_FILE", "").strip()
    )
    if key_file:
        return _read_key_file(Path(key_file).expanduser(), required=True)

    return _read_key_file(_default_api_key_file(), required=False)


def _generate_image(client: GenerateImageClient, backend: str, prompt: str, model: str, size: str) -> GeneratedImage:
    """根据规范化后的 backend 分发到对应生成链路。"""
    if backend == "images":
        return client.images_generations(prompt=prompt, model=model, size=size)
    if backend == "responses":
        return client.responses_image_generation(prompt=prompt, model=model)
    return client.banana_generate_content(prompt=prompt, model=model)


def _generate_candidate(
    index: int,
    api_key: str,
    base_url: str,
    timeout: int,
    backend: str,
    prompt: str,
    model: str,
    size: str,
) -> GeneratedCandidate:
    """为每个候选创建独立客户端实例，隔离并发请求的超时和异常。"""
    client = GenerateImageClient(api_key=api_key, base_url=base_url, timeout=timeout)
    return GeneratedCandidate(index=index, image=_generate_image(client, backend, prompt, model, size))


def _generate_candidates(
    api_key: str,
    base_url: str,
    timeout: int,
    backend: str,
    prompt: str,
    model: str,
    size: str,
    count: int,
) -> tuple[list[GeneratedCandidate], list[CandidateFailure]]:
    """并发生成候选图；只要有成功候选就继续交给视觉筛选。"""
    if count < 1:
        raise GenerateImageError("--candidates must be at least 1")
    if count == 1:
        try:
            return [_generate_candidate(1, api_key, base_url, timeout, backend, prompt, model, size)], []
        except GenerateImageError as exc:
            return [], [CandidateFailure(index=1, error=exc)]

    candidates: list[GeneratedCandidate] = []
    failures: list[CandidateFailure] = []
    with ThreadPoolExecutor(max_workers=count) as executor:
        futures = {
            executor.submit(_generate_candidate, index, api_key, base_url, timeout, backend, prompt, model, size): index
            for index in range(1, count + 1)
        }
        for future in as_completed(futures):
            index = futures[future]
            try:
                candidates.append(future.result())
            except GenerateImageError as exc:
                failures.append(CandidateFailure(index=index, error=exc))
    return sorted(candidates, key=lambda item: item.index), sorted(failures, key=lambda item: item.index)


def _output_path_for_candidate(args: argparse.Namespace, prompt: str, image: GeneratedImage, index: int, count: int) -> Path:
    """根据候选序号生成输出路径，多候选时加后缀防止互相覆盖。"""
    if args.out:
        out_path = _path_with_extension(Path(args.out).expanduser(), image.mime_type)
        if count == 1:
            return out_path
        return out_path.with_name(f"{out_path.stem}-candidate-{index}{out_path.suffix}")

    stem = _safe_stem(args.stem or prompt)
    suffix = _extension_for_mime(image.mime_type)
    filename = f"{stem}{suffix}" if count == 1 else f"{stem}-candidate-{index}{suffix}"
    return Path(args.out_dir).expanduser() / filename


def _write_candidate(args: argparse.Namespace, prompt: str, candidate: GeneratedCandidate, count: int) -> Path:
    """把候选图写入磁盘并避让重名文件，保证每个并发结果都有可检查路径。"""
    out_path = _unique_path(_output_path_for_candidate(args, prompt, candidate.image, candidate.index, count))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(candidate.image.image_bytes)
    return out_path


def _raise_if_no_candidates(failures: list[CandidateFailure]) -> None:
    """所有候选失败时保留鉴权错误语义，否则汇总普通生成错误。"""
    if not failures:
        raise GenerateImageError("no image candidates were generated")
    auth_failure = next((item for item in failures if isinstance(item.error, GenerateImageAuthError)), None)
    if auth_failure is not None:
        raise GenerateImageAuthError(str(auth_failure.error))
    details = "; ".join(f"candidate {item.index}: {item.error}" for item in failures)
    raise GenerateImageError(details)


def main() -> int:
    """CLI 入口：解析参数、处理密钥、生成图片并写入磁盘。"""
    parser = argparse.ArgumentParser(description="Generate images through provider-compatible APIs.")
    parser.add_argument("backend", nargs="?", default="images")
    parser.add_argument("--prompt")
    parser.add_argument("--out", help="Full output path. Extension is inferred from MIME when omitted.")
    parser.add_argument("--out-dir", default=".", help="Directory used when --out is omitted.")
    parser.add_argument("--stem", help="Semantic output basename without extension.")
    parser.add_argument("--model")
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument(
        "--candidates", type=int, default=1,
        help="Number of parallel image candidates to generate. Use 3 for visual selection.",
    )
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--base-url", default=os.environ.get("GENERATE_IMAGE_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-key-file", help="Path to a local file that contains the image API key.")
    parser.add_argument(
        "--save-api-key-stdin", action="store_true",
        help="Read an API key from stdin and save it to the local key file.",
    )
    parser.add_argument(
        "--save-api-key-only", action="store_true",
        help="Save the stdin API key and exit without generating an image.",
    )
    parser.add_argument("--raw-prompt", action="store_true", help="Send --prompt exactly as provided.")
    args = parser.parse_args()

    try:
        backend = BACKEND_ALIASES.get(args.backend.lower(), args.backend.lower())
        if backend not in DEFAULT_MODELS:
            parser.error(f"unknown backend: {args.backend}")
        if args.candidates < 1:
            parser.error("--candidates must be at least 1")
        if args.save_api_key_only and not args.save_api_key_stdin:
            parser.error("--save-api-key-only requires --save-api-key-stdin")
        if not args.prompt and not args.save_api_key_only:
            parser.error("--prompt is required unless --save-api-key-only is set")

        if args.save_api_key_stdin:
            saved_path = _api_key_file_path(args.api_key_file)
            _write_api_key_file(saved_path, sys.stdin.read())
            if args.save_api_key_only:
                print(f"api_key_saved: {saved_path}")
                return 0

        api_key = _read_api_key(args.api_key_file)
        if not api_key:
            raise GenerateImageAuthError(
                "GENERATE_IMAGE_API_KEY, GENERATE_IMAGE_API_KEY_FILE, or cached API key file is required"
            )

        prompt = args.prompt if args.raw_prompt else _clean_prompt(args.prompt)
        model = args.model or DEFAULT_MODELS[backend]
        candidates, failures = _generate_candidates(
            api_key=api_key,
            base_url=args.base_url,
            timeout=args.timeout,
            backend=backend,
            prompt=prompt,
            model=model,
            size=args.size,
            count=args.candidates,
        )
        if not candidates:
            _raise_if_no_candidates(failures)

        for candidate in candidates:
            out_path = _write_candidate(args, prompt, candidate, args.candidates)
            if args.candidates > 1:
                print(f"candidate: {candidate.index}")
            print(f"saved: {out_path}")
            print(f"mime: {candidate.image.mime_type}")
            print(f"bytes: {len(candidate.image.image_bytes)}")
            print(f"response_path: {candidate.image.response_path}")
        for failure in failures:
            print(f"candidate_failed: {failure.index}: {failure.error}", file=sys.stderr)
        if args.candidates > 1:
            print("selection_required: inspect candidates visually and keep the best image")
        return 0
    except GenerateImageAuthError as exc:
        print(f"auth_error: {exc}", file=sys.stderr)
        return 2
    except GenerateImageError as exc:
        print(f"generate_image_error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
