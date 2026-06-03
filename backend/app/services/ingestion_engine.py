"""
Ingestion Engine — Manages multi-round interactive intake and personal data bridging
for Delta's Cognitive Career Architect.
"""

import json
import logging
import uuid
import datetime
import pathlib
import re
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.semantic_memory import IngestionSession, TensionNodeModel, SemanticNodeModel
from app.services.memory_graph import MemoryGraph, SemanticNode, SemanticEdge
from app.services.ideal_frames import compute_confidence_and_gaps, PitfallDetector, get_ideal_frame
from app.services.tension_resolver import TensionResolver
from app.services.web_search import WebSearchService
from app.services.orchestrator import Orchestrator
from app.services.ai_service import generate_response

logger = logging.getLogger("delta.ingestion_engine")

class IngestionEngine:
    """
    Manages the multi-round onboarding conversation and existing profile data ingestion,
    updating the Semantic Memory Graph, resolving tensions, and identifying pitfalls.
    """

    def __init__(self):
        self.web_search = WebSearchService()
        self.orchestrator = Orchestrator()
        self.pitfall_detector = PitfallDetector()
        self.tension_resolver = TensionResolver()

    def start_session(self, db: Session, user_id: str, journey_type: str = "general") -> IngestionSession:
        """
        Initializes a new ingestion session, creates the user root node in the graph,
        and generates the opening onboarding question.
        """
        # Reset guest profile so they can enter fresh details
        from app.models.user import User
        user_obj = db.query(User).filter(User.id == user_id).first()
        if user_obj and user_id == "00000000-0000-0000-0000-000000000000":
            user_obj.name = "Guest User"
            user_obj.email = "guest@delta.dev"
            user_obj.target_role = ""
            user_obj.hours_per_week = 15
            user_obj.learning_style = "practical"
            db.commit()

        # Close any existing active sessions
        active_sessions = db.query(IngestionSession).filter(
            IngestionSession.user_id == user_id,
            IngestionSession.status == "active"
        ).all()
        for s in active_sessions:
            s.status = "paused"
        
        # Load or create graph
        graph = MemoryGraph.load_from_db(db, user_id)
        if not graph.get_user_root():
            user_record = db.query(SemanticNodeModel).filter(
                SemanticNodeModel.user_id == user_id, 
                SemanticNodeModel.node_type == "user"
            ).first()
            if user_record:
                # Root exists in DB, let load_from_db handle it
                pass
            else:
                # Retrieve actual user details from DB
                name = user_obj.name if user_obj else "Student"
                email = user_obj.email if user_obj else ""
                graph.create_user_root_node(name, email)
                graph.save_to_db(db)

        # Create new session record
        session_id = str(uuid.uuid4())
        
        initial_question = (
            "Hi, I am Delta's intake advisor. Before the resume, give me a small introduction in your own words: "
            "who you are, what you studied or worked on, why you are here, what goal or exam you are aiming for, "
            "and any deadline, intake, family constraint, or weekly time limit I should know. After that, attach your resume if you have one."
        )
        
        conversation = [
            {"role": "assistant", "content": initial_question, "dimension": "identity", "round": 0}
        ]

        session = IngestionSession(
            id=session_id,
            user_id=user_id,
            status="active",
            current_round=0,
            confidence_score=0.05,
            gaps_total=0,
            gaps_filled=0,
            tensions_total=0,
            tensions_resolved=0,
            journey_type=journey_type,
            conversation_log=json.dumps(conversation),
            market_context_used=json.dumps({}),
            created_at=datetime.datetime.utcnow()
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    def process_answer(self, db: Session, user_id: str, session_id: str, answer_content: str) -> Dict[str, Any]:
        """
        Processes a student's response, extracts facts/entities to the graph, resolves tensions,
        checks for pitfalls, calculates gaps and confidence, and generates the next Socratic question
        or finalizes the onboarding profile.
        """
        session = db.query(IngestionSession).filter(IngestionSession.id == session_id).first()
        if not session or session.status != "active":
            raise ValueError("Ingestion session not active or not found.")

        # 1. Update conversation log
        conversation = json.loads(session.conversation_log or "[]")
        
        # Determine dimension focus of the last question (defaults to cognitive)
        last_dimension = "cognitive"
        if conversation:
            last_dimension = conversation[-1].get("dimension", "cognitive")
            
        conversation.append({
            "role": "user",
            "content": answer_content,
            "dimension": last_dimension,
            "round": session.current_round
        })
        
        session.current_round += 1
        
        # 2. Load the student's Semantic Memory Graph
        graph = MemoryGraph.load_from_db(db, user_id)
        
        # 3. Fact Extraction: first capture common student facts deterministically,
        # then let the LLM add richer resume/profile details.
        profile_hints = self._extract_profile_hints(answer_content)
        self._extract_heuristic_intake_to_graph(graph, answer_content, profile_hints)
        self._extract_entities_to_graph(graph, answer_content, session.journey_type)
        graph.save_to_db(db)

        # 3b. User Profile Details Extraction: Update User table with extracted details if found
        from app.models.user import User
        user_obj = db.query(User).filter(User.id == user_id).first()
        if user_obj:
            self._apply_profile_hints(user_obj, profile_hints)
            profile_prompt = f"""Analyze the user message: "{answer_content}"
Identify if the user states their:
- name
- email
- target_role (dream career/role, e.g. "AI Software Engineer")
- learning_style (e.g. "practical", "theoretical", "competitive")
- hours_per_week (a number)
- place/location
- college
- current qualification/year
- future goals
- upcoming exams, deadlines, or blocked weeks

Return a JSON object with any of these fields that were explicitly or implicitly stated. If none are present, return {{}}.
Output ONLY valid JSON, nothing else."""
            try:
                profile_resp = generate_response(profile_prompt)
                if "```json" in profile_resp:
                    profile_resp = profile_resp.split("```json")[1].split("```")[0]
                elif "```" in profile_resp:
                    profile_resp = profile_resp.split("```")[1].split("```")[0]
                
                profile_data = json.loads(profile_resp.strip())
                if isinstance(profile_data, dict):
                    if "name" in profile_data and profile_data["name"] and not profile_hints.get("name"):
                        user_obj.name = str(profile_data["name"])
                    if "email" in profile_data and profile_data["email"]:
                        user_obj.email = str(profile_data["email"])
                    if "target_role" in profile_data and profile_data["target_role"]:
                        user_obj.target_role = str(profile_data["target_role"])
                    if "learning_style" in profile_data and profile_data["learning_style"]:
                        user_obj.learning_style = str(profile_data["learning_style"])
                    if "hours_per_week" in profile_data:
                        try:
                            user_obj.hours_per_week = int(profile_data["hours_per_week"])
                        except Exception:
                            pass
                    db.commit()
            except Exception as e:
                logger.error(f"Failed to extract profile updates: {e}")
            self._apply_profile_hints(user_obj, profile_hints)
            db.commit()

        # 4. Fetch Market Context (live web search) for their stated career ambitions/roles
        dream_roles = [node.label for node in graph.get_nodes_by_type("ambition")]
        target_role = dream_roles[0] if dream_roles else "Software Engineer"
        user_skills = [node.label for node in graph.get_nodes_by_type("skill")]
        
        market_pulse = self.web_search.search_for_market_pulse(
            target_role=target_role,
            user_skills=user_skills,
            user_location="India"
        )
        session.market_context_used = json.dumps(market_pulse)

        # 5. Detect and Update Tensions
        user_frame = graph.get_frame()
        detected_tensions = self.tension_resolver.detect_tensions(user_frame, market_pulse)
        
        # Run chat-based tension detection (to catch answer contradictions)
        chat_tensions = self.tension_resolver._detect_answer_tensions(conversation, market_pulse)
        detected_tensions.extend(chat_tensions)
        
        # Add new tensions to graph and DB
        active_tensions_in_db = db.query(TensionNodeModel).filter(
            TensionNodeModel.user_id == user_id,
            TensionNodeModel.status == "active"
        ).all()
        active_db_claims = {t.user_claim.lower() for t in active_tensions_in_db}
        
        for t in detected_tensions:
            if t.user_claim.lower() not in active_db_claims:
                # Add to DB
                db_tension = TensionNodeModel(
                    id=t.id,
                    user_id=user_id,
                    tension_type=t.tension_type,
                    user_claim=t.user_claim,
                    market_reality=t.market_reality,
                    severity=t.severity,
                    challenge_question=t.challenge_question,
                    status="active",
                    created_at=datetime.datetime.utcnow()
                )
                db.add(db_tension)
                
                # Add to memory graph
                graph.add_tension(
                    tension_id=t.id,
                    tension_type=t.tension_type,
                    user_claim=t.user_claim,
                    market_reality=t.market_reality,
                    severity=t.severity,
                    challenge_question=t.challenge_question
                )
        
        # Re-resolve/check active tensions
        for t_db in active_tensions_in_db:
            # Let the tension resolver check if user's latest response resolves this tension
            t_obj = self.tension_resolver.to_tension_node_obj(t_db)
            res_dict = self.tension_resolver.resolve(t_obj, answer_content)
            if res_dict.get("status") == "resolved":
                t_db.status = "resolved"
                t_db.resolution = res_dict.get("resolution")
                t_db.resolved_at = datetime.datetime.utcnow()
                graph.resolve_tension(t_db.id, res_dict.get("resolution", ""))
                session.tensions_resolved += 1

        db.commit()
        graph.save_to_db(db)

        # 6. Pitfall Detection
        profile_frame = graph.to_profile_frame()
        active_pitfalls = self.pitfall_detector.detect_pitfalls(profile_frame)
        ingestion_pitfalls = self.pitfall_detector.detect_during_ingestion(conversation, [c["content"] for c in conversation if c["role"] == "assistant"])
        active_pitfalls.extend(ingestion_pitfalls)

        # 7. Ingestion Gap & Confidence Assessment
        analysis = compute_confidence_and_gaps(session.journey_type, profile_frame)
        
        session.confidence_score = analysis["confidence_score"]
        session.gaps_total = len(analysis["missing_fields"])
        
        # Find active tensions count
        active_tensions = db.query(TensionNodeModel).filter(
            TensionNodeModel.user_id == user_id,
            TensionNodeModel.status == "active"
        ).all()
        session.tensions_total = db.query(TensionNodeModel).filter(TensionNodeModel.user_id == user_id).count()

        missing_intake_topics = self._missing_intake_topics(graph)

        # Agent 1 hands off as soon as it has the core fields Agent 2 needs.
        # It does not keep asking scripted questions just because optional ideal-frame gaps remain.
        is_complete = (session.current_round >= 1 and not missing_intake_topics) or session.current_round >= 7
        
        if is_complete:
            session.status = "completed"
            session.completed_at = datetime.datetime.utcnow()
            
            # Finalize Career Memory Profile snapshot in DB
            self._materialize_career_snapshot(db, user_id, graph, analysis["confidence_score"])
            
            db.commit()
            
            # Synthesize final onboarding summary response
            completion_prompt = f"""You are the Strategist. The user has successfully completed onboarding ingestion for the {session.journey_type} track!
Their confidence score is {analysis["confidence_score"] * 100}%.
Gaps remaining: {len(analysis['missing_fields'])}.
Active Pitfalls flagged: {[p['pitfall_type'] for p in active_pitfalls]}.
Current skills: {user_skills}.
Dream roles: {dream_roles}.

Write an incredibly inspiring, premium, high-fidelity onboarding wrap-up response.
1. Welcome them officially to Delta Career OS.
2. Outline their 'Digital Twin' profile strengths.
3. Call out their top 2 immediate focus skills.
4. Mention the Golden Path benchmark they will target for their year.
5. End with an energetic invitation to view their new interactive Roadmap!
Keep it professional, highly structured, and under 250 words."""

            final_msg = generate_response(completion_prompt).strip()
            conversation.append({
                "role": "assistant",
                "content": final_msg,
                "dimension": "identity",
                "round": session.current_round
            })
            session.conversation_log = json.dumps(conversation)
            db.commit()
            
            return {
                "status": "completed",
                "confidence_score": session.confidence_score,
                "message": final_msg,
                "active_pitfalls": active_pitfalls,
                "tensions": [self.tension_resolver.to_tension_node_obj(t).to_dict() for t in active_tensions],
                "gaps": analysis["missing_fields"],
                "conversation": conversation
            }

        # 8. Generate Next Question
        next_question = self._agent1_next_question(session.current_round, conversation, missing_intake_topics)
        dimension_focus = "temporal" if session.current_round in {4, 5} else "cognitive"
        
        # Priority A: Address active, unresolved tensions (Show as challenge cards)
        unresolved_tensions = [t for t in active_tensions if t.status == "active"]
        if not next_question and unresolved_tensions:
            # Pick highest severity active tension
            unresolved_tensions.sort(key=lambda x: x.severity, reverse=True)
            chosen_tension = unresolved_tensions[0]
            
            # Use Orchestrator debate loop to generate challenge response
            deliberation = self.orchestrator.deliberate(
                user_query=answer_content,
                graph_summary=graph.to_summary(),
                market_data=market_pulse,
                context={
                    "ingestion_round": session.current_round,
                    "tensions_remaining": len(unresolved_tensions),
                    "target_tension_claim": chosen_tension.user_claim,
                    "target_tension_reality": chosen_tension.market_reality
                },
                mode="ingestion"
            )
            next_question = deliberation.next_question or chosen_tension.challenge_question
            dimension_focus = deliberation.dimension_focus
            
            # Mark that tension has been challenged/posed
            chosen_tension.status = "active" # keep active but posed
        
        # Priority B: Fill missing critical fields
        if not next_question and analysis["missing_critical"]:
            missing_crit = analysis["missing_critical"][0]
            node_type, field_name = missing_crit.split(".")
            
            gap_item = {
                "node_type": node_type,
                "missing_fields": [field_name],
                "priority": 0.9,
                "label": f"Missing {field_name} details"
            }
            
            next_question = self.orchestrator.deliberate_for_question(
                gap=gap_item,
                graph_summary=graph.to_summary(),
                market_data=market_pulse,
                context={"ingestion_round": session.current_round}
            )
            dimension_focus = self._infer_dimension(node_type)

        # Priority C: Fill any other gaps
        if not next_question and analysis["missing_fields"]:
            missing_f = analysis["missing_fields"][0]
            node_type, field_name = missing_f.split(".")
            gap_item = {
                "node_type": node_type,
                "missing_fields": [field_name],
                "priority": 0.5,
                "label": f"Missing {field_name}"
            }
            next_question = self.orchestrator.deliberate_for_question(
                gap=gap_item,
                graph_summary=graph.to_summary(),
                market_data=market_pulse,
                context={"ingestion_round": session.current_round}
            )
            dimension_focus = self._infer_dimension(node_type)

        # Fallback question
        if not next_question:
            next_question = "Tell me about what project or tech stack you are currently most excited to build next."
            dimension_focus = "cognitive"

        # Append to log
        conversation.append({
            "role": "assistant",
            "content": next_question,
            "dimension": dimension_focus,
            "round": session.current_round
        })
        
        session.conversation_log = json.dumps(conversation)
        db.commit()

        return {
            "status": "active",
            "confidence_score": session.confidence_score,
            "message": next_question,
            "active_pitfalls": active_pitfalls,
            "tensions": [self.tension_resolver.to_tension_node_obj(t).to_dict() for t in active_tensions],
            "gaps": analysis["missing_fields"],
            "conversation": conversation
        }

    def _missing_intake_topics(self, graph: MemoryGraph) -> List[str]:
        nodes = graph.get_frame().get("nodes_by_type", {})

        def labels(node_type: str) -> list[str]:
            return [
                str(node.get("label", "")).lower()
                for node in nodes.get(node_type, [])
            ]

        identity_labels = labels("identity")
        ambition_labels = labels("ambition")
        skill_labels = labels("skill")
        evidence_labels = labels("evidence")
        constraint_labels = labels("constraint")
        preference_labels = labels("preference")
        all_constraints = " ".join(constraint_labels)

        missing = []
        if not identity_labels:
            missing.append("education_identity")
        if not ambition_labels:
            missing.append("goal_timeline")
        if not skill_labels and not evidence_labels:
            missing.append("skills_evidence")
        if not any(word in all_constraints for word in ["hour", "week", "time", "schedule", "availability"]):
            missing.append("weekly_availability")
        if not any(word in all_constraints for word in ["exam", "deadline", "blocked", "submission", "placement", "interview"]):
            missing.append("upcoming_calendar")
        if not preference_labels:
            missing.append("learning_preferences")
        return missing

    def _agent1_next_question(self, round_number: int, conversation: List[Dict[str, Any]], missing_topics: List[str]) -> Optional[str]:
        """Ask from missing evidence, not from a scripted sequence."""
        if not missing_topics:
            return None

        topic_questions = {
            "education_identity": "I could not confidently identify your college, degree/branch, and current year or semester. What are those details?",
            "goal_timeline": "What exact outcome should Delta optimize for, and by when? For example placements, masters in Germany, a role, research, GATE, or startup.",
            "skills_evidence": "Which skills, projects, internships, papers, certificates, GitHub links, or resume items are strongest proof of your current level?",
            "weekly_availability": "How many hours can you realistically give each week, and on which days?",
            "upcoming_calendar": "Are there exams, submissions, placement drives, interviews, or blocked weeks coming up in the next three months?",
            "learning_preferences": "How do you learn best: videos, docs, books, coaching, strict deadlines, peer study, or hands-on projects?",
        }
        base_question = topic_questions.get(missing_topics[0])
        if not base_question:
            return None

        recent_context = "\n".join(
            f"{msg.get('role')}: {str(msg.get('content', ''))[:1200]}"
            for msg in conversation[-5:]
        )
        latest_user = next((msg.get("content", "") for msg in reversed(conversation) if msg.get("role") == "user"), "")
        resume_hint = "resume" in latest_user.lower() or len(latest_user) > 1800

        prompt = f"""You are Agent 1 of Delta Career OS. You are an adaptive intake interviewer, not a static form.
Your job is to ask exactly ONE next question that gathers information for Agent 2's weekly plan.

CURRENT REQUIRED TOPIC:
{base_question}

MISSING TOPICS STILL NEEDED:
{", ".join(missing_topics)}

RECENT CONVERSATION / RESUME EXCERPT:
{recent_context}

Instructions:
1. Ask only one question.
2. If a resume or project evidence appears above, reference one concrete thing from it and ask the most important missing follow-up.
3. If the required topic was already answered, ask a sharper question that fills the next missing detail for weekly planning.
4. Keep it under 65 words.
5. Do not list all intake fields again.
6. Sound like a mentor, not a survey.

Return only the question."""
        try:
            adaptive_question = generate_response(prompt).strip().strip('"').strip("'")
            generic_failures = [
                "ask me about skills",
                "career journey",
                "learning path",
                "market trends",
            ]
            if adaptive_question and not any(text in adaptive_question.lower() for text in generic_failures):
                if resume_hint and "resume" not in adaptive_question.lower() and "project" not in adaptive_question.lower():
                    return f"I read the resume content. {adaptive_question}"
                return adaptive_question
        except Exception as exc:
            logger.warning(f"Agent 1 adaptive question generation failed: {exc}")
        return base_question

    def _extract_profile_hints(self, answer: str) -> Dict[str, Any]:
        """Extract boring-but-critical resume/profile facts without waiting on the LLM."""
        text = answer.strip()
        lines = [" ".join(line.strip().split()) for line in text.splitlines() if line.strip()]
        lower = text.lower()
        hints: Dict[str, Any] = {}

        email_match = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text)
        if email_match:
            hints["email"] = email_match.group(0)

        explicit_name = re.search(r"\b(?:my name is|i am|i'm|name\s*:)\s+([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){0,3})", text)
        if explicit_name:
            hints["name"] = explicit_name.group(1).strip()
        else:
            blocked = {
                "resume", "curriculum vitae", "cv", "education", "skills", "projects",
                "experience", "github", "linkedin", "email", "phone", "contact",
                "summary", "objective", "certifications", "achievements",
            }
            for line in lines[:8]:
                line_lower = line.lower()
                if any(word in line_lower for word in blocked):
                    continue
                if re.search(r"[@:/\\]|\d{3,}", line):
                    continue
                words = line.split()
                if 2 <= len(words) <= 4 and all(re.match(r"^[A-Za-z][A-Za-z.'-]*$", word) for word in words):
                    hints["name"] = line
                    break

        year_match = re.search(r"\b(1st|2nd|3rd|4th|first|second|third|fourth)\s+year[a-z]*\b", lower)
        sem_match = re.search(r"\b(?:sem|semester)\s*([1-8])\b|\b([1-8])(?:st|nd|rd|th)?\s+sem\b", lower)
        degree_match = re.search(r"\b(b\.?\s*tech|btech|bachelor|m\.?\s*tech|mtech|bca|mca|bsc|msc)\b", lower)
        branch_match = re.search(r"\b(cse|computer science|information technology|it|ece|mechanical|civil|electrical|ai|data science)\b", lower)
        college_match = re.search(r"\bat\s+([a-z0-9 .&'-]+?(?:college|university|institute|school|svit)(?:\s+college)?)\b", lower)
        location_match = re.search(r"\b(?:from|location\s*:|based in)\s+([A-Za-z][A-Za-z .,'-]{2,40})", text)
        hours_match = re.search(r"\b(\d{1,2})\s*(?:hours?|hrs?|h)\s*(?:/|per)?\s*(?:week|weekly)?\b", lower)

        if year_match:
            hints["year"] = f"{year_match.group(1)} year"
        if sem_match:
            hints["semester"] = sem_match.group(1) or sem_match.group(2)
        if degree_match:
            hints["degree"] = degree_match.group(1).replace(" ", "").upper()
        if branch_match:
            branch = branch_match.group(1)
            hints["branch"] = "CSE" if branch in {"cse", "computer science"} else branch.upper()
        if college_match:
            hints["college"] = college_match.group(1).strip().upper()
        if location_match:
            hints["location"] = location_match.group(1).strip(" .,")
        if hours_match:
            hints["hours_per_week"] = int(hours_match.group(1))

        role_patterns = [
            (r"\b(?:want to become|become|targeting|goal is|dream role is)\s+(?:an?\s+)?([A-Za-z /+-]{3,60})", "target_role"),
            (r"\b(?:masters?|ms)\s+(?:in|from|at)?\s*([A-Za-z /+-]{3,40})", "future_goal"),
        ]
        for pattern, key in role_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                hints[key] = match.group(1).strip(" .,\n")

        return hints

    def _apply_profile_hints(self, user_obj: Any, hints: Dict[str, Any]):
        if not hints:
            return
        name = hints.get("name")
        if name and (not user_obj.name or user_obj.name.lower() in {"guest user", "student", "unknown"}):
            user_obj.name = name
        if hints.get("email"):
            user_obj.email = hints["email"]
        if hints.get("target_role") and not user_obj.target_role:
            user_obj.target_role = hints["target_role"]
        elif hints.get("future_goal") and not user_obj.target_role:
            user_obj.target_role = hints["future_goal"]
        if hints.get("hours_per_week"):
            user_obj.hours_per_week = int(hints["hours_per_week"])

    def _extract_heuristic_intake_to_graph(self, graph: MemoryGraph, answer: str, profile_hints: Optional[Dict[str, Any]] = None):
        """Capture obvious intake facts even when the LLM extractor misses them."""
        text = answer.strip()
        lower = text.lower()
        profile_hints = profile_hints or self._extract_profile_hints(answer)

        existing = {
            (node.node_type, node.label.lower())
            for node in graph.get_nodes_by_type("identity")
            + graph.get_nodes_by_type("ambition")
            + graph.get_nodes_by_type("skill")
            + graph.get_nodes_by_type("constraint")
            + graph.get_nodes_by_type("preference")
            + graph.get_nodes_by_type("evidence")
        }

        def add(node_type: str, label: str, relation: str, dimension: str, confidence: float = 0.88):
            clean_label = " ".join(str(label).split()).strip(" ,.;")
            if not clean_label or (node_type, clean_label.lower()) in existing:
                return
            graph.add_entity_from_ingestion(
                node_type=node_type,
                label=clean_label,
                properties={"details": text[:1200], "source": "heuristic_intake"},
                relation_to_user=relation,
                dimension=dimension,
                source="heuristic_intake",
                confidence=confidence,
            )
            existing.add((node_type, clean_label.lower()))

        if profile_hints.get("name"):
            add("identity", f"Name: {profile_hints['name']}", "HAS_IDENTITY", "social", 0.95)
        if profile_hints.get("email"):
            add("identity", f"Email: {profile_hints['email']}", "HAS_IDENTITY", "social", 0.95)
        if profile_hints.get("location"):
            add("identity", f"Location: {profile_hints['location']}", "HAS_IDENTITY", "social", 0.9)

        if any(profile_hints.get(key) for key in ["year", "semester", "degree", "branch", "college"]):
            parts = []
            if profile_hints.get("year"):
                parts.append(profile_hints["year"])
            if profile_hints.get("degree"):
                parts.append(profile_hints["degree"])
            if profile_hints.get("branch"):
                parts.append(profile_hints["branch"])
            if profile_hints.get("college"):
                parts.append(f"at {profile_hints['college']}")
            if profile_hints.get("semester"):
                parts.append(f"semester {profile_hints['semester']}")
            add("identity", "Education: " + ", ".join(parts), "HAS_IDENTITY", "cognitive", 0.95)

        if profile_hints.get("hours_per_week"):
            add("constraint", f"{profile_hints['hours_per_week']} hours per week", "CONSTRAINED_BY", "temporal", 0.95)

        if any(word in lower for word in ["exam", "exams", "deadline", "submission", "interview", "placement", "blocked"]):
            add("constraint", f"Calendar constraint: {text[:160]}", "CONSTRAINED_BY", "temporal", 0.9)

        if any(word in lower for word in ["masters", "germany", "placement", "startup", "gate", "research", "internship"]):
            add("ambition", f"Goal: {text[:180]}", "STRIVES_FOR", "cognitive", 0.86)

        if any(word in lower for word in ["project", "github", "internship", "certificate", "paper", "resume"]):
            add("evidence", f"Evidence mentioned: {text[:180]}", "EVIDENCED_BY", "social", 0.82)

        if any(word in lower for word in ["video", "docs", "book", "hands-on", "project-based", "coaching", "peer", "deadline"]):
            add("preference", f"Learning preference: {text[:160]}", "PREFERS", "cognitive", 0.82)

    def ingest_personal_data(self, db: Session, user_id: str, raw_text: str, source: str = "linkedin") -> Dict[str, Any]:
        """
        The Personal Data Bridge. Parses raw text from resumes/LinkedIn, infers structural
        attributes, and populates the student's Career Knowledge Graph directly.
        """
        graph = MemoryGraph.load_from_db(db, user_id)
        if not graph.get_user_root():
            from app.models.user import User
            user_obj = db.query(User).filter(User.id == user_id).first()
            name = user_obj.name if user_obj else "Student"
            graph.create_user_root_node(name, user_obj.email if user_obj else "")
            graph.save_to_db(db)

        profile_hints = self._extract_profile_hints(raw_text)
        self._extract_heuristic_intake_to_graph(graph, raw_text, profile_hints)
        try:
            from app.models.user import User
            user_obj = db.query(User).filter(User.id == user_id).first()
            if user_obj:
                self._apply_profile_hints(user_obj, profile_hints)
                db.commit()
        except Exception as exc:
            logger.warning(f"Could not apply profile hints during data bridge: {exc}")

        # Create structured entities via LLM
        prompt = f"""You are Delta Profile Intelligence, an expert CV parser and career persona extractor.
We need to parse raw {source} text and convert it into structured vertices for our career knowledge graph.

RAW TEXT:
\"\"\"{raw_text}\"\"\"

Extract and output a strict JSON list of entity node dictionaries. Each dictionary must follow this shape:
{{
    "node_type": "identity | ambition | skill | constraint | preference | motivation | evidence",
    "label": "Short, human-readable name (e.g. 'FastAPI', 'AWS Certified', 'Time limit', 'Data Scientist')",
    "dimension": "cognitive | emotional | temporal | social",
    "confidence": 0.0 - 1.0 (how sure you are),
    "properties": {{
        "detail": "Any specific textual evidence or values",
        "proficiency": 1-10 (for skill),
        "source": "{source}_import"
    }},
    "relation_to_user": "STRIVES_FOR | HAS_SKILL | CONSTRAINED_BY | PREFERS | EVIDENCED_BY | FEARS"
}}

Rules:
1. Extract at least 4-8 high-fidelity nodes representing their actual background.
2. Be precise. If they have Python, list it as a skill with properties. If they completed a project, list it as evidence.
3. Output ONLY valid, parsable JSON, nothing else."""

        try:
            resp_text = generate_response(prompt)
            if "```json" in resp_text:
                resp_text = resp_text.split("```json")[1].split("```")[0]
            elif "```" in resp_text:
                resp_text = resp_text.split("```")[1].split("```")[0]

            nodes = json.loads(resp_text.strip())
            
            for item in nodes:
                node_type = item.get("node_type")
                label = item.get("label")
                properties = item.get("properties") or {}
                dimension = item.get("dimension", "cognitive")
                confidence = float(item.get("confidence", 0.7))
                relation = item.get("relation_to_user", "HAS_SKILL")

                # Add entity to graph
                graph.add_entity_from_ingestion(
                    node_type=node_type,
                    label=label,
                    properties=properties,
                    dimension=dimension,
                    source=f"{source}_import",
                    confidence=confidence,
                    relation_to_user=relation
                )

            graph.save_to_db(db)
            
            # Return updated status
            user_frame = graph.to_profile_frame()
            analysis = compute_confidence_and_gaps("general", user_frame)
            self._materialize_career_snapshot(db, user_id, graph, analysis["confidence_score"])
            db.commit()

            return {
                "success": True,
                "nodes_imported": len(nodes),
                "confidence_score": analysis["confidence_score"],
                "gaps_remaining": len(analysis["missing_fields"]),
                "imported_nodes_labels": [n.get("label") for n in nodes]
            }

        except Exception as e:
            logger.error(f"Personal Data Bridge failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _extract_entities_to_graph(self, graph: MemoryGraph, answer: str, journey_type: str):
        """
        Uses LLM to dynamically extract entity nodes and relations from a user response,
        then injects them into the student's memory graph.
        """
        prompt = f"""You are the Librarian agent. Analyze the user's latest conversation response and extract
any structural entities related to their career profile on the {journey_type} track.

USER RESPONSE:
"{answer}"

Extract:
1. Identity context: place/location, college, current qualification/year, language comfort, background (node_type identity, relation HAS_IDENTITY).
2. Skills/Capabilities they mention possessing (node_type skill, relation HAS_SKILL).
3. Ambitions/Dream roles/Goals they strive for, including masters abroad or long-range targets (node_type ambition, relation STRIVES_FOR).
4. Constraints/Limitations: weekly hours, exams, deadlines, blocked weeks, finances, hardware, college load (node_type constraint, relation CONSTRAINED_BY).
5. Preferences: learning style, content type, communication, project taste (node_type preference, relation PREFERS).
6. Evidence: completed projects, courses, credentials, resume facts, GitHub, portfolio (node_type evidence, relation EVIDENCED_BY).
7. Motivations or fears: family pressure, risk, confidence, reasons for the goal (node_type motivation, relation MOTIVATED_BY or FEARS).

Return a strict JSON list of dictionaries:
[
  {{
    "node_type": "identity | skill | ambition | constraint | preference | evidence | motivation",
    "label": "Short name of the entity",
    "dimension": "cognitive | emotional | temporal | social",
    "confidence": 0.8,
    "properties": {{
       "details": "Paraphrased specific statement or evidence from response",
       "proficiency": 1-10 (optional, if skill)
    }},
    "relation_type": "HAS_IDENTITY | HAS_SKILL | STRIVES_FOR | CONSTRAINED_BY | PREFERS | EVIDENCED_BY | MOTIVATED_BY | FEARS"
  }}
]

Output ONLY the JSON list, no explanation."""

        try:
            resp_text = generate_response(prompt)
            if "```json" in resp_text:
                resp_text = resp_text.split("```json")[1].split("```")[0]
            elif "```" in resp_text:
                resp_text = resp_text.split("```")[1].split("```")[0]

            nodes = json.loads(resp_text.strip())
            for item in nodes:
                graph.add_entity_from_ingestion(
                    node_type=item.get("node_type"),
                    label=item.get("label"),
                    properties=item.get("properties") or {},
                    dimension=item.get("dimension", "cognitive"),
                    source="ingestion",
                    confidence=float(item.get("confidence", 0.7)),
                    relation_to_user=item.get("relation_type") or item.get("relation_to_user", "HAS_SKILL")
                )
        except Exception as e:
            logger.error(f"Failed to extract entities from answer: {e}")

    def _materialize_career_snapshot(self, db: Session, user_id: str, graph: MemoryGraph, score: float):
        """
        Materializes the graph's contents into the legacy flat CareerMemoryProfile database table,
        acting as a bridge so downstream modules (Roadmap, Project Recommendation) still function.
        Also writes a human-readable JSON profile file to disk for other agents to consume.
        """
        from app.models.career_os import CareerMemoryProfile
        
        profile = db.query(CareerMemoryProfile).filter(CareerMemoryProfile.user_id == user_id).first()
        if not profile:
            profile = CareerMemoryProfile(
                id=str(uuid.uuid4()),
                user_id=user_id,
                created_at=datetime.datetime.utcnow()
            )
            db.add(profile)

        frame = graph.to_profile_frame()
        
        # Populate JSON columns
        profile.identity = json.dumps(frame.get("identity", {}))
        profile.ambitions = json.dumps(frame.get("ambition", {}))
        profile.capabilities = json.dumps(frame.get("capability", {}))
        profile.constraints = json.dumps(frame.get("constraint", {}))
        profile.preferences = json.dumps(frame.get("preference", {}))
        profile.behavior = json.dumps(frame.get("motivation", {}))
        profile.evidence = json.dumps(frame.get("evidence", {}))
        
        # Update metadata
        profile.confidence_score = score
        profile.graph_version += 1
        
        # Populate active tensions list
        active_t_nodes = [t.id for t in graph.get_active_tensions()]
        profile.tension_nodes = json.dumps(active_t_nodes)
        profile.updated_at = datetime.datetime.utcnow()

        # ── Write human-readable profile JSON file for other agents ──
        try:
            from app.models.user import User
            user_obj = db.query(User).filter(User.id == user_id).first()
            profile_export = {
                "user_id": user_id,
                "name": getattr(user_obj, 'name', 'Unknown') if user_obj else 'Unknown',
                "email": getattr(user_obj, 'email', '') if user_obj else '',
                "target_role": getattr(user_obj, 'target_role', '') if user_obj else '',
                "hours_per_week": getattr(user_obj, 'hours_per_week', 10) if user_obj else 10,
                "learning_style": getattr(user_obj, 'learning_style', 'practical') if user_obj else 'practical',
                "confidence_score": score,
                "last_updated": datetime.datetime.utcnow().isoformat() + 'Z',
                "identity": frame.get("identity", {}),
                "ambitions": frame.get("ambition", {}),
                "capabilities": frame.get("capability", {}),
                "constraints": frame.get("constraint", {}),
                "preferences": frame.get("preference", {}),
                "motivations": frame.get("motivation", {}),
                "evidence": frame.get("evidence", {}),
                "active_tensions": [t.id for t in graph.get_active_tensions()],
            }
            # Write to <project_root>/data/profiles/<user_id>.json
            profiles_dir = pathlib.Path(__file__).resolve().parents[3] / "data" / "profiles"
            profiles_dir.mkdir(parents=True, exist_ok=True)
            profile_path = profiles_dir / f"{user_id}.json"
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(profile_export, f, indent=2, ensure_ascii=False)
            logger.info(f"Profile snapshot written to {profile_path}")
        except Exception as e:
            logger.warning(f"Could not write profile JSON file: {e}")

    def _infer_dimension(self, node_type: str) -> str:
        """Helper to map a node type to its corresponding cognitive dimension."""
        mapping = {
            "identity": "identity",
            "ambition": "cognitive",
            "capability": "cognitive",
            "constraint": "temporal",
            "preference": "cognitive",
            "motivation": "emotional",
            "evidence": "social"
        }
        return mapping.get(node_type, "cognitive")
