from sqlalchemy import inspect, text

from db.database import engine, AsyncSessionLocal
from schemas.schema_model import SchemaResponse, QueryResponse, WriteResponse


READ_ONLY_KEYWORDS = {
    "SELECT",
    "WITH",
    "EXPLAIN",
}

WRITE_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "CREATE",
    "DROP",
    "TRUNCATE",
}

async def read_db_schema() -> SchemaResponse:
    async with engine.connect() as conn:

        def _inspect(sync_conn):
            inspector = inspect(sync_conn)

            schema = {}

            for table in inspector.get_table_names():

                columns = inspector.get_columns(table)

                schema[table] = {
                    "columns": [
                        {
                            "name": col["name"],
                            "type": str(col["type"]),
                            "nullable": col["nullable"],
                        }
                        for col in columns
                    ]
                }

            return schema

        schema = await conn.run_sync(_inspect)

        return SchemaResponse(
            tables=schema
        )
        
async def read_sql(
    sql: str,
) -> QueryResponse:

    first_word = sql.strip().split()[0].upper()

    if first_word not in READ_ONLY_KEYWORDS:
        raise ValueError(
            f"Only read queries allowed. Got: {first_word}"
        )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(sql)
        )

        rows = [
            dict(row)
            for row in result.mappings()
        ]

        return QueryResponse(
            rows=rows,
            row_count=len(rows),
        )
        
async def write_sql(
    sql: str,
) -> WriteResponse:

    first_word = sql.strip().split()[0].upper()

    if first_word not in WRITE_KEYWORDS:
        raise ValueError(
            f"Not a write query: {first_word}"
        )

    async with AsyncSessionLocal() as session:
        print("="*50)
        print("SQL QUERY : " + sql)
        print("="*50)
        result = await session.execute(
            text(sql)
        )

        await session.commit()

        return WriteResponse(
            row_count=result.rowcount or 0,  # type: ignore
            success=True,
        )