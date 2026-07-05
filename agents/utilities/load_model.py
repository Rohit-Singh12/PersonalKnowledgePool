from pathlib import Path
import yaml
from typing import Literal
from langchain_nvidia_ai_endpoints import ChatNVIDIA


def load_models(llm_type: Literal['Planner', 'Router', 'Synthesizer']):
    CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
    with open(CONFIG_PATH, encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    if llm_type == 'Planner':
        return ChatNVIDIA(
            model=cfg["planner"]["model"]
        )

    if llm_type == 'Router':
        return ChatNVIDIA(
            model=cfg["router"]["model"]
        )

    return ChatNVIDIA(
        model=cfg["synthesizer"]["model"]
    )