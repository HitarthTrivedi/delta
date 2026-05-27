"""
Tension Resolver — Detects conflicts between user beliefs and market reality.

When the system discovers a contradiction between what the user claims/believes
and what the market data shows, it creates a TensionNode. These tensions are
surfaced to the user as "Challenge Questions" during ingestion.

Tension Types:
  - fact_vs_belief: A verifiable fact contradicts a user belief
    (e.g., "Java is dying" when market shows Java demand is stable)
  - aspiration_vs_reality: User's timeline/scope is unrealistic
    (e.g., "Build a SaaS in 2 days" when average is 6 months)
  - gap_vs_confidence: User overestimates their readiness
    (e.g., claims "expert in ML" but has no model deployments)

Resolution flows:
  1. Detect tension → Create TensionNode
  2. Generate a Challenge Question that surfaces the conflict constructively
  3. User responds → Resolution is recorded
  4. Graph is updated based on the resolution
"""

import json
import uuid
import datetime
from dataclasses import dataclass, field
from typing import Optional

from app.services.ai_service import generate_response


@dataclass
class TensionNode:
    """Represents a detected conflict between user belief and reality."""
    id: str
    user_claim: str
    market_reality: str
    tension_type: str  # fact_vs_belief, aspiration_vs_reality, gap_vs_confidence
    severity: float  # 0.0 - 1.0
    challenge_question: str = ""
    resolution: Optional[str] = None
    status: str = "active"  # active, challenged, resolved, dismissed
    source_node_ids: list = field(default_factory=list)
    created_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_claim": self.user_claim,
            "market_reality": self.market_reality,
            "tension_type": self.tension_type,
            "severity": self.severity,
            "challenge_question": self.challenge_question,
            "resolution": self.resolution,
            "status": self.status,
        }


class TensionResolver:
    """
    Detects and resolves tensions between user beliefs and market data.
    
    The core insight: the AI should never silently overwrite user data when
    market data contradicts it. Instead, it creates a Tension Node and surfaces
    a Challenge Question that gives the user agency to respond.
    """

    # Severity thresholds
    SEVERITY_LOW = 0.3
    SEVERITY_MEDIUM = 0.6
    SEVERITY_HIGH = 0.8
    SEVERITY_CRITICAL = 0.95

    def to_tension_node_obj(self, db_node) -> TensionNode:
        """Converts a database TensionNodeModel to a domain TensionNode object."""
        return TensionNode(
            id=db_node.id,
            user_claim=db_node.user_claim,
            market_reality=db_node.market_reality,
            tension_type=db_node.tension_type,
            severity=db_node.severity,
            challenge_question=db_node.challenge_question or "",
            resolution=db_node.resolution,
            status=db_node.status,
            source_node_ids=[db_node.source_belief_node_id] if db_node.source_belief_node_id else [],
            created_at=db_node.created_at or datetime.datetime.utcnow(),
        )

    def detect_tensions(
        self,
        user_frame: dict,
        market_data: dict,
        ingestion_answers: list[dict] | None = None,
    ) -> list[TensionNode]:
        """
        Compare user's graph frame against market data to find conflicts.
        
        Args:
            user_frame: The user's current semantic frame (from MemoryGraph.get_frame())
            market_data: Current market pulse data
            ingestion_answers: Optional list of ingestion Q&A pairs for deeper analysis
        
        Returns:
            List of detected TensionNodes, sorted by severity (highest first)
        """
        tensions = []
        tensions.extend(self._detect_timeline_tensions(user_frame, market_data))
        tensions.extend(self._detect_skill_gap_tensions(user_frame, market_data))
        tensions.extend(self._detect_belief_tensions(user_frame, market_data))
        tensions.extend(self._detect_feasibility_tensions(user_frame, market_data))

        if ingestion_answers:
            tensions.extend(self._detect_answer_tensions(ingestion_answers, market_data))

        # Deduplicate by type + claim similarity
        seen_claims = set()
        unique_tensions = []
        for t in tensions:
            claim_key = f"{t.tension_type}:{t.user_claim[:50]}"
            if claim_key not in seen_claims:
                seen_claims.add(claim_key)
                unique_tensions.append(t)

        unique_tensions.sort(key=lambda t: t.severity, reverse=True)
        return unique_tensions

    def generate_challenge(self, tension: TensionNode, user_context: dict = None) -> str:
        """
        Generate a Challenge Question that surfaces the conflict constructively.
        
        The question should:
        1. Acknowledge the user's perspective
        2. Present the conflicting data without being condescending
        3. Give the user a choice (not a correction)
        4. Sound like a mentor probing deeper, not a system catching an error
        """
        context_str = ""
        if user_context:
            context_str = f"\nUser context: {json.dumps(user_context, default=str)[:500]}"

        prompt = f"""You are Delta, an elite career mentor. You've detected a tension between 
what the user believes and what the market data shows.

Tension Type: {tension.tension_type}
User's Claim: {tension.user_claim}
Market Reality: {tension.market_reality}
Severity: {tension.severity}/1.0
{context_str}

Generate ONE challenge question that:
1. Acknowledges the user's perspective without dismissing it
2. Presents the market data as context, not as a correction
3. Gives the user agency — they should feel like they're making an informed choice
4. Sounds like a thoughtful mentor, not a system flagging an error
5. Is specific and actionable, not vague

Examples of good challenges:
- "I've looked at deployment timelines for similar AI health tools — they average 6 months for a production-ready MVP. Given your 2-week goal, are we building a demo prototype or planning for a longer launch?"
- "Your confidence in ML is strong, but 90% of ML Engineer postings now require model deployment experience beyond notebooks. Have you deployed a model to production, even a simple one?"

Return ONLY the challenge question text, nothing else."""

        try:
            question = generate_response(prompt).strip()
            # Clean up any quotes or formatting
            question = question.strip('"').strip("'").strip()
            tension.challenge_question = question
            tension.status = "challenged"
            return question
        except Exception as e:
            print(f"[TensionResolver] Challenge generation failed: {e}")
            # Fallback challenge question
            tension.challenge_question = (
                f"I noticed something interesting — you mentioned '{tension.user_claim}', "
                f"but current market data suggests {tension.market_reality}. "
                f"How would you like to approach this?"
            )
            tension.status = "challenged"
            return tension.challenge_question

    def resolve(self, tension: TensionNode, user_response: str) -> dict:
        """
        Process the user's response to a challenge question.
        
        Returns a resolution dict with:
        - action: what the system should do ("accept_user", "accept_market", "compromise", "explore_further")
        - updated_belief: the refined understanding
        - graph_updates: list of node/edge changes to apply
        """
        prompt = f"""You are Delta's cognitive resolution engine. The user responded to a tension challenge.

Original Tension:
- Type: {tension.tension_type}
- User's Claim: {tension.user_claim}
- Market Reality: {tension.market_reality}
- Challenge Question: {tension.challenge_question}

User's Response: {user_response}

Analyze the response and return a JSON object:
{{
    "action": "accept_user | accept_market | compromise | explore_further",
    "updated_belief": "The refined understanding combining user's response with market data",
    "confidence_adjustment": 0.1,  // How much to adjust confidence (-0.3 to +0.3)
    "reasoning": "Why you chose this resolution",
    "follow_up_needed": false,
    "follow_up_question": null
}}

Rules:
- "accept_user": User provides valid reasoning that overrides market data (rare)
- "accept_market": User acknowledges the gap and accepts the market view
- "compromise": User partially accepts; create a middle ground
- "explore_further": Response is ambiguous; need more information"""

        try:
            response_text = generate_response(prompt)
            # Parse JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            resolution = json.loads(response_text.strip())
            # Inject status key for backward compatibility
            action = resolution.get("action", "compromise")
            status = "resolved" if action != "explore_further" else "active"
            resolution["status"] = status
            
            tension.resolution = resolution.get("updated_belief", "Resolved through user dialogue")
            tension.status = status
            return resolution

        except Exception as e:
            print(f"[TensionResolver] Resolution failed: {e}")
            tension.resolution = f"User response: {user_response}"
            tension.status = "resolved"
            return {
                "action": "compromise",
                "status": "resolved",
                "updated_belief": f"User acknowledged the tension. Original claim: {tension.user_claim}. User perspective: {user_response}",
                "confidence_adjustment": 0.0,
                "reasoning": "Resolution fallback due to parsing error",
                "follow_up_needed": False,
            }

    # ── Private Detection Methods ─────────────────────────────────────────

    def _detect_timeline_tensions(self, user_frame: dict, market_data: dict) -> list[TensionNode]:
        """Detect when user's timeline expectations are unrealistic."""
        tensions = []
        ambition_nodes = user_frame.get("nodes_by_type", {}).get("ambition", [])

        for node in ambition_nodes:
            props = node.get("properties", {})
            
            # Check for unrealistic short-term targets
            short_term = props.get("short_term_targets", [])
            if isinstance(short_term, list):
                for target in short_term:
                    target_lower = str(target).lower()
                    # Detect overly aggressive timelines
                    if any(word in target_lower for word in ["1 day", "2 days", "1 week", "weekend", "tonight"]):
                        tensions.append(TensionNode(
                            id=str(uuid.uuid4()),
                            user_claim=f"Plans to achieve: '{target}'",
                            market_reality="Industry benchmarks for similar goals typically require 2-6 months for meaningful progress.",
                            tension_type="aspiration_vs_reality",
                            severity=self.SEVERITY_HIGH,
                        ))

            # Check confidence vs capabilities
            confidence = props.get("confidence_level", "medium")
            if confidence in ("high", "very high", "expert"):
                capability_nodes = user_frame.get("nodes_by_type", {}).get("capability", [])
                if not capability_nodes or all(
                    not n.get("properties", {}).get("current_skills") for n in capability_nodes
                ):
                    tensions.append(TensionNode(
                        id=str(uuid.uuid4()),
                        user_claim=f"High confidence level ({confidence}) in achieving career goals",
                        market_reality="No concrete skills or evidence have been captured yet to support this confidence level.",
                        tension_type="gap_vs_confidence",
                        severity=self.SEVERITY_MEDIUM,
                    ))

        return tensions

    def _detect_skill_gap_tensions(self, user_frame: dict, market_data: dict) -> list[TensionNode]:
        """Detect when user's skills are misaligned with market demands."""
        tensions = []
        skill_nodes = user_frame.get("nodes_by_type", {}).get("skill", [])
        user_skills = {n.get("label", "").lower() for n in skill_nodes}

        demanded = market_data.get("demanded_skills", []) or market_data.get("top_demanded_skills", [])
        if not demanded:
            return tensions

        demanded_lower = {s.lower() for s in demanded[:5]}

        # Check for complete mismatch
        overlap = user_skills & demanded_lower
        if user_skills and not overlap and len(demanded_lower) >= 3:
            tensions.append(TensionNode(
                id=str(uuid.uuid4()),
                user_claim=f"Current skills: {', '.join(s.capitalize() for s in list(user_skills)[:5])}",
                market_reality=f"Top demanded skills for target role: {', '.join(demanded[:5])}. Zero overlap detected.",
                tension_type="gap_vs_confidence",
                severity=self.SEVERITY_MEDIUM,
            ))

        return tensions

    def _detect_belief_tensions(self, user_frame: dict, market_data: dict) -> list[TensionNode]:
        """Detect factual contradictions between user beliefs and market data."""
        tensions = []
        
        # Check for market warnings that contradict user evidence
        warnings = market_data.get("market_warnings", [])
        evidence_nodes = user_frame.get("nodes_by_type", {}).get("evidence", [])
        
        for warning in warnings:
            warning_lower = str(warning).lower()
            for node in evidence_nodes:
                props = node.get("properties", {})
                projects = props.get("projects", [])
                if isinstance(projects, list):
                    for project in projects:
                        if isinstance(project, dict):
                            desc = str(project.get("description", "")).lower()
                            # Check if user's projects are in the "weak" category
                            if ("prompt-only" in warning_lower and "prompt" in desc) or \
                               ("notebook" in warning_lower and "notebook" in desc):
                                tensions.append(TensionNode(
                                    id=str(uuid.uuid4()),
                                    user_claim=f"Project: {project.get('name', 'Unnamed')} — {project.get('description', '')}",
                                    market_reality=warning,
                                    tension_type="fact_vs_belief",
                                    severity=self.SEVERITY_MEDIUM,
                                ))

        return tensions

    def _detect_feasibility_tensions(self, user_frame: dict, market_data: dict) -> list[TensionNode]:
        """Detect when constraints make the goal infeasible without adjustment."""
        tensions = []
        constraint_nodes = user_frame.get("nodes_by_type", {}).get("constraint", [])
        ambition_nodes = user_frame.get("nodes_by_type", {}).get("ambition", [])

        for constraint in constraint_nodes:
            props = constraint.get("properties", {})
            time_limit = props.get("time_limit", "")
            
            # Parse hours from time_limit string
            hours = 15  # default
            if isinstance(time_limit, str):
                digits = ''.join(c for c in time_limit if c.isdigit())
                if digits:
                    hours = int(digits)
            elif isinstance(time_limit, (int, float)):
                hours = int(time_limit)

            # Very limited time + ambitious goals = tension
            if hours < 8:
                for ambition in ambition_nodes:
                    dream_roles = ambition.get("properties", {}).get("dream_roles", [])
                    if isinstance(dream_roles, list) and dream_roles:
                        tensions.append(TensionNode(
                            id=str(uuid.uuid4()),
                            user_claim=f"Targeting {', '.join(dream_roles)} with {hours} hours/week",
                            market_reality=f"Competitive candidates typically invest 15-25 hours/week. {hours} hours/week significantly limits the speed of progress.",
                            tension_type="aspiration_vs_reality",
                            severity=self.SEVERITY_MEDIUM if hours >= 5 else self.SEVERITY_HIGH,
                        ))

        return tensions

    def _detect_answer_tensions(self, ingestion_answers: list[dict], market_data: dict) -> list[TensionNode]:
        """
        Detect tensions from raw ingestion answers.
        Uses LLM to analyze contradictions between answers and market data.
        """
        if not ingestion_answers or not market_data:
            return []

        # Only analyze if we have enough answers
        if len(ingestion_answers) < 2:
            return []

        answers_text = "\n".join([
            f"Q: {qa.get('question', '')}\nA: {qa.get('answer', '')}"
            for qa in ingestion_answers[-4:]  # Last 4 Q&A pairs
        ])

        market_text = json.dumps({
            "demanded_skills": market_data.get("demanded_skills", market_data.get("top_demanded_skills", [])),
            "market_warnings": market_data.get("market_warnings", []),
            "project_patterns": market_data.get("project_patterns", []),
        }, default=str)[:800]

        prompt = f"""Analyze these ingestion answers against market data. Find tensions/contradictions.

Answers:
{answers_text}

Market Data:
{market_text}

Return a JSON array of tensions (or empty array if none found). Each tension:
{{
    "user_claim": "What the user said or implied",
    "market_reality": "What the market data shows",
    "tension_type": "fact_vs_belief | aspiration_vs_reality | gap_vs_confidence",
    "severity": 0.5
}}

Only flag REAL tensions. Don't manufacture conflicts. Return [] if the answers are aligned with market reality."""

        try:
            response_text = generate_response(prompt)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            tension_dicts = json.loads(response_text.strip())
            if not isinstance(tension_dicts, list):
                return []

            return [
                TensionNode(
                    id=str(uuid.uuid4()),
                    user_claim=t.get("user_claim", ""),
                    market_reality=t.get("market_reality", ""),
                    tension_type=t.get("tension_type", "gap_vs_confidence"),
                    severity=min(1.0, max(0.1, float(t.get("severity", 0.5)))),
                )
                for t in tension_dicts
                if t.get("user_claim") and t.get("market_reality")
            ]

        except Exception as e:
            print(f"[TensionResolver] Answer tension detection failed: {e}")
            return []
