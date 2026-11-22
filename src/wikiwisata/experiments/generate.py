"""Pemanggilan model generator."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

_MODEL_CACHE: dict[tuple[str, str], tuple[Any, Any]] = {}


@dataclass(frozen=True)
class Generation:
    text: str
    prompt_tokens: int
    output_tokens: int
    latency_ms: float


def load_model(config: dict[str, Any]):
    """Muat tokenizer dan model sekali per proses."""
    model_id = str(config["model"]["id"])
    revision = str(config["model"].get("revision") or "main")
    key = (model_id, revision)

    if key not in _MODEL_CACHE:
        tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            revision=revision,
            dtype=torch.bfloat16,
            device_map="auto",
        )
        model.eval()
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token_id = tokenizer.eos_token_id
        _MODEL_CACHE[key] = (tokenizer, model)

    return _MODEL_CACHE[key]


def generate(
    prompt: str,
    config: dict[str, Any],
    seed: int | None = None,
) -> Generation:
    """Hasilkan teks dari prompt dan catat token serta latensi."""
    tokenizer, model = load_model(config)

    messages = [{"role": "user", "content": prompt}]
    chat_prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(chat_prompt, return_tensors="pt").to(model.device)
    prompt_tokens = int(inputs["input_ids"].shape[1])

    decoding = config.get("decoding", {})
    temperature = float(decoding.get("temperature", 0.2))
    top_p = float(decoding.get("top_p", 0.95))
    max_new_tokens = int(decoding.get("max_new_tokens", 512))
    do_sample = temperature > 0

    generate_kwargs: dict[str, Any] = {
        "max_new_tokens": max_new_tokens,
        "pad_token_id": tokenizer.pad_token_id,
        "do_sample": do_sample,
    }
    if do_sample:
        generate_kwargs["temperature"] = temperature
        generate_kwargs["top_p"] = top_p

    seed_value = int(seed if seed is not None else config.get("seed", 13))
    torch.manual_seed(seed_value)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed_value)

    started = time.perf_counter()
    with torch.inference_mode():
        output = model.generate(**inputs, **generate_kwargs)
    latency_ms = (time.perf_counter() - started) * 1000

    generated = output[0][prompt_tokens:]
    text = tokenizer.decode(generated, skip_special_tokens=True).strip()

    return Generation(
        text=text,
        prompt_tokens=prompt_tokens,
        output_tokens=int(generated.shape[0]),
        latency_ms=round(latency_ms, 1),
    )
