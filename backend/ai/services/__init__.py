# backend/ai/services/__init__.py

"""
Service layer for AI helpers used by the EMS chatbot.

Exports:
- answer_question: main entry point for answering natural-language questions.
- plan_action:     classify a message into a potential write action + params.
"""

from .query_planner import answer_question
from .action_planner import plan_action

__all__ = ["answer_question", "plan_action"]
