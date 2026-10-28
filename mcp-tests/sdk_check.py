"""Kontrola oficiálním klientem MCP (Python SDK) proti lokálnímu serveru: python mcp-tests/sdk_check.py"""
import asyncio
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8790/mcp"


async def main():
    async with streamable_http_client(URL) as (read, write, *_):
        async with ClientSession(read, write) as s:
            init = await s.initialize()
            print("server:", init.server_info.name, init.protocol_version)
            tools = (await s.list_tools()).tools
            print("nástroje:", ", ".join(t.name for t in tools))
            print("prompty:", ", ".join(p.name for p in (await s.list_prompts()).prompts))
            r = await s.call_tool("jednani", {"obec": "strelice", "id": "posledni"})
            print("jednani posledni:", r.is_error, r.structured_content["id"], len(r.structured_content["usneseni"]), "usnesení")
            r = await s.call_tool("hledat", {"dotaz": "skatepark"})
            print("hledat skatepark:", r.structured_content["celkem"], "výsledků")
            r = await s.call_tool("rozpocet", {"obec": "nikde"})
            print("špatná obec → isError:", r.is_error)


sys.stdout.reconfigure(encoding="utf-8")
asyncio.run(main())
