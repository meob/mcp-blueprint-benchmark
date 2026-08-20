import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .config import C_DESC_FIXES, BLUEPRINT_BIN, REPO, ROOT, SAKILA_DSN


def _to_ollama_tool(tool, desc_fix=None):
    description = tool.description + desc_fix if desc_fix else tool.description
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": description,
            "parameters": tool.inputSchema,
        },
    }


def _result_text(result):
    return "\n".join(
        block.text for block in result.content if getattr(block, "type", "") == "text"
    )


class AgentEnv:
    approach = "?"
    desc_fixes = {}

    def __init__(self):
        self.tools = []

    def ollama_tools(self):
        return [_to_ollama_tool(t, self.desc_fixes.get(t.name)) for t in self.tools]

    async def call_tool(self, name, arguments):
        raise NotImplementedError


class ApproachBEnv(AgentEnv):
    """Approach B: verticalized sakila pack (domain tools)."""
    approach = "B"
    desc_fixes = {}

    async def __aenter__(self):
        params = StdioServerParameters(
            command=BLUEPRINT_BIN,
            args=["serve", "--config", str(REPO / "config"), "--transport", "stdio"],
            cwd=str(REPO),
            env={
                **os.environ,
                "MCP_BLUEPRINT_DATABASE_ENGINE": "postgresql",
                "MCP_BLUEPRINT_DATABASE_URL": SAKILA_DSN,
                "MCP_BLUEPRINT_SERVER_PACKS": "sakila",
            },
        )
        self._stack = stdio_client(params)
        self._read, self._write = await self._stack.__aenter__()
        self._session = await ClientSession(self._read, self._write).__aenter__()
        await self._session.initialize()
        self.tools = (await self._session.list_tools()).tools
        return self

    async def __aexit__(self, *exc):
        for closer in (self._session, self._stack):
            try:
                await closer.__aexit__(*exc)
            except BaseException:
                pass

    async def call_tool(self, name, arguments):
        result = await self._session.call_tool(name, arguments=arguments)
        if result.isError:
            raise ValueError(_result_text(result) or "tool error")
        return _result_text(result)


class ApproachCEnv(AgentEnv):
    """Approach C: generic pack with anti-pattern tools."""
    approach = "C"
    desc_fixes = C_DESC_FIXES

    async def __aenter__(self):
        params = StdioServerParameters(
            command=BLUEPRINT_BIN,
            args=[
                "serve",
                "--config",
                str(ROOT / "config" / "sakila_baseline.yaml"),
                "--transport",
                "stdio",
            ],
            cwd=str(ROOT),
            env={
                **os.environ,
                "MCP_BLUEPRINT_DATABASE_ENGINE": "postgresql",
                "MCP_BLUEPRINT_DATABASE_URL": SAKILA_DSN,
                "MCP_BLUEPRINT_SERVER_PACKS": "sakila",
            },
        )
        self._stack = stdio_client(params)
        self._read, self._write = await self._stack.__aenter__()
        self._session = await ClientSession(self._read, self._write).__aenter__()
        await self._session.initialize()
        self.tools = (await self._session.list_tools()).tools
        return self

    async def __aexit__(self, *exc):
        for closer in (self._session, self._stack):
            try:
                await closer.__aexit__(*exc)
            except BaseException:
                pass

    async def call_tool(self, name, arguments):
        result = await self._session.call_tool(name, arguments=arguments)
        if result.isError:
            raise ValueError(_result_text(result) or "tool error")
        return _result_text(result)


class ApproachAEnv(AgentEnv):
    """Approach A: raw SQL via execute_sql tool."""
    approach = "A"

    async def __aenter__(self):
        params = StdioServerParameters(
            command=str(ROOT / ".venv" / "bin" / "python"),
            args=["-m", "benchmark.execute_sql_server"],
            cwd=str(ROOT),
            env={**os.environ, "SAKILA_DSN": SAKILA_DSN},
        )
        self._stack = stdio_client(params)
        self._read, self._write = await self._stack.__aenter__()
        self._session = await ClientSession(self._read, self._write).__aenter__()
        await self._session.initialize()
        self.tools = (await self._session.list_tools()).tools
        return self

    async def __aexit__(self, *exc):
        for closer in (self._session, self._stack):
            try:
                await closer.__aexit__(*exc)
            except BaseException:
                pass

    async def call_tool(self, name, arguments):
        result = await self._session.call_tool(name, arguments=arguments)
        if result.isError:
            raise ValueError(_result_text(result) or "tool error")
        return _result_text(result)
