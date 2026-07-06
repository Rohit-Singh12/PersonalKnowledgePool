from services.psql_service import read_db_schema, SchemaResponse, WriteResponse, write_sql, QueryResponse, read_sql

async def register(mcp):
    
    @mcp.tool
    async def read_schema() -> SchemaResponse:
        """
            Returns the database schema.
            
            Use this to fetch database schema, when user asks to fetch or write some data from the database.
            This will give you schema that is present so that you have better idea of what to fetch and write.
        """
        return await read_db_schema()

    @mcp.tool
    async def write_sql_query(sql: str) -> WriteResponse:
        """
            Execute write SQL query. Make sure you have the schema of the database.
            Call read_schema tool before this to ensure you are making correct query.
            Args:
                sql (str): PSQL query to be executed
        """
        return await write_sql(sql)

    @mcp.tool
    async def read_sql_queury(sql: str) -> QueryResponse:
        """
            Execute Read related SQL quries. Make sure you have the schema of the database.
            Call read_schema tool before this to ensure you are making correct query.
            
            Args:
                sql (str): PSQL read query to be executed
        """
        return await read_sql(sql)