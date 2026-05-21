"""Agent Orchestrator — the main agentic loop."""

import json
import sys
from pathlib import Path
from dataclasses import dataclass, field

from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import LLM_MODEL, LLM_MODEL_FAST, TEMPERATURE, OPENROUTER_API_KEY
from agent.prompts.system_prompt import ORCHESTRATOR_SYSTEM_PROMPT, ROUTING_PROMPT
from agent.subagents import TriageSubagent, SchedulingSubagent, FAQSubagent, Urgency
from rag.retriever import HospitalRetriever
from mcp_server.hospital_tools import (
    get_department_info,
    check_appointment_availability,
    book_appointment,
    get_patient_queue_status,
    escalate_to_human,
)


@dataclass
class ConversationState:
    messages: list = field(default_factory=list)
    current_intent: str = "unknown"
    triage_urgency: str = "normal"
    pending_booking: dict = field(default_factory=dict)
    escalated: bool = False


class HospitalAgentOrchestrator:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY
        )
        self.retriever = HospitalRetriever()

        self.triage = TriageSubagent(self.client)
        self.scheduler = SchedulingSubagent(self.client)
        self.faq = FAQSubagent(self.client)

        self.state = ConversationState()

    def _classify_intent(self, message: str) -> str:
        response = self.client.chat.completions.create(
            model=LLM_MODEL_FAST,
            max_tokens=50,
            temperature=0.0,
            messages=[
                {"role": "user", "content": ROUTING_PROMPT.format(message=message)}
            ],
        )
        return response.choices[0].message.content.strip().upper()

    def _execute_tool(self, tool_name: str, **kwargs) -> dict:
        tool_map = {
            "lookup_department": get_department_info,
            "check_available_slots": check_appointment_availability,
            "schedule_appointment": book_appointment,
            "check_queue": get_patient_queue_status,
            "transfer_to_human": escalate_to_human,
        }

        tool_fn = tool_map.get(tool_name)
        if not tool_fn:
            return {"error": f"Unknown tool: {tool_name}"}

        return tool_fn(**kwargs)

    def _extract_department(self, message: str) -> str | None:
        dept_keywords = {
            "emergency": ["emergency", "er", "طوارئ"],
            "internal_medicine": ["internal", "medicine", "باطنية"],
            "cardiology": ["cardiology", "heart", "cardiac", "قلب"],
            "orthopedics": ["orthopedic", "bone", "joint", "fracture", "عظام"],
            "pediatrics": ["pediatric", "children", "child", "kids", "أطفال"],
            "radiology": ["radiology", "xray", "x-ray", "mri", "ct scan", "أشعة"],
            "laboratory": ["lab", "laboratory", "blood test", "مختبر"],
            "pharmacy": ["pharmacy", "medication", "medicine", "صيدلية"],
            "billing": ["billing", "insurance", "payment", "فواتير", "تأمين"],
        }

        message_lower = message.lower()
        for dept_id, keywords in dept_keywords.items():
            if any(kw in message_lower for kw in keywords):
                return dept_id
        return None

    def process_message(self, message: str) -> str:
        self.state.messages.append({"role": "user", "content": message})

        # Step 1: Triage
        print("Triaging...")
        triage_result = self.triage.classify(message)
        self.state.triage_urgency = triage_result.urgency.value
        print(
            f"  Urgency: {triage_result.urgency.value} | Reasoning: {triage_result.reasoning}"
        )

        # Step 2: Emergency fast-path
        if triage_result.urgency == Urgency.CRITICAL:
            print("CRITICAL — Escalating immediately")
            result = self._execute_tool(
                "transfer_to_human", reason=triage_result.reasoning, urgency="critical"
            )
            self.state.escalated = True
            response = f"I'm transferring you to our emergency team right away. Please stay on the line. {result['message']}"
            self.state.messages.append({"role": "assistant", "content": response})
            return response

        if triage_result.escalate_to_human:
            result = self._execute_tool(
                "transfer_to_human",
                reason=triage_result.reasoning,
                urgency=triage_result.urgency.value,
            )
            self.state.escalated = True
            response = (
                f"Let me connect you with someone who can help. {result['message']}"
            )
            self.state.messages.append({"role": "assistant", "content": response})
            return response

        # Step 3: Intent classification
        print("Classifying intent...")
        intent = self._classify_intent(message)
        self.state.current_intent = intent
        print(f"  Intent: {intent}")

        # Step 4: Route to subagent
        response = ""

        if intent == "APPOINTMENT":
            print("Routing to Scheduling subagent")
            rag_results = self.retriever.retrieve(message, top_k=2)
            context = self.retriever.format_context(rag_results)
            response = self.scheduler.handle(
                message, context, self.state.messages.copy()
            )

        elif intent == "DEPARTMENT_INFO":
            dept = self._extract_department(message)
            if dept:
                result = self._execute_tool("lookup_department", department_id=dept)
                if "error" not in result:
                    response = (
                        f"The {result['department']} is currently {result['status']}. "
                        f"Estimated wait time is about {result['estimated_wait_minutes']} minutes. "
                        f"You can reach them at {result['phone']}."
                    )
                else:
                    response = result["error"]
            else:
                rag_results = self.retriever.retrieve(message)
                context = self.retriever.format_context(rag_results)
                response = self.faq.answer(message, context)

        elif intent == "QUEUE_STATUS":
            dept = self._extract_department(message)
            if dept:
                result = self._execute_tool("check_queue", department_id=dept)
                if "error" not in result:
                    response = (
                        f"There are currently {result['patients_in_queue']} patients waiting "
                        f"at {result['department']}. Estimated wait is about "
                        f"{result['estimated_wait_minutes']} minutes. {result['recommendation']}"
                    )
                else:
                    response = result["error"]
            else:
                response = "Which department would you like to check the queue for?"

        elif intent in ("POLICY_QUESTION", "GENERAL"):
            rag_results = self.retriever.retrieve(message)
            context = self.retriever.format_context(rag_results)
            response = self.faq.answer(message, context)

        elif intent == "HUMAN_TRANSFER":
            result = self._execute_tool(
                "transfer_to_human",
                reason="Caller requested human operator",
                urgency="normal",
            )
            self.state.escalated = True
            response = result["message"]

        else:
            rag_results = self.retriever.retrieve(message)
            context = self.retriever.format_context(rag_results)
            response = self.faq.answer(message, context)

        self.state.messages.append({"role": "assistant", "content": response})
        return response


def run_interactive():
    print("=" * 50)
    print("Hospital AI Assistant - Demo Mode")
    print("Type your message as if calling the hospital.")
    print("Type 'quit' to exit.")
    print("=" * 50)

    agent = HospitalAgentOrchestrator()

    while True:
        try:
            user_input = input("\nCaller: ")
        except (EOFError, KeyboardInterrupt):
            break

        if user_input.lower() in ("quit", "exit", "q"):
            break

        if not user_input.strip():
            continue

        response = agent.process_message(user_input)
        print(f"\nAgent: {response}")

        if agent.state.escalated:
            print("--- Call transferred to human operator ---")
            break


if __name__ == "__main__":
    run_interactive()
