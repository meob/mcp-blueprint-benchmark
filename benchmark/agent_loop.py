import asyncio
import json
import time

import httpx

from .config import MAX_STEPS, NUM_CTX, OLLAMA_NATIVE_URL, OLLAMA_URL, SEED, TEMPERATURE


class ModelError(Exception):
    pass


async def warm_up(model):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        "stream": False,
        "options": {"num_ctx": NUM_CTX, "temperature": TEMPERATURE, "seed": SEED},
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(900.0)) as client:
        resp = await client.post(OLLAMA_NATIVE_URL, json=payload)
    if resp.status_code != 200:
        raise ModelError(f"ollama warm-up http {resp.status_code}: {resp.text[:300]}")


async def chat_once(model, messages, tools):
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "temperature": TEMPERATURE,
        "seed": SEED,
        "stream": False,
        "options": {"num_ctx": NUM_CTX, "temperature": TEMPERATURE, "seed": SEED},
    }
    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=httpx.Timeout(900.0)) as client:
        resp = await client.post(OLLAMA_URL, json=payload)
        elapsed_ms = (time.perf_counter() - start) * 1000
    if resp.status_code != 200:
        raise ModelError(f"ollama http {resp.status_code}: {resp.text[:300]}")
    body = resp.json()
    return body, elapsed_ms


async def run_agent(model, env, user_prompt):
    messages = [{"role": "system", "content": env.system_prompt}, {"role": "user", "content": user_prompt}]
    trace = []
    tokens = {"prompt": 0, "completion": 0, "total": 0}
    total_ms = 0.0
    finish_reason = "max_steps"
    error = None

    for step in range(MAX_STEPS):
        try:
            body, ms = await chat_once(model, messages, env.ollama_tools())
        except Exception as exc:
            error = f"chat error at step {step}: {exc}"
            break
        total_ms += ms
        usage = body.get("usage") or {}
        tokens["prompt"] += usage.get("prompt_tokens", 0)
        tokens["completion"] += usage.get("completion_tokens", 0)
        tokens["total"] += usage.get("total_tokens", 0)

        message = body["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            for idx, tc in enumerate(tool_calls):
                tc.setdefault("id", f"call_{step}_{idx}")
        messages.append(message)

        if not tool_calls:
            finish_reason = body["choices"][0].get("finish_reason") or "stop"
            break

        for tc in tool_calls:
            fn = tc["function"]
            name = fn.get("name")
            raw_args = fn.get("arguments") or "{}"
            try:
                arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError as exc:
                arguments = {}
                error = f"tool argument parse error on {name}: {exc}"
            t0 = time.perf_counter()
            try:
                result_text = await env.call_tool(name, arguments)
                err = None
            except Exception as exc:
                result_text = str(exc)
                err = f"{type(exc).__name__}: {exc}"
            call_ms = (time.perf_counter() - t0) * 1000
            total_ms += call_ms
            trace.append({
                "step": step,
                "tool": name,
                "arguments": arguments,
                "result_preview": result_text[:500],
                "duration_ms": round(call_ms, 1),
                "error": err,
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": result_text,
            })

    final_answer = ""
    for m in reversed(messages):
        if m.get("role") == "assistant" and m.get("content"):
            final_answer = m["content"]
            break

    return {
        "messages": messages,
        "trace": trace,
        "tokens": tokens,
        "latency_ms": round(total_ms, 1),
        "steps": step + 1,
        "finish_reason": finish_reason,
        "error": error,
        "final_answer": final_answer,
    }
