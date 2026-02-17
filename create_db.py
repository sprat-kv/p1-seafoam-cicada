import os
import sys
import asyncio
from importlib import import_module
from dotenv import load_dotenv

load_dotenv()

async def main():
    AsyncPostgresSaver = import_module(
        "langgraph.checkpoint.postgres.aio"
    ).AsyncPostgresSaver
    async with AsyncPostgresSaver.from_conn_string(os.environ["DATABASE_URL"]) as cp:
        await cp.setup()
        print("LangGraph checkpoint tables setup complete.")


def run() -> None:
    """Run async setup with a Windows-compatible, non-deprecated loop strategy."""
    if sys.platform == "win32":
        # Avoid deprecated global loop policy APIs (deprecated in Python 3.14).
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            runner.run(main())
        return

    asyncio.run(main())


if __name__ == "__main__":
    run()