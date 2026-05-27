"""
Orchestrator — Multi-Agent Consensus Engine (Librarian/Critic/Strategist).

Before any response is sent to the user during ingestion, three virtual agents
deliberate internally to ensure precision and avoid hallucinations:

  1. THE LIBRARIAN (Fact-Checker): Extracts the absolute current state from the
     user's Knowledge Graph. Provides only relevant nodes and edges. No interpretation.

  2. THE CRITIC (Reality-Check): Compares the Librarian's data against Market Pulse
     data. Identifies contradictions, gaps in logic, and outdated assumptions.
     Highlights Tension Nodes.

  3. THE STRATEGIST (Synthesizer): Reviews facts and warnings. Formulates a response
     that acknowledges the user's identity, addresses tensions, and asks the most
     high-leverage question to move the journey forward.

This uses 3 separate LLM calls (as per user requirement: "nothing static, full 3 LLM calls").
"""

import json
from dataclasses import dataclass
from typing import Optional

from app.services.ai_service import generate_response


@dataclass
class LibrarianOutput:
    """Facts extracted by the Librarian agent."""
    relevant_nodes: list[dict]
    relevant_edges: list[dict]
    user_identity_summary: str
    current_capabilities: list[str]
    stated_ambitions: list[str]
    known_constraints: list[str]
    evidence_present: list[str]
    raw_text: str


@dataclass
class CriticOutput:
    """Analysis from the Critic agent."""
    tensions: list[dict]  # Contradictions found
    gaps_in_logic: list[str]  # Logical gaps
    outdated_assumptions: list[str]  # Things that may no longer be true
    risk_assessment: str  # Overall risk level
    recommended_focus: str  # What the Strategist should prioritize
    raw_text: str


@dataclass
class StrategistOutput:
    """Final synthesized response from the Strategist."""
    response: str  # The user-facing response
    next_question: Optional[str]  # Follow-up question (if any)
    persona_mode: str  # Which persona to adopt (mentor, stoic, challenger, etc.)
    dimension_focus: str  # cognitive, emotional, temporal, social
    confidence: float  # How confident the Strategist is in this response
    raw_text: str


class Orchestrator:
    """
    The Internal Debate engine. Runs 3 LLM calls per response:
    Librarian → Critic → Strategist.
    
    Usage:
        orchestrator = Orchestrator()
        result = orchestrator.deliberate(
            user_query="What should I learn first?",
            graph_summary=graph.to_summary(),
            market_data=market_pulse,
            context={"ingestion_round": 3, "gaps_remaining": 5}
        )
        print(result.response)  # The final user-facing response
    """

    def deliberate(
        self,
        user_query: str,
        graph_summary: dict,
        market_data: dict,
        context: dict | None = None,
        mode: str = "ingestion",
    ) -> StrategistOutput:
        """
        Run the full 3-agent deliberation cycle.
        
        Args:
            user_query: The user's message or answer
            graph_summary: Output from MemoryGraph.to_summary()
            market_data: Current market pulse data
            context: Additional context (ingestion round, gaps, etc.)
            mode: "ingestion" or "guidance" (affects persona selection)
        
        Returns:
            StrategistOutput with the final response
        """
        # Phase 1: Librarian extracts facts
        librarian_output = self._run_librarian(graph_summary, user_query, context)

        # Phase 2: Critic compares facts vs market
        critic_output = self._run_critic(librarian_output, market_data, context)

        # Phase 3: Strategist synthesizes response
        strategist_output = self._run_strategist(
            librarian_output, critic_output, user_query, context, mode
        )

        return strategist_output

    def deliberate_for_question(
        self,
        gap: dict,
        graph_summary: dict,
        market_data: dict,
        context: dict | None = None,
    ) -> str:
        """
        Specialized deliberation for generating an ingestion question.
        
        Instead of responding to a user query, this generates the NEXT question
        to ask based on gaps, tensions, and market context.
        """
        librarian_output = self._run_librarian(
            graph_summary,
            f"What do we need to learn about: {gap.get('label', gap.get('node_type', 'unknown'))}",
            context,
        )

        critic_output = self._run_critic(librarian_output, market_data, context)

        # Strategist generates a question instead of a response
        prompt = f"""You are the Strategist. Based on the Librarian's facts and the Critic's analysis,
generate ONE adaptive question to fill this gap in the user's career profile.

GAP TO FILL:
- Type: {gap.get('node_type', 'unknown')}
- Missing: {gap.get('missing_fields', [])}
- Priority: {gap.get('priority', 0.5)}
- Label: {gap.get('label', 'Unknown gap')}

LIBRARIAN'S FACTS:
{librarian_output.raw_text[:800]}

CRITIC'S ANALYSIS:
{critic_output.raw_text[:800]}

CONTEXT:
{json.dumps(context or {}, default=str)[:400]}

Rules:
1. The question must NOT sound like a survey or a form field
2. It should feel like a mentor probing deeper into the student's real situation
3. Reference what you already know about them (from the Librarian's facts)
4. If the Critic flagged tensions, weave the tension into the question naturally
5. Be specific — don't ask "tell me about your skills", ask "You mentioned Python — have you built anything beyond scripts with it, like a web API or a data pipeline?"
6. Adapt the tone based on the user's emotional state (if known)

Return ONLY the question text, nothing else."""

        try:
            question = generate_response(prompt).strip()
            return question.strip('"').strip("'")
        except Exception:
            return f"Can you tell me more about your {gap.get('node_type', 'background')}?"

    # ── Phase 1: The Librarian ────────────────────────────────────────────

    def _run_librarian(
        self,
        graph_summary: dict,
        query: str,
        context: dict | None = None,
    ) -> LibrarianOutput:
        """
        THE LIBRARIAN: Extract the absolute current state of the User's Knowledge Graph.
        Provide only the nodes and edges relevant to the current query. No interpretation.
        """
        graph_text = json.dumps(graph_summary, default=str)[:2000]
        context_text = json.dumps(context or {}, default=str)[:400]

        prompt = f"""ROLE: You are THE LIBRARIAN. Your ONLY job is to extract facts from the user's Knowledge Graph.
You must NOT interpret, advise, or add your own analysis. Report ONLY what exists in the graph.

USER'S KNOWLEDGE GRAPH STATE:
{graph_text}

CURRENT QUERY/CONTEXT:
Query: {query}
Context: {context_text}

Extract and return a JSON object with ONLY these fields:
{{
    "user_identity_summary": "1-2 sentence factual summary of who this user is",
    "current_capabilities": ["list of actual skills with proficiency indicators"],
    "stated_ambitions": ["list of stated goals and dream roles"],
    "known_constraints": ["list of constraints: time, money, devices, college load"],
    "evidence_present": ["list of concrete evidence: projects, certs, GitHub repos"],
    "relevant_nodes": ["node labels relevant to the current query"],
    "relevant_edges": ["relationship descriptions relevant to the query"],
    "data_quality": "high | medium | low — based on how much real data vs defaults exist"
}}

CRITICAL: Report ONLY what the data says. If a field has no data, say "no data available".
Do NOT fill gaps with assumptions."""

        try:
            response_text = generate_response(prompt)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            data = json.loads(response_text.strip())
            return LibrarianOutput(
                relevant_nodes=[{"label": n} for n in data.get("relevant_nodes", [])],
                relevant_edges=[{"desc": e} for e in data.get("relevant_edges", [])],
                user_identity_summary=data.get("user_identity_summary", "No data available"),
                current_capabilities=data.get("current_capabilities", []),
                stated_ambitions=data.get("stated_ambitions", []),
                known_constraints=data.get("known_constraints", []),
                evidence_present=data.get("evidence_present", []),
                raw_text=response_text,
            )
        except Exception as e:
            print(f"[Orchestrator:Librarian] Failed: {e}")
            return LibrarianOutput(
                relevant_nodes=[],
                relevant_edges=[],
                user_identity_summary="Data extraction failed — using raw graph summary",
                current_capabilities=[],
                stated_ambitions=[],
                known_constraints=[],
                evidence_present=[],
                raw_text=graph_text[:500],
            )

    # ── Phase 2: The Critic ───────────────────────────────────────────────

    def _run_critic(
        self,
        librarian: LibrarianOutput,
        market_data: dict,
        context: dict | None = None,
    ) -> CriticOutput:
        """
        THE CRITIC: Compare the Librarian's data against the Market Pulse data.
        Identify contradictions, gaps in logic, or outdated assumptions.
        Highlight the 'Tension Nodes'.
        """
        market_text = json.dumps({
            "demanded_skills": market_data.get("demanded_skills", market_data.get("top_demanded_skills", [])),
            "emerging_skills": market_data.get("emerging_skills", []),
            "market_warnings": market_data.get("market_warnings", []),
            "project_patterns": market_data.get("project_patterns", []),
            "recruiter_signals": market_data.get("recruiter_language", market_data.get("recruiter_signals", [])),
        }, default=str)[:1200]

        prompt = f"""ROLE: You are THE CRITIC. Your job is to find problems, contradictions, and blind spots.
Compare what the Librarian found against current market reality.

LIBRARIAN'S REPORT:
- User: {librarian.user_identity_summary}
- Capabilities: {', '.join(librarian.current_capabilities) or 'none recorded'}
- Ambitions: {', '.join(librarian.stated_ambitions) or 'none stated'}
- Constraints: {', '.join(librarian.known_constraints) or 'none identified'}
- Evidence: {', '.join(librarian.evidence_present) or 'none provided'}

CURRENT MARKET DATA:
{market_text}

CONTEXT: {json.dumps(context or {}, default=str)[:300]}

Analyze and return a JSON object:
{{
    "tensions": [
        {{
            "type": "fact_vs_belief | aspiration_vs_reality | gap_vs_confidence",
            "claim": "What the user claims or implies",
            "reality": "What the market data shows",
            "severity": 0.7
        }}
    ],
    "gaps_in_logic": ["List of logical gaps or missing connections"],
    "outdated_assumptions": ["Things the user might believe that are no longer true"],
    "risk_assessment": "low | medium | high — overall risk of current trajectory",
    "recommended_focus": "What the Strategist should prioritize in the response"
}}

Rules:
1. Only flag REAL tensions. Don't manufacture problems.
2. Be specific — "skills don't match market" is too vague. Say which skills and which market demands.
3. If there are no tensions, return an empty tensions array. Don't force conflicts.
4. Consider the Indian tech market context specifically."""

        try:
            response_text = generate_response(prompt)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            data = json.loads(response_text.strip())
            return CriticOutput(
                tensions=data.get("tensions", []),
                gaps_in_logic=data.get("gaps_in_logic", []),
                outdated_assumptions=data.get("outdated_assumptions", []),
                risk_assessment=data.get("risk_assessment", "medium"),
                recommended_focus=data.get("recommended_focus", "Continue gathering information"),
                raw_text=response_text,
            )
        except Exception as e:
            print(f"[Orchestrator:Critic] Failed: {e}")
            return CriticOutput(
                tensions=[],
                gaps_in_logic=[],
                outdated_assumptions=[],
                risk_assessment="unknown",
                recommended_focus="Insufficient data for critique — continue gathering information",
                raw_text=f"Critic analysis failed: {e}",
            )

    # ── Phase 3: The Strategist ───────────────────────────────────────────

    def _run_strategist(
        self,
        librarian: LibrarianOutput,
        critic: CriticOutput,
        user_query: str,
        context: dict | None = None,
        mode: str = "ingestion",
    ) -> StrategistOutput:
        """
        THE STRATEGIST: Review the Librarian's facts and the Critic's warnings.
        Formulate a response that acknowledges the user's identity, addresses
        tensions, and asks the most high-leverage question.
        """
        # Determine persona based on context
        persona_hint = self._select_persona(critic, context)

        prompt = f"""ROLE: You are THE STRATEGIST. You have received facts from the Librarian and 
warnings from the Critic. Synthesize ONE response for the user.

MODE: {mode} ({"asking questions to build their career profile" if mode == "ingestion" else "providing career guidance"})

LIBRARIAN'S FACTS:
- User: {librarian.user_identity_summary}
- Skills: {', '.join(librarian.current_capabilities) or 'none yet'}
- Goals: {', '.join(librarian.stated_ambitions) or 'not yet defined'}
- Constraints: {', '.join(librarian.known_constraints) or 'unknown'}
- Evidence: {', '.join(librarian.evidence_present) or 'none'}

CRITIC'S WARNINGS:
- Risk Level: {critic.risk_assessment}
- Tensions: {json.dumps(critic.tensions, default=str)[:600]}
- Logic Gaps: {', '.join(critic.gaps_in_logic) or 'none'}
- Focus: {critic.recommended_focus}

USER'S MESSAGE: {user_query}

PERSONA GUIDANCE: {persona_hint}

CONTEXT: {json.dumps(context or {}, default=str)[:300]}

Return a JSON object:
{{
    "response": "Your response to the user. Be specific, personal, and action-oriented.",
    "next_question": "A follow-up question if appropriate, otherwise null",
    "persona_mode": "mentor | stoic | challenger | cheerleader | analyst",
    "dimension_focus": "cognitive | emotional | temporal | social",
    "confidence": 0.8
}}

Rules:
1. If there are tensions, weave them naturally into your response — don't list them mechanically
2. Reference specific things the Librarian found about the user
3. If in ingestion mode, your response should process their answer and naturally lead to the next question
4. The response should feel like talking to a brilliant mentor who remembers everything about you
5. NEVER be generic. Use their actual skills, goals, and constraints in your language
6. Keep response under 150 words for ingestion mode, under 250 for guidance mode"""

        try:
            response_text = generate_response(prompt)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            data = json.loads(response_text.strip())
            return StrategistOutput(
                response=data.get("response", "I need a moment to process that. Could you tell me more?"),
                next_question=data.get("next_question"),
                persona_mode=data.get("persona_mode", "mentor"),
                dimension_focus=data.get("dimension_focus", "cognitive"),
                confidence=float(data.get("confidence", 0.7)),
                raw_text=response_text,
            )
        except Exception as e:
            print(f"[Orchestrator:Strategist] Failed: {e}")
            return StrategistOutput(
                response="That's helpful context. Let me process that and ask you something more specific.",
                next_question=None,
                persona_mode="mentor",
                dimension_focus="cognitive",
                confidence=0.3,
                raw_text=f"Strategist synthesis failed: {e}",
            )

    def _select_persona(self, critic: CriticOutput, context: dict | None) -> str:
        """
        Dynamic persona selection based on the Critic's analysis and context.
        
        This implements Recursive Self-Prompting — the system adjusts its own
        persona based on the current state of the conversation.
        """
        risk = critic.risk_assessment
        tensions = critic.tensions
        round_num = (context or {}).get("ingestion_round", 0)

        # High risk or many tensions → Stoic Mentor (calm, grounding)
        if risk == "high" or len(tensions) >= 3:
            return (
                "Adopt a STOIC MENTOR persona. The user may be overwhelmed or unrealistic. "
                "Be calm, focus on small wins, and gently reality-check without crushing motivation."
            )

        # Early rounds → Encouraging Mentor (build trust)
        if round_num <= 2:
            return (
                "Adopt a WARM MENTOR persona. This is early in the conversation. "
                "Build rapport, show genuine interest, and make the user feel heard."
            )

        # Mid-rounds with tensions → Challenger (push thinking)
        if tensions and round_num > 2:
            return (
                "Adopt a CHALLENGER persona. The user has shared enough for you to push back "
                "constructively. Ask harder questions. Don't accept surface-level answers."
            )

        # Late rounds → Analyst (precise, efficient)
        if round_num > 5:
            return (
                "Adopt an ANALYST persona. We're in the later rounds of ingestion. "
                "Be precise and efficient. Fill remaining gaps quickly without being robotic."
            )

        # Default → Balanced Mentor
        return (
            "Adopt a BALANCED MENTOR persona. Be encouraging but honest. "
            "Show you've been paying attention to details they shared earlier."
        )
