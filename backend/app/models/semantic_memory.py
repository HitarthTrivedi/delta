"""
Semantic Memory Models — Graph-vector memory layer for delta's cognitive architecture.

This module defines the SQLAlchemy models that power delta's semantic knowledge graph:
- SemanticNodeModel: Vertices in the user's career knowledge graph (skills, ambitions, constraints, etc.)
- SemanticEdgeModel: Typed, weighted relationships between semantic nodes
- TensionNodeModel: Detected contradictions between user beliefs and market reality
- IngestionSession: Tracks multi-round career profile ingestion conversations
"""

from sqlalchemy import Column, String, Float, Text, DateTime, LargeBinary, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.database import Base
import datetime


class SemanticNodeModel(Base):
    """A vertex in the user's career semantic graph.

    Each node represents a discrete concept in the user's career profile —
    a skill they possess, an ambition they hold, a constraint they face, etc.

    Nodes carry an optional embedding vector for similarity search and an
    activation weight that decays over time (W_t = W_0 * e^(-λ*t)) so that
    stale information naturally loses influence.

    Attributes:
        id: UUID primary key.
        user_id: Foreign key to the owning user.
        node_type: Semantic category — one of: user, ambition, skill, constraint,
                   evidence, market_signal, tension, preference, motivation, identity.
        label: Human-readable short name for the node.
        properties: JSON dict of node-specific data (schema varies by node_type).
        embedding: Serialized numpy float32 array (ndarray.tobytes()) for vector search.
        activation_weight: Temporal decay weight, initialized to 1.0.
        dimension: Cognitive dimension this node belongs to — cognitive, emotional,
                   temporal, or social.
        source: Provenance tag — ingestion, market_pulse, inference, or user_update.
        confidence: System confidence in this node's accuracy (0.0–1.0).
        access_count: Number of times this node has been retrieved / used.
        created_at: Timestamp of node creation.
        last_accessed: Timestamp of most recent access (used for decay calculation).
    """

    __tablename__ = "semantic_nodes"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    node_type = Column(String, nullable=False)  # user, ambition, skill, constraint, evidence, market_signal, tension, preference, motivation, identity
    label = Column(String, nullable=False)
    properties = Column(Text, nullable=True)  # JSON dict of node-specific data
    embedding = Column(LargeBinary, nullable=True)  # numpy float32 array, tobytes() serialized
    activation_weight = Column(Float, default=1.0)  # Temporal decay: W_t = W_0 * e^(-λ*t)
    dimension = Column(String, default="cognitive")  # cognitive, emotional, temporal, social
    source = Column(String, nullable=True)  # Where this node came from: ingestion, market_pulse, inference, user_update
    confidence = Column(Float, default=0.5)  # How confident the system is in this node's accuracy
    access_count = Column(Integer, default=0)  # How many times this node has been accessed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")

    # Edges where this node is the source
    outgoing_edges = relationship(
        "SemanticEdgeModel",
        foreign_keys="SemanticEdgeModel.source_id",
        back_populates="source_node",
    )
    # Edges where this node is the target
    incoming_edges = relationship(
        "SemanticEdgeModel",
        foreign_keys="SemanticEdgeModel.target_id",
        back_populates="target_node",
    )


class SemanticEdgeModel(Base):
    """A typed, weighted, directed edge between two SemanticNodeModel vertices.

    Edges encode the relationships that give the semantic graph its meaning —
    e.g. a user STRIVES_FOR an ambition, HAS_SKILL for a capability, or is
    CONSTRAINED_BY a life circumstance.

    Attributes:
        id: UUID primary key.
        user_id: Foreign key to the owning user.
        source_id: Foreign key to the source SemanticNodeModel.
        target_id: Foreign key to the target SemanticNodeModel.
        relation_type: Edge label — one of: STRIVES_FOR, HAS_SKILL, CONSTRAINED_BY,
                       PREFERS, EVIDENCED_BY, FEARS, CONFLICTS_WITH, DERIVED_FROM,
                       INFERRED_AS, TRIGGERED_BY.
        properties: JSON dict of edge-specific metadata.
        weight: Numeric strength / confidence of this relationship.
        created_at: Timestamp of edge creation.
    """

    __tablename__ = "semantic_edges"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    source_id = Column(String, ForeignKey("semantic_nodes.id"), nullable=False)
    target_id = Column(String, ForeignKey("semantic_nodes.id"), nullable=False)
    relation_type = Column(String, nullable=False)  # STRIVES_FOR, HAS_SKILL, CONSTRAINED_BY, PREFERS, EVIDENCED_BY, FEARS, CONFLICTS_WITH, DERIVED_FROM, INFERRED_AS, TRIGGERED_BY
    properties = Column(Text, nullable=True)  # JSON dict of edge-specific data
    weight = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")
    source_node = relationship("SemanticNodeModel", foreign_keys=[source_id], back_populates="outgoing_edges")
    target_node = relationship("SemanticNodeModel", foreign_keys=[target_id], back_populates="incoming_edges")


class TensionNodeModel(Base):
    """A detected contradiction between a user's stated beliefs and market reality.

    Tensions are first-class objects in the graph — they represent gaps where
    what the user *thinks* diverges from what the data *shows*.  The system
    generates a challenge question to surface the conflict and tracks whether
    the user resolves, dismisses, or ignores it.

    Attributes:
        id: UUID primary key.
        user_id: Foreign key to the owning user.
        source_belief_node_id: Optional link to the SemanticNode representing
                               the user belief that created the tension.
        tension_type: Category — fact_vs_belief, aspiration_vs_reality, or
                      gap_vs_confidence.
        user_claim: Verbatim or paraphrased statement from the user.
        market_reality: Contradicting evidence from market data.
        severity: Magnitude of the contradiction (0.0–1.0).
        challenge_question: Auto-generated Socratic question to surface the tension.
        resolution: How the tension was eventually resolved (null until resolved).
        status: Lifecycle state — active → challenged → resolved | dismissed.
        created_at: Timestamp of detection.
        resolved_at: Timestamp of resolution (null while active).
    """

    __tablename__ = "tension_nodes"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    source_belief_node_id = Column(String, ForeignKey("semantic_nodes.id"), nullable=True)
    tension_type = Column(String, nullable=False)  # fact_vs_belief, aspiration_vs_reality, gap_vs_confidence
    user_claim = Column(Text, nullable=False)  # What the user said
    market_reality = Column(Text, nullable=False)  # What the market shows
    severity = Column(Float, default=0.5)  # 0.0 - 1.0
    challenge_question = Column(Text, nullable=True)  # The question generated to surface the conflict
    resolution = Column(Text, nullable=True)  # How it was resolved (null until resolved)
    status = Column(String, default="active")  # active, challenged, resolved, dismissed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    user = relationship("User")


class IngestionSession(Base):
    """Tracks a multi-round career-profile ingestion conversation.

    During ingestion, the system asks progressively deeper questions across
    cognitive dimensions, identifies knowledge gaps, and detects tensions.
    This model persists the full session state so that ingestion can be
    paused, resumed, or analysed after completion.

    Attributes:
        id: UUID primary key.
        user_id: Foreign key to the owning user.
        status: Session lifecycle — active, paused, completed, or abandoned.
        current_round: Zero-indexed round counter.
        confidence_score: Aggregate ingestion confidence (0.0–1.0).
        gaps_total: Number of knowledge gaps identified so far.
        gaps_filled: Number of gaps that have been resolved.
        tensions_total: Number of tensions detected during ingestion.
        tensions_resolved: Number of tensions resolved during ingestion.
        journey_type: Detected career archetype (e.g. software_engineering, data_science).
        conversation_log: JSON array of {role, content, dimension, round} entries.
        market_context_used: JSON snapshot of market data referenced during ingestion.
        created_at: Timestamp of session start.
        completed_at: Timestamp of session completion (null while in progress).
    """

    __tablename__ = "ingestion_sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String, default="active")  # active, paused, completed, abandoned
    current_round = Column(Integer, default=0)
    confidence_score = Column(Float, default=0.0)  # Overall ingestion confidence 0-1
    gaps_total = Column(Integer, default=0)  # Total gaps identified
    gaps_filled = Column(Integer, default=0)  # Gaps resolved so far
    tensions_total = Column(Integer, default=0)
    tensions_resolved = Column(Integer, default=0)
    journey_type = Column(String, nullable=True)  # e.g., software_engineering, data_science, quant_dev
    conversation_log = Column(Text, nullable=True)  # JSON array of {role, content, dimension, round}
    market_context_used = Column(Text, nullable=True)  # JSON of market data used during ingestion
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User")
