"""API dan entrypoint prediksi untuk modul serving Wikiwisata."""

from __future__ import annotations

import argparse
import json
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml

from wikiwisata.experiments.config import load_config
from wikiwisata.experiments.parse import parse_answer_with_normalization
from wikiwisata.experiments.prompt_manager import get_entry, read_prompt
from wikiwisata.experiments.schema import validate
from wikiwisata.serving.fallback import (
    build_fallback_response,
    is_personal_pii_request,
    is_unsafe_guarantee_request,
    sanitize_output,
)
from wikiwisata.serving.tracer import DEFAULT_TRACE_LOG_PATH, RequestTracer
from wikiwisata.serving.ui_app import render_ui_html

REPO_ROOT = Path(__file__).resolve().parents[3]
API_CONFIG_PATH = REPO_ROOT / "configs" / "serving" / "api.yaml"
PROMPTS_DIR = REPO_ROOT / "prompts"
SCHEMA_PATH = REPO_ROOT / "schemas" / "answer.schema.json"

CONFIG_FILES: dict[str, Path] = {
    "B0": REPO_ROOT / "configs" / "experiments" / "b0_baseline.yaml",
    "B1": REPO_ROOT / "configs" / "experiments" / "b1_structured_abstain.yaml",
    "B2": REPO_ROOT / "configs" / "experiments" / "b2_retrieval_variant.yaml",
    "B3": REPO_ROOT / "configs" / "experiments" / "b3_metadata_filtered.yaml",
    "B4": REPO_ROOT / "configs" / "experiments" / "b4_planner_verifier.yaml",
    "B5": REPO_ROOT / "configs" / "experiments" / "b5_lora_qlora.yaml",
    "B6": REPO_ROOT / "configs" / "experiments" / "b6_agentic_tool.yaml",
}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_api_config(path: str | Path = API_CONFIG_PATH) -> dict[str, Any]:
    """Muat konfigurasi serving dari configs/serving/api.yaml."""
    cfg_path = Path(path)
    if not cfg_path.exists():
        return {
            "host": "127.0.0.1",
            "port": 8000,
            "default_config": "B4",
            "timeout_seconds": 120,
            "max_tool_calls": 4,
        }
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}


def _stage_unready_reason(config: dict[str, Any], config_id: str) -> str | None:
    """Periksa apakah stage pada config sudah siap dijalankan tanpa mocking."""
    if config.get("retrieval", {}).get("enabled"):
        # Saat ini pipeline.py belum menghubungkan Retriever.search() untuk B2-B6.
        from wikiwisata.experiments import pipeline as exp_pipeline

        placeholder = exp_pipeline._passages_text(config)
        if "belum diimplementasikan" in placeholder:
            return f"retrieval untuk konfigurasi {config_id} belum aktif di pipeline eksperimen"

    if config.get("planner", {}).get("enabled"):
        try:
            from wikiwisata.experiments.stages.planner import plan  # noqa: F401
        except Exception as exc:
            return f"planner belum tersedia: {exc}"

    if config.get("adapter", {}).get("enabled"):
        adapter_path = REPO_ROOT / str(
            config.get("adapter", {}).get("path", "artifacts/ian/adapters/b5")
        )
        if not (adapter_path / "adapter_config.json").exists():
            return f"adapter LoRA/QLoRA untuk {config_id} belum tersedia di {adapter_path}"

    return None


def _finalize_and_trace(
    *,
    response: dict[str, Any],
    tracer: RequestTracer,
    force_personal_redaction: bool,
    fallback_used: bool,
    fallback_reason: str | None,
    prompt_tokens: int = 0,
    output_tokens: int = 0,
    error: str | None = None,
) -> dict[str, Any]:
    sanitized, pii_redacted = sanitize_output(
        response, force_personal_contact_redaction=force_personal_redaction
    )
    meta = sanitized.setdefault("meta", {})
    meta["request_id"] = tracer.request_id

    record = tracer.finish(
        verdict=sanitized["verdict"],
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        pii_redacted=pii_redacted,
        prompt_tokens=prompt_tokens,
        output_tokens=output_tokens,
        error=error,
    )
    meta["latency_ms"] = record.total_latency_ms
    meta["pii_redacted"] = pii_redacted

    validate(sanitized, SCHEMA_PATH)
    return sanitized


def predict(
    question: str,
    travel_date: str,
    config_id: str | None = None,
    *,
    source: str = "api",
    trace_log_path: str | Path = DEFAULT_TRACE_LOG_PATH,
    force_fallback_reason: str | None = None,
) -> dict[str, Any]:
    """Jalankan satu request prediksi dan kembalikan JSON sesuai answer.schema.json."""
    api_cfg = load_api_config()
    selected_id = (config_id or str(api_cfg.get("default_config", "B4"))).upper()
    cleaned_question = (question or "").strip()
    cleaned_date = (travel_date or "").strip()

    tracer = RequestTracer(
        config_id=selected_id,
        question=cleaned_question,
        travel_date=cleaned_date,
        source=source,
        log_path=trace_log_path,
    )

    if not cleaned_question:
        resp = build_fallback_response(
            reason="Pertanyaan tidak boleh kosong.",
            config_id=selected_id,
        )
        return _finalize_and_trace(
            response=resp,
            tracer=tracer,
            force_personal_redaction=False,
            fallback_used=True,
            fallback_reason="empty_question",
        )

    if not _DATE_RE.match(cleaned_date):
        resp = build_fallback_response(
            reason="Format tanggal perjalanan harus YYYY-MM-DD.",
            config_id=selected_id,
        )
        return _finalize_and_trace(
            response=resp,
            tracer=tracer,
            force_personal_redaction=False,
            fallback_used=True,
            fallback_reason="invalid_travel_date",
        )

    if selected_id not in CONFIG_FILES:
        resp = build_fallback_response(
            reason=f"Konfigurasi '{selected_id}' tidak dikenal.",
            config_id=selected_id,
        )
        return _finalize_and_trace(
            response=resp,
            tracer=tracer,
            force_personal_redaction=False,
            fallback_used=True,
            fallback_reason="unknown_config",
        )

    # Guardrail PII: tolak eksplisit permintaan data pribadi/kontak personal seseorang
    if is_personal_pii_request(cleaned_question):
        resp = build_fallback_response(
            reason="Permintaan ditolak untuk melindungi data pribadi (PII) dan kontak personal.",
            config_id=selected_id,
            prompt_id="guardrail_pii",
            user_message=(
                "Maaf, saya tidak dapat memberikan data pribadi (seperti NIK, KTP, "
                "atau kontak pribadi individu) demi perlindungan privasi."
            ),
        )
        return _finalize_and_trace(
            response=resp,
            tracer=tracer,
            force_personal_redaction=True,
            fallback_used=True,
            fallback_reason="pii_guardrail",
        )

    # Guardrail keselamatan: tolak memberi jaminan keselamatan mutlak / saran medis / jalur ilegal
    if is_unsafe_guarantee_request(cleaned_question):
        resp = build_fallback_response(
            reason="Sistem tidak dapat memberikan jaminan keselamatan mutlak, saran medis darurat, atau jalur ilegal.",
            config_id=selected_id,
            prompt_id="guardrail_safety",
            user_message=(
                "Maaf, saya tidak dapat memberikan jaminan keselamatan atau saran "
                "aktivitas berisiko/medis darurat. Silakan ikuti arahan otoritas resmi setempat."
            ),
        )
        return _finalize_and_trace(
            response=resp,
            tracer=tracer,
            force_personal_redaction=False,
            fallback_used=True,
            fallback_reason="safety_guardrail",
        )

    if force_fallback_reason:
        resp = build_fallback_response(
            reason=force_fallback_reason,
            config_id=selected_id,
        )
        return _finalize_and_trace(
            response=resp,
            tracer=tracer,
            force_personal_redaction=False,
            fallback_used=True,
            fallback_reason=force_fallback_reason,
        )

    exp_config = load_config(CONFIG_FILES[selected_id])
    unready_reason = _stage_unready_reason(exp_config, selected_id)
    if unready_reason is not None:
        resp = build_fallback_response(
            reason=f"Mode terbatas aktif: {unready_reason}.",
            config_id=selected_id,
        )
        return _finalize_and_trace(
            response=resp,
            tracer=tracer,
            force_personal_redaction=False,
            fallback_used=True,
            fallback_reason=unready_reason,
        )

    # Eksekusi model nyata (B0/B1 yang sudah siap di repo)
    prompt_tokens = 0
    output_tokens = 0
    try:
        from wikiwisata.experiments.generate import generate
        from wikiwisata.experiments.pipeline import fill_template

        prompt_id = str(exp_config["prompt"])
        template = read_prompt(PROMPTS_DIR, prompt_id)
        entry = get_entry(PROMPTS_DIR, prompt_id)
        repair_template = read_prompt(PROMPTS_DIR, "format_repair")

        prompt = fill_template(
            template,
            {
                "question": cleaned_question,
                "travel_date": cleaned_date,
                "passages": "(tidak ada passage)",
            },
        )

        t_gen = tracer.start_stage()
        generation = generate(prompt, exp_config)
        tracer.end_stage("generation_ms", t_gen)
        prompt_tokens += generation.prompt_tokens
        output_tokens += generation.output_tokens

        t_parse = tracer.start_stage()
        try:
            parsed, _ = parse_answer_with_normalization(generation.text, SCHEMA_PATH)
        except Exception as exc:
            repair_prompt = fill_template(
                repair_template,
                {"error": f"{type(exc).__name__}: {exc}", "raw_output": generation.text},
            )
            repaired = generate(repair_prompt, exp_config)
            prompt_tokens += repaired.prompt_tokens
            output_tokens += repaired.output_tokens
            parsed, _ = parse_answer_with_normalization(repaired.text, SCHEMA_PATH)
        tracer.end_stage("parse_ms", t_parse)

        parsed["meta"]["config_id"] = selected_id
        parsed["meta"]["prompt_id"] = prompt_id
        parsed["meta"]["prompt_version"] = entry["version"]
        parsed["meta"]["fallback"] = False

        return _finalize_and_trace(
            response=parsed,
            tracer=tracer,
            force_personal_redaction=False,
            fallback_used=False,
            fallback_reason=None,
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
        )
    except Exception as exc:
        err_msg = f"{type(exc).__name__}: {exc}"
        short_err = f"{type(exc).__name__}: {str(exc).splitlines()[0]}"
        resp = build_fallback_response(
            reason=f"Inferensi gagal atau output tidak valid ({short_err}).",
            config_id=selected_id,
            user_message=(
                "Maaf, output model belum memenuhi format jawaban terverifikasi "
                f"({short_err})."
            ),
        )
        return _finalize_and_trace(
            response=resp,
            tracer=tracer,
            force_personal_redaction=False,
            fallback_used=True,
            fallback_reason="inference_or_parse_error",
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
            error=err_msg,
        )


class WikiwisataHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler standar Python untuk endpoint /, /health, dan /predict."""

    trace_log_path: Path = DEFAULT_TRACE_LOG_PATH

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status: int, html_text: str) -> None:
        body = html_text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            cfg = load_api_config()
            self._send_json(
                HTTPStatus.OK,
                {"status": "ok", "default_config": cfg.get("default_config", "B4")},
            )
            return
        if self.path == "/":
            cfg = load_api_config()
            self._send_html(
                HTTPStatus.OK,
                render_ui_html(str(cfg.get("default_config", "B4"))),
            )
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Endpoint tidak ditemukan."})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/predict":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Endpoint tidak ditemukan."})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"JSON tidak valid: {exc}"})
            return

        if not isinstance(payload, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Payload harus berupa objek JSON."})
            return

        result = predict(
            question=str(payload.get("question", "")),
            travel_date=str(payload.get("travel_date", "")),
            config_id=payload.get("config_id"),
            source=str(payload.get("source", "api")),
            trace_log_path=self.trace_log_path,
        )
        self._send_json(HTTPStatus.OK, result)


def serve(
    host: str | None = None,
    port: int | None = None,
    trace_log_path: str | Path = DEFAULT_TRACE_LOG_PATH,
) -> None:
    """Jalankan HTTP server Wikiwisata."""
    cfg = load_api_config()
    bind_host = host or str(cfg.get("host", "127.0.0.1"))
    bind_port = int(port if port is not None else cfg.get("port", 8000))

    class _Handler(WikiwisataHTTPHandler):
        pass

    _Handler.trace_log_path = Path(trace_log_path)
    server = ThreadingHTTPServer((bind_host, bind_port), _Handler)
    print(f"Wikiwisata serving aktif di http://{bind_host}:{bind_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Jalankan Wikiwisata API & UI server.")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args(argv)
    serve(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
