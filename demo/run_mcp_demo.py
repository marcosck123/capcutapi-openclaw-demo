#!/usr/bin/env python3
"""Run a minimal end-to-end MCP demo and persist the generated draft locally."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "demo" / "output"


def send_request(process: subprocess.Popen[str], payload: dict) -> dict:
    process.stdin.write(json.dumps(payload) + "\n")
    process.stdin.flush()

    line = process.stdout.readline()
    if not line.strip():
        raise RuntimeError(f"Empty response for method {payload.get('method')}")
    return json.loads(line)


def call_tool(process: subprocess.Popen[str], request_id: int, name: str, arguments: dict) -> dict:
    response = send_request(
        process,
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )
    content = response["result"]["content"][0]["text"]
    parsed = json.loads(content)
    if not parsed.get("success"):
        raise RuntimeError(f"{name} failed: {parsed}")
    return parsed


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    stderr_log = OUTPUT_ROOT / "mcp-demo.stderr.log"
    stderr_handle = stderr_log.open("w", encoding="utf-8")

    process = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "mcp_server.py")],
        cwd=REPO_ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=stderr_handle,
        text=True,
        bufsize=1,
    )

    try:
        print("Starting CapCut MCP demo")

        initialize_response = send_request(
            process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}, "resources": {}},
                    "clientInfo": {
                        "name": "openclaw-demo",
                        "version": "1.0.0",
                    },
                },
            },
        )
        server_info = initialize_response["result"]["serverInfo"]
        print(f"Connected to MCP server {server_info['name']} v{server_info['version']}")

        process.stdin.write(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {},
                }
            )
            + "\n"
        )
        process.stdin.flush()

        tools_response = send_request(
            process,
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        tools = tools_response["result"]["tools"]
        print(f"Discovered {len(tools)} tools")

        create_result = call_tool(
            process,
            3,
            "create_draft",
            {"width": 1080, "height": 1920},
        )
        draft_id = create_result["result"]["draft_id"]
        print(f"Created draft {draft_id}")

        text_result = call_tool(
            process,
            4,
            "add_text",
            {
                "draft_id": draft_id,
                "text": "OpenClaw + CapCut",
                "start": 0,
                "end": 4,
                "font_size": 10,
                "font_color": "#F3F4F6",
                "background_color": "#111827",
                "background_alpha": 0.82,
                "background_round_radius": 0.18,
                "shadow_enabled": True,
                "shadow_color": "#000000",
                "shadow_alpha": 0.85,
                "text_styles": [
                    {
                        "start": 0,
                        "end": 8,
                        "font_color": "#22C55E",
                        "bold": True,
                    },
                    {
                        "start": 11,
                        "end": 17,
                        "font_color": "#60A5FA",
                        "bold": True,
                    },
                ],
            },
        )
        print(
            "Added styled text "
            f"(shadow={text_result['features_used']['shadow']}, "
            f"background={text_result['features_used']['background']}, "
            f"multi_style={text_result['features_used']['multi_style']})"
        )

        draft_path = OUTPUT_ROOT / draft_id
        root_draft_path = REPO_ROOT / draft_id
        if draft_path.exists():
            shutil.rmtree(draft_path)
        if root_draft_path.exists():
            shutil.rmtree(root_draft_path)

        save_result = call_tool(
            process,
            5,
            "save_draft",
            {"draft_id": draft_id, "draft_folder": str(OUTPUT_ROOT)},
        )
        if root_draft_path.exists():
            shutil.move(str(root_draft_path), str(draft_path))
        print(f"Saved draft into {draft_path}")

        draft_info = draft_path / "draft_info.json"
        if not draft_info.exists():
            raise RuntimeError(f"Expected draft file missing: {draft_info}")

        asset_count = len(list((draft_path / "assets").rglob("*")))
        print(f"Verified generated files: draft_info.json plus {asset_count} asset paths")
        print(f"Remote draft URL: {save_result['result']['draft_url']}")
        print("Demo completed successfully")
        return 0
    except Exception as exc:
        print(f"Demo failed: {exc}")
        stderr_handle.flush()
        stderr = stderr_log.read_text(encoding="utf-8").strip()
        if stderr:
            print("Server stderr:")
            print(stderr)
        return 1
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        stderr_handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
