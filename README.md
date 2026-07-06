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

### 1. Start the web search service

From the searxng folder, run:

```bash
docker run --name searxng -d \
    -p 8888:8080 \
    -v "./config/:/etc/searxng/" \
    -v "./data/:/var/cache/searxng/" \
    docker.io/searxng/searxng:latest
```

### 2. Start the MCP server

```bash
cd MCP
python server.py
```

### 3. Run the agent workflow

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

3. Set environment variables. You can create a `.env` file at the project root (not committed) using the format in `.env.example`.

Example `.env` values:

```
DATABASE_URL=postgresql+asyncpg://rohit:yourpassword@localhost:5432/articles
NVIDIA_API_KEY=nvapi-REPLACE_WITH_YOUR_KEY
```

4. Run the server from the `MCP` folder:

```bash
cd MCP
python server.py
```

Notes:
- Replace `rohit:yourpassword` with the DB user and password you created.
- If you use a different API provider, set the corresponding API key environment variable instead of `NVIDIA_API_KEY`.
