# Personal Knowledge Pool 🏊‍♂️

An AI-assisted knowledge base system designed to collect, process, retrieve, and reason over information from the web.

---

## 🌟 Unique Core Feature: Zero API Keys for Tooling & Integrations

A key architectural design of **Personal Knowledge Pool** is that **all MCP servers and agent tools run completely locally with ZERO API keys required**. 

Unlike typical AI frameworks that require expensive, rate-limited, or privacy-invasive third-party SaaS API keys, this project is built for self-hosted independence:
*   **Web Search via SearXNG:** Uses a local, dockerized instance of **SearXNG** (a privacy-respecting metasearch engine) to aggregate search results across multiple engines without any Google Search, Bing Search, or Tavily API keys.
*   **Local Scraper via Crawl4AI:** Extracts clean, LLM-friendly Markdown from web pages using `crawl4ai` running locally. No scrapers or proxy services (like Firecrawl or Zyte) are needed.
*   **Offline Feed & Sitemap Parser:** Directly parses RSS/Atom feeds and site XML maps using python library utility scripts, with no external feed ingestion services.
*   **Local PostgreSQL Database Tools:** Directly connects to and interacts with a local PostgreSQL server to read the active schema, execute safe read queries, and commit database writes.

> [!NOTE]
> The only API key needed is for the LLM reasoning agent itself (such as `NVIDIA_API_KEY` for the Nvidia AI Foundation models, or your preferred OpenAI-compatible LLM endpoint), which acts as the orchestrator. All other tools are entirely free and run locally.

---

## 🛠 What It Does

1.  **Searches the Web:** Resolves a query using local SearXNG.
2.  **Scrapes & Parses Pages:** Extracts the core text from webpage URLs, RSS feeds, or sitemaps into clean Markdown.
3.  **Local Knowledge Base Storage:** Persists relevant information (metadata, snippets, and full page contents) into structured PostgreSQL tables.
4.  **Retrieves and Reasons:** Employs a multi-node **LangGraph** workflow that can plan complex steps, invoke local tools, query existing databases, and synthesize unified responses.

---

## 📁 Project Layout

*   [agents/](file:///c:/Users/rohit/Personal/GitHubNew/PersonalKnowledgePool/agents): LangGraph orchestrator, state schemas, and processing nodes.
    *   **Planner Node:** Outlines tasks to solve a user's prompt.
    *   **Tool Call Node:** Executes registered MCP tools.
    *   **Query Resolver Node:** Finds and retrieves stored database knowledge.
    *   **Task Context & Synthesizer Nodes:** Combines information across tasks.
*   [MCP/](file:///c:/Users/rohit/Personal/GitHubNew/PersonalKnowledgePool/MCP): FastMCP server implementation exposing tools, database models, and service classes.
*   [searxng/](file:///c:/Users/rohit/Personal/GitHubNew/PersonalKnowledgePool/searxng): Local search engine Docker configuration and test query scripts.

---

## 🚀 Setup & Execution

### Option A: Docker Compose (Recommended)

Docker Compose orchestrates the database, search engine, MCP server, and LangGraph agent out-of-the-box.

#### Prerequisites
*   Docker & Docker Compose installed.
*   A `.env` file at the project root populated with your LLM API Key and PostgreSQL connection string (see the [Environment Variables](#environment-variables) section below).

#### Start Services
From the project root, run:
```bash
docker compose up --build
```
This launches:
*   `searxng` at `http://localhost:8888`
*   `mcp-server` at `http://localhost:8080/mcp`
*   `langgraph-agent` running in background/interactive mode.

#### Run the Agent
To start an interactive chat session inside the running agent container:
```bash
docker compose exec -it langgraph-agent python graph.py
```
To open a bash shell in the agent container:
```bash
docker compose exec -it langgraph-agent bash
```

---

### Option B: Manual Setup (Alternative)

If you prefer to run services individually without containerizing the Python apps:

#### 1. Start the SearXNG Container
From the `searxng` directory, execute:
```bash
docker run --name searxng -d \
    -p 8888:8080 \
    -v "./config/:/etc/searxng/" \
    -v "./data/:/var/cache/searxng/" \
    docker.io/searxng/searxng:latest
```

#### 2. Install Python Dependencies
Make sure you have [uv](https://github.com/astral-sh/uv) installed, then run:
```bash
uv sync
```

#### 3. Run the MCP Server
From the `MCP` directory:
```bash
cd MCP
python server.py
```

#### 4. Run the Agent Workflow
```bash
python agents/graph.py
```

---

## 🗄 Database Migrations (Alembic)

The system uses Alembic to manage database schema updates in PostgreSQL. Migration files reside in [MCP/alembic](file:///c:/Users/rohit/Personal/GitHubNew/PersonalKnowledgePool/MCP/alembic) and configuration is located in [MCP/alembic.ini](file:///c:/Users/rohit/Personal/GitHubNew/PersonalKnowledgePool/MCP/alembic.ini).

### Migrations with Docker Compose
If running under Docker Compose, execute migrations from the `mcp-server` container:

1.  **Apply Migrations:** Upgrades the database to the latest schema version.
    ```bash
    docker compose exec -T mcp-server alembic upgrade head
    ```
2.  **Check Current Revision:**
    ```bash
    docker compose exec -T mcp-server alembic current
    ```
3.  **Generate a New Migration:** (Run after modifying SQLAlchemy models in [MCP/db/models](file:///c:/Users/rohit/Personal/GitHubNew/PersonalKnowledgePool/MCP/db/models))
    ```bash
    docker compose exec -T mcp-server alembic revision --autogenerate -m "description of change"
    ```
4.  **Downgrade Schema:**
    ```bash
    docker compose exec -T mcp-server alembic downgrade -1
    ```

### Local/Manual Migrations
If running outside of Docker:
```bash
cd MCP
alembic upgrade head
```

---

## ⚙ Environment Variables

Create a `.env` file in the project root. Refer to `.env.example` for details.

| Variable Name | Description | Example / Recommended Value |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection string (uses `asyncpg`) | `postgresql+asyncpg://rohit:password@host.docker.internal:5432/articles` |
| `NVIDIA_API_KEY` | API Key for LangGraph orchestrator LLM (Nvidia) | `nvapi-REPLACE_WITH_YOUR_ACTUAL_KEY` |

### 🔑 Setting up a Free NVIDIA API Key

The LangGraph reasoning agent uses the NVIDIA API to run models (like Llama 3.1) for orchestration. NVIDIA offers a generous free tier with complimentary credits to test and run these models:

1. Visit the [NVIDIA API Catalog](https://build.nvidia.com/).
2. Log in or create a free NVIDIA Developer account.
3. Select an orchestration model (e.g., Llama-3.1-70b-instruct).
4. Click **Get API Key** or **Generate Key**.
5. Copy the generated key (which starts with `nvapi-`).
6. Add it to your `.env` file:
   ```env
   NVIDIA_API_KEY=nvapi-your-generated-key-here
   ```

> [!TIP]
> When running the database locally on the host machine and calling it from a docker container, use `host.docker.internal` instead of `localhost` in the connection string.

---

## 🛠 Local PostgreSQL Configuration & Troubleshooting

### 1. Database Creation
If running PostgreSQL locally on your host machine, create the database and user:
```sql
CREATE DATABASE articles;
CREATE USER rohit WITH ENCRYPTED PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE articles TO rohit;
```

### 2. Resolving Client Authentication (`pg_hba.conf`) Errors
If Docker containers cannot authenticate with PostgreSQL, you might see `no pg_hba.conf entry...`. 

To fix this:
1.  Locate your `pg_hba.conf` by running this in `psql`:
    ```sql
    SHOW hba_file;
    ```
2.  Edit the file (e.g., `/etc/postgresql/<version>/main/pg_hba.conf` on Linux) and add a rule allowing connections from your Docker network bridge subnet:
    ```conf
    # Allow Docker container subnet access
    host    all             all             172.18.0.0/16           scram-sha-256
    ```
3.  Ensure your `postgresql.conf` allows connections on all network interfaces:
    ```conf
    listen_addresses = '*'
    ```
4.  Restart PostgreSQL:
    ```bash
    sudo systemctl restart postgresql
    ```

---

## 🔮 Future Roadmap

*   **PostgreSQL Graph Checkpointing:** Save LangGraph session states directly to PostgreSQL instead of local SQLite files for shared multi-user sessions.
*   **Consolidated Personal Knowledge Base:** Establish a Karpathy-style knowledge vault that index and search over markdown notes, uploaded files, and bookmarks.
*   **User Personalization:** Enhance search reasoning nodes to weight queries and summarize results based on user preferences and search histories.
