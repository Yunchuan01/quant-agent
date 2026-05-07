# Quant Agent

AI-powered data screening agent built with:
- **LangGraph ReAct Agent** - natural language to structured screening logic
- **MCP (Model Context Protocol)** - independent tool server for quantitative indicators
- **Bridge Tools** - main-process tools for data execution and script saving
- **Harness Framework** - Rules + Hooks for constraining Agent behavior
- **Skills System** - on-demand domain knowledge loading

## Quick Start

```bash
# Install dependencies
pip install -e .

# Configure API keys
cp .env.example .env
# Edit .env with your actual keys

# Run
python app/screener.py
```

## Project Structure

```
quant-agent/
├── app/                  # Entry point and settings
├── src/
│   ├── agent/            # Agent core, tools, context, harness, memory
│   └── screening/        # Screening logic, script saver, result display
├── mcp_server/           # Independent MCP tool server
├── datahub/              # Data loading and caching
├── infrastructure/       # Config, logging, session, telemetry, errors
├── utils/                # Agent utilities (LLM helper, result checker)
└── .quant_agent/         # Runtime config (rules, hooks, skills, sessions)
```
