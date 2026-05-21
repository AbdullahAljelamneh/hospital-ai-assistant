"""Subagent implementations."""

import json
from dataclasses import dataclass
from enum import Enum

from openai import OpenAI

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import LLM_MODEL_FAST, TEMPERATURE, ESCALATION_KEYWORDS
from agent.prompts.triage_prompt import TRIAGE_PROMPT
from agent.prompts.scheduling_prompt import SCHEDULING_PROMPT


class Urgency(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class TriageResult:
    urgency: Urgency
    category: str
    reasoning: str
    recommended_department: str | None
    escalate_to_human: bool


class TriageSubagent:
    """Classifies the urgency of a caller's message."""

    def __init__(self, client: OpenAI):
        self.client = client

    def classify(self, message: str) -> TriageResult:
        message_lower = message.lower()
        for keyword in ESCALATION_KEYWORDS:
            if keyword in message_lower:
                return TriageResult(
                    urgency=Urgency.CRITICAL,
                    category="emergency",
                    reasoning=f"Keyword match: '{keyword}'",
                    recommended_department="emergency",
                    escalate_to_human=True,
                )

        response = self.client.chat.completions.create(
            model=LLM_MODEL_FAST,
            max_tokens=300,
            temperature=0.1,
            messages=[
                {"role": "user", "content": TRIAGE_PROMPT.format(message=message)}
            ],
        )

        try:
            raw = response.choices[0].message.content
            raw = (
                raw.strip()
                .removeprefix("```json")
                .removeprefix("```")
                .removesuffix("```")
                .strip()
            )
            result = json.loads(raw)
            return TriageResult(
                urgency=Urgency(result["urgency"]),
                category=result["category"],
                reasoning=result["reasoning"],
                recommended_department=result.get("recommended_department"),
                escalate_to_human=result.get("escalate_to_human", False),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return TriageResult(
                urgency=Urgency.HIGH,
                category="unknown",
                reasoning="Failed to parse triage response — escalating for safety",
                recommended_department=None,
                escalate_to_human=True,
            )


class SchedulingSubagent:
    """Handles appointment booking conversations."""

    def __init__(self, client: OpenAI):
        self.client = client

    def handle(
        self, message: str, context: str = "", conversation_history: list = None
    ) -> str:
        messages = conversation_history or []
        messages.append({"role": "user", "content": message})

        response = self.client.chat.completions.create(
            model=LLM_MODEL_FAST,
            max_tokens=500,
            temperature=TEMPERATURE,
            messages=[
                {
                    "role": "system",
                    "content": SCHEDULING_PROMPT.format(
                        context=context, message=message
                    ),
                },
                *messages,
            ],
        )

        return response.choices[0].message.content


class FAQSubagent:
    """Answers informational questions using RAG context."""

    def __init__(self, client: OpenAI):
        self.client = client

    def answer(self, message: str, context: str) -> str:
        response = self.client.chat.completions.create(
            model=LLM_MODEL_FAST,
            max_tokens=400,
            temperature=TEMPERATURE,
            messages=[
                {
                    "role": "system",
                    "content": """You are a hospital information assistant. Answer the caller's question 
using ONLY the provided context. If the context doesn't contain the answer, 
say so and offer to transfer to a human. Keep answers concise and phone-friendly.
Respond in the same language as the caller.""",
                },
                {
                    "role": "user",
                    "content": f"<context>\n{context}\n</context>\n\nCaller's question: {message}",
                },
            ],
        )

        return response.choices[0].message.content
