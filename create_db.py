import os
import sys
import asyncio
from importlib import import_module
from dotenv import load_dotenv
import psycopg

load_dotenv()

async def main():
    AsyncPostgresSaver = import_module(
        "langgraph.checkpoint.postgres.aio"
    ).AsyncPostgresSaver
    async with AsyncPostgresSaver.from_conn_string(os.environ["DATABASE_URL"]) as cp:
        await cp.setup()
        print("LangGraph checkpoint tables setup complete.")

    ddl = """
    CREATE TABLE IF NOT EXISTS customer_case_history (
        id BIGSERIAL PRIMARY KEY,
        thread_id TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL CHECK (status IN ('active', 'in_review', 'closed')),
        customer_name TEXT,
        order_id TEXT,
        graph_state_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        conversation_json JSONB NOT NULL DEFAULT '[]'::jsonb,
        decision_maker_action TEXT,
        hitl_action TEXT,
        final_action TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_customer_case_history_status_updated_at
    ON customer_case_history (status, updated_at DESC);
    """

    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as conn:
        async with conn.cursor() as cur:
            await cur.execute(ddl)
        await conn.commit()
    print("customer_case_history table setup complete.")


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