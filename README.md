# Personal Knowledge Pool

Personal Knowledge Pool is a small AI-assisted knowledge base project that helps you collect, store, and retrieve information from the web.

## What it does

- Searches the web for relevant articles
- Scrapes and processes article content
- Saves selected results into a local database
- Lets you ask an agent to retrieve and reason over stored knowledge

## Project layout

- agents/: LangGraph agent workflow and nodes
- MCP/: MCP server and database-related services
- searxng/: local search engine setup for web search

## Setup

### Docker Compose (recommended)

Prerequisites:
- Docker and Docker Compose installed
- A `.env` file at the project root with the required environment variables, especially `DATABASE_URL`

From the project root, run:

```bash
docker compose up --build
```

This starts the following services:
- `searxng` on http://localhost:8888
- `mcp-server` on http://localhost:8080
- `langgraph-agent` as an interactive container for running the agent workflow

To run the example workflow from the agent container:

```bash
docker compose exec -it langgraph-agent python graph.py
```

You can also open a shell in the container first:

```bash
docker compose exec -it langgraph-agent bash
```

## Database migrations with Alembic

The MCP service uses Alembic to manage PostgreSQL schema changes. Migration scripts live in [MCP/alembic](MCP/alembic) and the configuration is in [MCP/alembic.ini](MCP/alembic.ini).

### Production-style workflow with Docker Compose

For production-like deployments, run migrations from the running MCP container before or during a controlled deploy.

1. Make sure the container has access to the correct database via the `DATABASE_URL` value in your `.env` file.
2. Take a database backup using your usual production backup process.
3. Apply the latest migrations:

```bash
docker compose exec -T mcp-server alembic upgrade head
```

4. Verify the current revision:

```bash
docker compose exec -T mcp-server alembic current
```

5. If you need to create a new migration after changing SQLAlchemy models:

```bash
docker compose exec -T mcp-server alembic revision --autogenerate -m "describe your change"
```

6. If you ever need to roll back a migration, use:

```bash
docker compose exec -T mcp-server alembic downgrade -1
```

### Local/manual Alembic usage

If you are running the MCP app outside Docker, use the same commands from the `MCP` directory:

```bash
cd MCP
alembic upgrade head
alembic current
```

### Manual setup (alternative)

#### 1. Start the web search service

From the searxng folder, run:

```bash
docker run --name searxng -d \
    -p 8888:8080 \
    -v "./config/:/etc/searxng/" \
    -v "./data/:/var/cache/searxng/" \
    docker.io/searxng/searxng:latest
```

#### 2. Start the MCP server

```bash
cd MCP
python server.py
```

#### 3. Run the agent workflow

You can trigger the example workflow from the agent entry point:

```bash
python agents/graph.py
```

The example query in agents/graph.py asks the agent to look for articles, scrape them, and save the best results to the database.

## Notes

- The project currently uses a local database and local search setup.
- You can modify the message in agents/graph.py to ask for different topics or article selections.

## Future improvements

- Store checkpoints in PostgreSQL for better persistence and queryability
- Build a Karpathy-style knowledge base that consolidates all of the user's data
- Add user personalization so the system can tailor searches, summaries, and recommendations to the individual user

## Prerequisites: PostgreSQL and environment variables

Before running the MCP server you must have PostgreSQL (psql) available and the required environment variables set.

1. Install PostgreSQL (example for Ubuntu/Debian):

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
```

2. Start PostgreSQL and create a database and user (example):

```bash
sudo systemctl start postgresql
sudo -u postgres psql
-- In the psql prompt:
CREATE DATABASE articles;
CREATE USER rohit WITH ENCRYPTED PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE articles TO rohit;
\q
```

3. If you hit PostgreSQL authentication errors such as `no pg_hba.conf entry...`, inspect the client authentication config from psql:

```bash
SHOW hba_file;
sudo vim /etc/postgresql/<version>/main/pg_hba.conf
```

Add a rule like this:

```conf
host    all    all    172.18.0.0/16    scram-sha-256
```

Then restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

4. Set environment variables. You can create a `.env` file at the project root (not committed) using the format in `.env.example`.

Example `.env` values:

```
DATABASE_URL=postgresql+asyncpg://rohit:yourpassword@host.docker.internal:5432/articles
NVIDIA_API_KEY=nvapi-REPLACE_WITH_YOUR_KEY
```

If PostgreSQL is running locally and you need the app (especially from Docker) to connect to it, use `host.docker.internal` instead of `localhost` in the URL. Also make sure your PostgreSQL configuration allows remote connections by setting `listen_addresses` to `'*'`.

4. Run the server from the `MCP` folder:

```bash
cd MCP
python server.py
```

Notes:
- Replace `rohit:yourpassword` with the DB user and password you created.
- If you use a different API provider, set the corresponding API key environment variable instead of `NVIDIA_API_KEY`.
