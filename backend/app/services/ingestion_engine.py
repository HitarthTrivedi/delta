"""
Ingestion Engine — Manages multi-round interactive intake and personal data bridging
for Delta's Cognitive Career Architect.
"""

import json
import logging
import uuid
import datetime
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
                from app.models.user import User
                user_obj = db.query(User).filter(User.id == user_id).first()
                name = user_obj.name if user_obj else "Student"
                email = user_obj.email if user_obj else ""
                graph.create_user_root_node(name, email)
                graph.save_to_db(db)

        # Create new session record
        session_id = str(uuid.uuid4())
        
        # Determine initial opening question based on journey type
        opening_prompt = f"""You are the Strategist agent. The user is embarking on a {journey_type} career journey.
Generate a warm, compelling, personalized opening question that invites them to share their current stage,
major ambitions, and any background.
Be encouraging, keep it under 50 words, and do NOT sound like a generic form. Ensure it is highly professional.
Return ONLY the question text."""
        
        initial_question = generate_response(opening_prompt).strip().strip('"').strip("'")
        
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
        
        # 3. Fact Extraction: Extract entities and edges from answer via LLM
        self._extract_entities_to_graph(graph, answer_content, session.journey_type)
        graph.save_to_db(db)

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

        # Check if ingestion has reached completion
        # Soft limit of 8 rounds or high confidence score with no missing critical gaps
        is_complete = analysis["is_complete"] or (session.current_round >= 8 and session.confidence_score >= 0.65)
        
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
        next_question = None
        dimension_focus = "cognitive"
        
        # Priority A: Address active, unresolved tensions (Show as challenge cards)
        unresolved_tensions = [t for t in active_tensions if t.status == "active"]
        if unresolved_tensions:
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
1. Skills/Capabilities they mention possessing (HAS_SKILL relation).
2. Ambitions/Dream roles/Goals they strive for (STRIVES_FOR relation).
3. Constraints/Limitations (time, finances, hardware) they mention (CONSTRAINED_BY relation).
4. Preferences (learning style, content type, communication) (PREFERS relation).
5. Evidence (completed projects, courses, credentials) (EVIDENCED_BY relation).
6. Motivations or fears (motivation, risk, fears) (FEARS or TRIGGERED_BY relation).

Return a strict JSON list of dictionaries:
[
  {{
    "node_type": "skill | ambition | constraint | preference | evidence | motivation",
    "label": "Short name of the entity",
    "dimension": "cognitive | emotional | temporal | social",
    "confidence": 0.8,
    "properties": {{
       "details": "Paraphrased specific statement or evidence from response",
       "proficiency": 1-10 (optional, if skill)
    }},
    "relation_type": "HAS_SKILL | STRIVES_FOR | CONSTRAINED_BY | PREFERS | EVIDENCED_BY"
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
