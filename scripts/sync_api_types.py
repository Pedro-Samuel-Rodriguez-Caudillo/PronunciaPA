#!/usr/bin/env python3
"""Script to synchronize TypeScript types from OpenAPI schema.

This script:
1. Starts the FastAPI server temporarily
2. Fetches the OpenAPI schema from /openapi.json
3. Generates TypeScript types using openapi-typescript
4. Updates frontend/src/types/api.ts

Usage:
    python scripts/sync_api_types.py
    
    # Or with custom server URL
    python scripts/sync_api_types.py --url http://localhost:8001
"""
import argparse
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import httpx


SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
API_TYPES_FILE = FRONTEND_DIR / "src" / "types" / "api.ts"


async def wait_for_server(url: str, timeout: int = 30) -> bool:
    """Wait for server to be ready."""
    start = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start < timeout:
            try:
                response = await client.get(f"{url}/health", timeout=2.0)
                if response.status_code == 200:
                    return True
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
            await asyncio.sleep(0.5)
    return False


async def fetch_openapi_schema(url: str) -> dict:
    """Fetch OpenAPI schema from server."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{url}/openapi.json", timeout=10.0)
        response.raise_for_status()
        return response.json()


def generate_typescript_types(schema: dict, output_path: Path) -> None:
    """Generate TypeScript types from OpenAPI schema using openapi-typescript."""
    # Save schema temporarily
    temp_schema = PROJECT_ROOT / ".openapi.temp.json"
    temp_schema.write_text(json.dumps(schema, indent=2))
    
    try:
        # Check if openapi-typescript is installed
        result = subprocess.run(
            ["npx", "openapi-typescript", "--version"],
            cwd=FRONTEND_DIR,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            print("⚠️  openapi-typescript not found, installing...")
            subprocess.run(
                ["npm", "install", "--save-dev", "openapi-typescript"],
                cwd=FRONTEND_DIR,
                check=True,
            )
        
        # Generate types
        print(f"🔧 Generating TypeScript types to {output_path}...")
        result = subprocess.run(
            [
                "npx",
                "openapi-typescript",
                str(temp_schema),
                "--output",
                str(output_path),
                "--export-type",
            ],
            cwd=FRONTEND_DIR,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            print(f"❌ Error generating types:\n{result.stderr}")
            sys.exit(1)
        
        print(f"✅ TypeScript types generated successfully")
        
    finally:
        # Cleanup temp file
        if temp_schema.exists():
            temp_schema.unlink()


async def main(server_url: Optional[str] = None, start_server: bool = True) -> None:
    """Main synchronization workflow."""
    url = server_url or "http://localhost:8000"
    server_process = None
    
    try:
        if start_server:
            print(f"🚀 Starting server at {url}...")
            server_process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "ipa_server.main:get_app", "--factory", "--port", "8000"],
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            print("⏳ Waiting for server to be ready...")
            if not await wait_for_server(url):
                print("❌ Server failed to start within timeout")
                sys.exit(1)
            print("✅ Server is ready")
        
        # Fetch schema
        print(f"📥 Fetching OpenAPI schema from {url}/openapi.json...")
        schema = await fetch_openapi_schema(url)
        print(f"✅ Schema fetched ({len(schema.get('paths', {}))} endpoints)")
        
        # Generate TypeScript types
        generate_typescript_types(schema, API_TYPES_FILE)
        
        print(f"\n✨ Type synchronization complete!")
        print(f"📄 Updated: {API_TYPES_FILE.relative_to(PROJECT_ROOT)}")
        
    finally:
        if server_process:
            print("\n🛑 Stopping server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync TypeScript types from OpenAPI schema")
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Server URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--no-start-server",
        action="store_true",
        help="Don't start server, use existing one",
    )
    
    args = parser.parse_args()
    
    asyncio.run(main(
        server_url=args.url,
        start_server=not args.no_start_server,
    ))
