# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a CrewAI-based multi-agent planner system (`agent_planner/`) that orchestrates three specialized agents (Planner, Researcher, Writer) in a sequential pipeline to process complex user requests. The example use case is generating a project plan for a LEGO Geometry Engine (BrickVisionAI).

## Setup & Running

```bash
cd agent_planner
source venv/bin/activate
pip install -r requirements.txt   # if dependencies change
python main.py
```

The virtual environment is at `agent_planner/venv/`. A `.env` file is required with:
```
ANTHROPIC_API_KEY=<your key>
MODEL=claude-opus-4-6
```

## Architecture

The system uses **CrewAI** with a sequential process (`Process.sequential`):

1. **`src/agents.py`** — Defines three agents using `crewai.Agent`: Planner, Researcher, Writer. Each has a role, goal, and backstory that guide LLM behavior.

2. **`src/tasks.py`** — Defines three tasks using `crewai.Task`: plan, research, write. Each task is bound to a specific agent and carries a description + expected output.

3. **`main.py`** — Entry point. Instantiates agents and tasks, assembles them into a `Crew`, and calls `crew.kickoff()`. The `run()` function accepts a free-form `user_request` string that is passed through to all three tasks.

**Data flow:** The user request string flows into all three task descriptions simultaneously. Tasks execute sequentially: plan → research → write. CrewAI handles inter-task context passing automatically.

## Key Dependency Notes

- `crewai==0.108.0` — agent orchestration framework
- `anthropic==0.49.0` — underlying LLM provider (Claude)
- `python-dotenv` — loads `ANTHROPIC_API_KEY` and `MODEL` from `.env`

To add a new agent/task pair: define the agent factory in `src/agents.py`, define the task factory in `src/tasks.py`, then add both to the `Crew` in `main.py`.
