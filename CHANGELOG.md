# Changelog

All notable changes to this project will be documented in this file.

The project follows Semantic Versioning (SemVer): MAJOR.MINOR.PATCH.

## [Unreleased]

### Added
- Comprehensive retry and error handling framework across all LangGraph nodes.
- Shared `retry_helper` utility supporting exponential back-off for timeouts and rate limits, flat delays for other transient errors, and pre-call delays.
- Support for structured `node_errors` list reducer and a `needs_user_input` short-circuit flag in `AgentState` to prevent unhandled node failures.
- Robust exception handling in `planner`, `context_synthesizer`, `query_resolver`, `tool_call`, `next_task`, and `response_synthesizer` nodes, allowing routing directly to the synthesizer on permanent failure.
- Initial project documentation in README.md
- Repository-level ignore rules in .gitignore
- Future improvement notes for persistence, knowledge base expansion, and personalization

## [0.1.0] - 2026-07-05

### Added
- Initial project setup documentation and contribution-friendly project files
- Basic repository structure for the personal knowledge base workflow
