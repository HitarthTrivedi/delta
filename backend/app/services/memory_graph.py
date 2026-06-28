"""
Memory Graph Service — The core cognitive memory engine for delta.

This is the heart of the GraphRAG architecture. Instead of storing user data as flat JSON
columns, this module creates a living semantic graph where:
  - Entities (skills, ambitions, constraints) are NODES with vector embeddings
  - Relationships (STRIVES_FOR, HAS_SKILL, CONSTRAINED_BY) are EDGES with weights
  - Temporal decay ensures current priorities surface over old ones
  - Multi-dimensional framing tracks cognitive, emotional, temporal, and social aspects

The graph lives in-process (networkx) for fast traversal, with SQLite persistence
via SemanticNodeModel/SemanticEdgeModel. Vector embeddings enable semantic similarity
search ("find everything related to healthcare regulations") while graph traversal
enables relationship navigation ("Who is the user? → What is their goal?").
"""

import datetime
import json
import math
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional

import networkx as nx
import numpy as np
from sqlalchemy.orm import Session

_embedding_model = "MOCK"  # sentence-transformers removed — too heavy for 512MB Render free tier
_EMBEDDING_DIM = 384


def _get_embedding_model():
    return _embedding_model


def _compute_embedding(text: str) -> np.ndarray:
    """Compute a vector embedding for a text string.

    Embeddings are deterministic, so we cache them by text hash to avoid
    recomputing the (CPU-heavy) encode pass for repeated strings.
    """
    model = _get_embedding_model()
    if model == "MOCK":
        # Deterministic mock: hash the text to get a reproducible vector
        np.random.seed(hash(text) % (2**32))
        return np.random.randn(_EMBEDDING_DIM).astype(np.float32)

    from app.services.cache import cache_get, cache_set
    cached_vec = cache_get("embedding", text)
    if cached_vec is not None:
        return np.array(cached_vec, dtype=np.float32)

    vec = model.encode(text, normalize_embeddings=True).astype(np.float32)
    cache_set("embedding", text, vec.tolist(), ttl=2592000)  # 30 days
    return vec


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


# ─── Data Classes ────────────────────────────────────────────────────────────

# Relation types for semantic edges
RELATION_TYPES = {
    "HAS_IDENTITY",     # User → Identity
    "STRIVES_FOR",      # User → Ambition
    "HAS_SKILL",        # User → Skill
    "CONSTRAINED_BY",   # User → Constraint
    "PREFERS",          # User → Preference
    "EVIDENCED_BY",     # Skill → Evidence
    "FEARS",            # User → Risk/Fear
    "CONFLICTS_WITH",   # Belief → Market Reality (Tension)
    "DERIVED_FROM",     # Inference → Source Data
    "INFERRED_AS",      # Raw Data → Inferred Classification
    "TRIGGERED_BY",     # Pitfall → Behavioral Pattern
    "MOTIVATED_BY",     # User → Motivation
    "BELONGS_TO",       # Skill → Category/Domain
    "REQUIRES",         # Ambition → Skill
    "BLOCKS",           # Constraint → Skill/Ambition
    "SUPERSEDES",       # New Data → Old Data
}

NODE_TYPES = {
    "user",          # The root user node
    "identity",      # Education, location, background
    "ambition",      # Goals, dream roles, target industries
    "capability",    # Aggregated skill/proficiency baseline
    "skill",         # Individual skills with proficiency
    "constraint",    # Time, money, devices, college load
    "preference",    # Learning style, content type, tone
    "motivation",    # What drives them
    "evidence",      # Projects, certs, GitHub, portfolio
    "market_signal", # External market data
    "tension",       # Conflicts between belief and reality
    "pitfall",       # Detected behavioral traps
    "inference",     # AI-derived conclusions
    "gap",           # Identified missing capabilities
}

DIMENSIONS = {"cognitive", "emotional", "temporal", "social"}


@dataclass
class SemanticNode:
    """A node in the semantic memory graph."""
    id: str
    node_type: str
    label: str
    properties: dict = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None
    activation_weight: float = 1.0
    dimension: str = "cognitive"
    source: str = "ingestion"
    confidence: float = 0.5
    access_count: int = 0
    created_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    last_accessed: datetime.datetime = field(default_factory=datetime.datetime.utcnow)

    def to_dict(self) -> dict:
        """Serialize for API responses (excludes embedding bytes)."""
        return {
            "id": self.id,
            "node_type": self.node_type,
            "label": self.label,
            "properties": self.properties,
            "activation_weight": self.activation_weight,
            "dimension": self.dimension,
            "source": self.source,
            "confidence": self.confidence,
            "access_count": self.access_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
        }


@dataclass
class SemanticEdge:
    """An edge (relationship) in the semantic memory graph."""
    id: str
    source_id: str
    target_id: str
    relation_type: str
    properties: dict = field(default_factory=dict)
    weight: float = 1.0
    created_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "properties": self.properties,
            "weight": self.weight,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ─── Memory Graph ────────────────────────────────────────────────────────────


class MemoryGraph:
    """
    The living semantic memory graph for a single user.
    
    Backed by networkx.DiGraph for fast traversal, with vector embeddings
    stored on each node for semantic similarity search.
    
    Usage:
        graph = MemoryGraph(user_id="123")
        graph.add_node(SemanticNode(id="n1", node_type="skill", label="Python", ...))
        graph.add_node(SemanticNode(id="n2", node_type="ambition", label="AI Engineer", ...))
        graph.add_edge(SemanticEdge(id="e1", source_id="n1", target_id="n2", relation_type="REQUIRES"))
        
        # Find semantically similar nodes
        results = graph.similarity_search("machine learning frameworks", top_k=5)
        
        # Traverse relationships
        skills = graph.traverse_path("user_root", "HAS_SKILL", depth=1)
        
        # Detect gaps against ideal frame
        gaps = graph.get_gaps(ideal_frame)
    """

    # Temporal decay constant (lambda). Higher = faster forgetting.
    DECAY_LAMBDA = 0.01  # ~1% decay per day

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.graph = nx.DiGraph()
        self._nodes: dict[str, SemanticNode] = {}
        self._edges: dict[str, SemanticEdge] = {}
        self._embeddings: dict[str, np.ndarray] = {}  # node_id → embedding

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    # ── Node/Edge Operations ──────────────────────────────────────────────

    def add_node(self, node: SemanticNode, compute_embedding: bool = True) -> SemanticNode:
        """
        Add a semantic node to the graph.
        
        If compute_embedding is True, generates a vector embedding from the node's
        label + properties for semantic search capability.
        """
        if node.node_type not in NODE_TYPES:
            raise ValueError(f"Invalid node_type: {node.node_type}. Must be one of {NODE_TYPES}")
        if node.dimension not in DIMENSIONS:
            raise ValueError(f"Invalid dimension: {node.dimension}. Must be one of {DIMENSIONS}")

        # Compute embedding from label + key properties
        if compute_embedding and node.embedding is None:
            embed_text = f"{node.node_type}: {node.label}"
            if node.properties:
                # Include top-level property values for richer embedding
                prop_text = " ".join(
                    str(v) for v in node.properties.values()
                    if isinstance(v, str) and len(str(v)) < 200
                )
                embed_text = f"{embed_text}. {prop_text}"
            node.embedding = _compute_embedding(embed_text)

        self._nodes[node.id] = node
        self.graph.add_node(node.id, **node.to_dict())
        if node.embedding is not None:
            self._embeddings[node.id] = node.embedding
        return node

    def add_edge(self, edge: SemanticEdge) -> SemanticEdge:
        """Add a semantic edge (relationship) between two nodes."""
        if edge.source_id not in self._nodes:
            raise ValueError(f"Source node {edge.source_id} not found in graph")
        if edge.target_id not in self._nodes:
            raise ValueError(f"Target node {edge.target_id} not found in graph")
        if edge.relation_type not in RELATION_TYPES:
            raise ValueError(f"Invalid relation_type: {edge.relation_type}. Must be one of {RELATION_TYPES}")

        self._edges[edge.id] = edge
        self.graph.add_edge(
            edge.source_id, edge.target_id,
            id=edge.id,
            relation_type=edge.relation_type,
            weight=edge.weight,
            properties=edge.properties,
        )
        return edge

    def get_node(self, node_id: str) -> Optional[SemanticNode]:
        """Retrieve a node by ID, updating its access metadata."""
        node = self._nodes.get(node_id)
        if node:
            node.last_accessed = datetime.datetime.utcnow()
            node.access_count += 1
            # Reinforcement: accessing a node resets its decay
            node.activation_weight = min(1.0, node.activation_weight + 0.1)
        return node

    def get_nodes_by_type(self, node_type: str) -> list[SemanticNode]:
        """Get all nodes of a specific type."""
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def get_edges_from(self, node_id: str, relation_type: Optional[str] = None) -> list[SemanticEdge]:
        """Get all outgoing edges from a node, optionally filtered by relation type."""
        edges = [e for e in self._edges.values() if e.source_id == node_id]
        if relation_type:
            edges = [e for e in edges if e.relation_type == relation_type]
        return edges

    def get_edges_to(self, node_id: str, relation_type: Optional[str] = None) -> list[SemanticEdge]:
        """Get all incoming edges to a node, optionally filtered by relation type."""
        edges = [e for e in self._edges.values() if e.target_id == node_id]
        if relation_type:
            edges = [e for e in edges if e.relation_type == relation_type]
        return edges

    def remove_node(self, node_id: str):
        """Remove a node and all its connected edges."""
        if node_id in self._nodes:
            del self._nodes[node_id]
            self._embeddings.pop(node_id, None)
            # Remove connected edges
            to_remove = [
                eid for eid, e in self._edges.items()
                if e.source_id == node_id or e.target_id == node_id
            ]
            for eid in to_remove:
                del self._edges[eid]
            if self.graph.has_node(node_id):
                self.graph.remove_node(node_id)

    def update_node_properties(self, node_id: str, properties: dict):
        """Merge new properties into an existing node, re-computing embedding."""
        node = self._nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")
        node.properties.update(properties)
        node.last_accessed = datetime.datetime.utcnow()
        # Recompute embedding with updated properties
        embed_text = f"{node.node_type}: {node.label}"
        prop_text = " ".join(
            str(v) for v in node.properties.values()
            if isinstance(v, str) and len(str(v)) < 200
        )
        embed_text = f"{embed_text}. {prop_text}"
        node.embedding = _compute_embedding(embed_text)
        self._embeddings[node_id] = node.embedding

    # ── Semantic Search ───────────────────────────────────────────────────

    def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        node_type_filter: Optional[str] = None,
        min_activation: float = 0.1,
    ) -> list[tuple[SemanticNode, float]]:
        """
        Find nodes semantically similar to a query string.
        
        Returns list of (node, similarity_score) tuples sorted by relevance,
        filtered by minimum activation weight.
        """
        query_embedding = _compute_embedding(query)
        results = []

        for node_id, embedding in self._embeddings.items():
            node = self._nodes.get(node_id)
            if not node:
                continue
            if node.activation_weight < min_activation:
                continue
            if node_type_filter and node.node_type != node_type_filter:
                continue

            sim = _cosine_similarity(query_embedding, embedding)
            # Weight similarity by activation weight for temporal relevance
            weighted_sim = sim * node.activation_weight
            results.append((node, weighted_sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    # ── Graph Traversal ───────────────────────────────────────────────────

    def traverse_path(
        self,
        start_node_id: str,
        relation_type: Optional[str] = None,
        depth: int = 1,
    ) -> list[SemanticNode]:
        """
        Traverse outgoing edges from a start node up to a given depth.
        Optionally filter by relation type.
        Returns all reachable nodes.
        """
        if start_node_id not in self._nodes:
            return []

        visited = set()
        result = []
        queue = [(start_node_id, 0)]

        while queue:
            current_id, current_depth = queue.pop(0)
            if current_id in visited or current_depth > depth:
                continue
            visited.add(current_id)

            if current_id != start_node_id:
                node = self._nodes.get(current_id)
                if node:
                    result.append(node)

            if current_depth < depth:
                edges = self.get_edges_from(current_id, relation_type)
                for edge in edges:
                    if edge.target_id not in visited:
                        queue.append((edge.target_id, current_depth + 1))

        return result

    def get_related(self, node_id: str, depth: int = 1) -> dict:
        """
        Get a contextual summary of everything related to a node.
        Used by the ingestion engine to build context for question generation.
        """
        node = self._nodes.get(node_id)
        if not node:
            return {"node": None, "related": [], "known": "", "goal": ""}

        related_nodes = self.traverse_path(node_id, depth=depth)

        # Build context strings
        goals = [n.label for n in related_nodes if n.node_type == "ambition"]
        skills = [n.label for n in related_nodes if n.node_type == "skill"]
        constraints = [n.label for n in related_nodes if n.node_type == "constraint"]

        return {
            "node": node.to_dict(),
            "related": [n.to_dict() for n in related_nodes],
            "goal": ", ".join(goals) if goals else "not yet defined",
            "known": ", ".join(skills) if skills else "no skills recorded",
            "constraints": ", ".join(constraints) if constraints else "none identified",
        }

    # ── Frame Operations ──────────────────────────────────────────────────

    def get_frame(self) -> dict:
        """
        Get the complete semantic frame for this user.
        Returns all nodes and edges organized by type.
        """
        frame = {
            "user_id": self.user_id,
            "nodes_by_type": {},
            "edges_by_type": {},
            "total_nodes": self.node_count,
            "total_edges": self.edge_count,
            "dimensions": {dim: 0 for dim in DIMENSIONS},
        }

        for node in self._nodes.values():
            ntype = node.node_type
            if ntype not in frame["nodes_by_type"]:
                frame["nodes_by_type"][ntype] = []
            frame["nodes_by_type"][ntype].append(node.to_dict())
            frame["dimensions"][node.dimension] = frame["dimensions"].get(node.dimension, 0) + 1

        for edge in self._edges.values():
            rtype = edge.relation_type
            if rtype not in frame["edges_by_type"]:
                frame["edges_by_type"][rtype] = []
            frame["edges_by_type"][rtype].append(edge.to_dict())

        return frame

    def to_profile_frame(self) -> dict:
        """
        Convert graph-native nodes into the profile-frame shape used by the
        Ideal Frame scorer, pitfall detector, and legacy CareerMemoryProfile.

        Graph memory keeps many granular nodes. The rest of the Career OS often
        needs one semantic map per domain, e.g. profile["capability"]["current_skills"].
        This method is the bridge between those two representations.
        """
        return semantic_frame_to_profile_frame(self.get_frame())

    def get_gaps(self, ideal_frame: dict) -> list[dict]:
        """
        Compare the current user frame against an ideal Target State Frame.
        Returns a list of gaps (missing nodes/fields) sorted by priority.
        
        The ideal_frame should have the structure from ideal_frames.py:
        {
            "required_nodes": [
                {"type": "skill", "required_fields": ["current_skills", "technical_baseline"]},
                ...
            ],
            "critical_gaps": ["technical_baseline", "dream_roles"],
            ...
        }
        """
        gaps = []
        critical_gaps = set(ideal_frame.get("critical_gaps", []))

        for requirement in ideal_frame.get("required_nodes", []):
            req_type = requirement["type"]
            req_fields = requirement.get("required_fields", [])

            # Find existing nodes of this type
            existing_nodes = self.get_nodes_by_type(req_type)

            if not existing_nodes:
                # Entire node type is missing
                priority = 1.0 if any(f in critical_gaps for f in req_fields) else 0.7
                gaps.append({
                    "gap_type": "missing_node_type",
                    "node_type": req_type,
                    "missing_fields": req_fields,
                    "priority": priority,
                    "label": f"No {req_type} information captured yet",
                    "is_critical": priority == 1.0,
                })
            else:
                # Check if required fields are present in any node's properties
                all_properties = {}
                for node in existing_nodes:
                    all_properties.update(node.properties)

                missing_fields = []
                for field_name in req_fields:
                    if field_name not in all_properties or not all_properties[field_name]:
                        missing_fields.append(field_name)

                if missing_fields:
                    priority = 0.8 if any(f in critical_gaps for f in missing_fields) else 0.5
                    gaps.append({
                        "gap_type": "missing_fields",
                        "node_type": req_type,
                        "missing_fields": missing_fields,
                        "existing_fields": list(all_properties.keys()),
                        "priority": priority,
                        "label": f"Incomplete {req_type}: missing {', '.join(missing_fields)}",
                        "is_critical": priority >= 0.8,
                    })

        # Also check optional nodes
        for requirement in ideal_frame.get("optional_nodes", []):
            req_type = requirement["type"]
            existing = self.get_nodes_by_type(req_type)
            if not existing:
                gaps.append({
                    "gap_type": "optional_missing",
                    "node_type": req_type,
                    "missing_fields": requirement.get("required_fields", []),
                    "priority": 0.3,
                    "label": f"Optional: {req_type} would improve confidence",
                    "is_critical": False,
                })

        # Sort by priority (critical gaps first)
        gaps.sort(key=lambda g: g["priority"], reverse=True)
        return gaps

    def compute_confidence(self, ideal_frame: dict) -> float:
        """
        Compute overall ingestion confidence (0.0 - 1.0).
        
        Factors:
        1. Gap coverage: % of required nodes/fields present
        2. Node confidence: average confidence of existing nodes
        3. Evidence density: how many nodes have strong evidence
        4. Critical gap penalty: heavy penalty if critical fields are missing
        """
        required = ideal_frame.get("required_nodes", [])
        if not required:
            return 0.0

        total_fields = 0
        filled_fields = 0
        critical_fields = set(ideal_frame.get("critical_gaps", []))
        critical_filled = 0
        critical_total = len(critical_fields)

        for requirement in required:
            req_type = requirement["type"]
            req_fields = requirement.get("required_fields", [])
            total_fields += len(req_fields)

            existing = self.get_nodes_by_type(req_type)
            all_props = {}
            for node in existing:
                all_props.update(node.properties)

            for field_name in req_fields:
                if field_name in all_props and all_props[field_name]:
                    filled_fields += 1
                    if field_name in critical_fields:
                        critical_filled += 1

        # Base coverage score
        coverage = filled_fields / max(total_fields, 1)

        # Average node confidence
        all_nodes = list(self._nodes.values())
        avg_confidence = (
            sum(n.confidence for n in all_nodes) / len(all_nodes)
            if all_nodes else 0.0
        )

        # Critical gap penalty
        if critical_total > 0:
            critical_ratio = critical_filled / critical_total
        else:
            critical_ratio = 1.0

        # Weighted combination
        score = (
            coverage * 0.45 +          # 45% weight on field coverage
            avg_confidence * 0.20 +     # 20% on node confidence
            critical_ratio * 0.35       # 35% on critical gaps filled
        )

        return min(1.0, max(0.0, score))

    # ── Temporal Decay ────────────────────────────────────────────────────

    def decay_weights(self):
        """
        Apply temporal decay to all node activation weights.
        
        Formula: W_t = W_0 * e^(-λ * t)
        Where t = days since last access.
        
        This ensures that recently accessed/mentioned nodes surface
        above old, stale information.
        """
        now = datetime.datetime.utcnow()
        for node in self._nodes.values():
            days_elapsed = (now - node.last_accessed).total_seconds() / 86400
            node.activation_weight = node.activation_weight * math.exp(
                -self.DECAY_LAMBDA * days_elapsed
            )
            # Floor at 0.05 so nothing fully disappears
            node.activation_weight = max(0.05, node.activation_weight)

    # ── Persistence ───────────────────────────────────────────────────────

    def save_to_db(self, db: Session):
        """Persist the graph to SQLite via upserts instead of full rewrites."""
        from app.models.semantic_memory import SemanticNodeModel, SemanticEdgeModel

        existing_nodes = {
            node.id: node
            for node in db.query(SemanticNodeModel).filter(
                SemanticNodeModel.user_id == self.user_id
            ).all()
        }
        existing_edges = {
            edge.id: edge
            for edge in db.query(SemanticEdgeModel).filter(
                SemanticEdgeModel.user_id == self.user_id
            ).all()
        }

        current_node_ids = set(self._nodes.keys())
        current_edge_ids = set(self._edges.keys())

        for stale_edge_id, stale_edge in existing_edges.items():
            if stale_edge_id not in current_edge_ids:
                db.delete(stale_edge)
        for stale_node_id, stale_node in existing_nodes.items():
            if stale_node_id not in current_node_ids:
                db.delete(stale_node)

        # Upsert nodes
        for node in self._nodes.values():
            db_node = existing_nodes.get(node.id)
            if not db_node:
                db_node = SemanticNodeModel(id=node.id, user_id=self.user_id)
                db.add(db_node)
            db_node.node_type = node.node_type
            db_node.label = node.label
            db_node.properties = json.dumps(node.properties)
            db_node.embedding = node.embedding.tobytes() if node.embedding is not None else None
            db_node.activation_weight = node.activation_weight
            db_node.dimension = node.dimension
            db_node.source = node.source
            db_node.confidence = node.confidence
            db_node.access_count = node.access_count
            db_node.created_at = node.created_at
            db_node.last_accessed = node.last_accessed

        # Upsert edges
        for edge in self._edges.values():
            db_edge = existing_edges.get(edge.id)
            if not db_edge:
                db_edge = SemanticEdgeModel(id=edge.id, user_id=self.user_id)
                db.add(db_edge)
            db_edge.source_id = edge.source_id
            db_edge.target_id = edge.target_id
            db_edge.relation_type = edge.relation_type
            db_edge.properties = json.dumps(edge.properties)
            db_edge.weight = edge.weight
            db_edge.created_at = edge.created_at

        db.commit()

    @classmethod
    def load_from_db(cls, db: Session, user_id: str) -> "MemoryGraph":
        """Load a user's graph from SQLite."""
        from app.models.semantic_memory import SemanticNodeModel, SemanticEdgeModel

        graph = cls(user_id=user_id)

        # Load nodes
        db_nodes = db.query(SemanticNodeModel).filter(
            SemanticNodeModel.user_id == user_id
        ).all()

        for db_node in db_nodes:
            embedding = None
            if db_node.embedding:
                embedding = np.frombuffer(db_node.embedding, dtype=np.float32).copy()

            props = {}
            if db_node.properties:
                try:
                    props = json.loads(db_node.properties)
                except (json.JSONDecodeError, TypeError):
                    props = {}

            node = SemanticNode(
                id=db_node.id,
                node_type=db_node.node_type,
                label=db_node.label,
                properties=props,
                embedding=embedding,
                activation_weight=db_node.activation_weight or 1.0,
                dimension=db_node.dimension or "cognitive",
                source=db_node.source or "ingestion",
                confidence=db_node.confidence or 0.5,
                access_count=db_node.access_count or 0,
                created_at=db_node.created_at or datetime.datetime.utcnow(),
                last_accessed=db_node.last_accessed or datetime.datetime.utcnow(),
            )
            graph.add_node(node, compute_embedding=False)

        # Load edges
        db_edges = db.query(SemanticEdgeModel).filter(
            SemanticEdgeModel.user_id == user_id
        ).all()

        for db_edge in db_edges:
            props = {}
            if db_edge.properties:
                try:
                    props = json.loads(db_edge.properties)
                except (json.JSONDecodeError, TypeError):
                    props = {}

            edge = SemanticEdge(
                id=db_edge.id,
                source_id=db_edge.source_id,
                target_id=db_edge.target_id,
                relation_type=db_edge.relation_type,
                properties=props,
                weight=db_edge.weight or 1.0,
                created_at=db_edge.created_at or datetime.datetime.utcnow(),
            )
            # Only add edge if both nodes exist (defensive)
            if edge.source_id in graph._nodes and edge.target_id in graph._nodes:
                graph.add_edge(edge)

        # Auto-heal any legacy duplicate nodes in DB and in memory
        graph.deduplicate_legacy_nodes(db)

        return graph

    def deduplicate_legacy_nodes(self, db: Session):
        """
        Deduplicates any legacy duplicate nodes (same type & case-insensitive label)
        already present in the SQLite database, merging properties, and updating edges.
        """
        from app.models.semantic_memory import SemanticNodeModel, SemanticEdgeModel

        # 1. Group nodes by (node_type, label.strip().lower())
        node_groups = {}
        for node in list(self._nodes.values()):
            if node.node_type == "user":
                continue
            key = (node.node_type, node.label.strip().lower())
            if key not in node_groups:
                node_groups[key] = []
            node_groups[key].append(node)

        duplicates_removed = False

        for (node_type, label), group in node_groups.items():
            if len(group) <= 1:
                continue

            # Keep the first node (primary node)
            primary = group[0]
            duplicates = group[1:]

            # Merge properties from duplicates into primary
            for dup in duplicates:
                if dup.properties:
                    for k, v in dup.properties.items():
                        if k not in primary.properties or (v and not primary.properties.get(k)):
                            primary.properties[k] = v
                        elif k == "proficiency":
                            try:
                                primary.properties[k] = max(int(primary.properties[k]), int(v))
                            except Exception:
                                primary.properties[k] = v
                primary.confidence = max(primary.confidence, dup.confidence)

                # Find all edges pointing to or coming from this duplicate and redirect them to primary
                edges_to_redirect = [e for e in list(self._edges.values()) if e.source_id == dup.id or e.target_id == dup.id]
                for edge in edges_to_redirect:
                    if edge.source_id == dup.id:
                        edge.source_id = primary.id
                    if edge.target_id == dup.id:
                        edge.target_id = primary.id

                    # Check if an identical edge already exists in memory to avoid edge duplication
                    other_edges = [e for e in self._edges.values() if e.id != edge.id]
                    duplicate_edge = False
                    for oe in other_edges:
                        if oe.source_id == edge.source_id and oe.target_id == edge.target_id and oe.relation_type == edge.relation_type:
                            duplicate_edge = True
                            break

                    if duplicate_edge:
                        # Remove this edge from memory and DB
                        if edge.id in self._edges:
                            del self._edges[edge.id]
                        db.query(SemanticEdgeModel).filter(SemanticEdgeModel.id == edge.id).delete()
                    else:
                        # Update DB edge references
                        db_edge = db.query(SemanticEdgeModel).filter(SemanticEdgeModel.id == edge.id).first()
                        if db_edge:
                            db_edge.source_id = edge.source_id
                            db_edge.target_id = edge.target_id

                # Delete duplicate node from memory and DB
                if dup.id in self._nodes:
                    del self._nodes[dup.id]
                db.query(SemanticNodeModel).filter(SemanticNodeModel.id == dup.id).delete()
                duplicates_removed = True

            # Update primary node in DB
            db_node = db.query(SemanticNodeModel).filter(SemanticNodeModel.id == primary.id).first()
            if db_node:
                db_node.properties = json.dumps(primary.properties)
                db_node.confidence = primary.confidence

        if duplicates_removed:
            db.commit()

    # ── Utility Methods ───────────────────────────────────────────────────

    def create_user_root_node(self, name: str, email: str = "") -> SemanticNode:
        """Create the root 'user' node that all other nodes connect to."""
        root_id = f"user_{self.user_id}"
        root = SemanticNode(
            id=root_id,
            node_type="user",
            label=name,
            properties={"name": name, "email": email},
            dimension="cognitive",
            source="system",
            confidence=1.0,
        )
        return self.add_node(root)

    def get_user_root(self) -> Optional[SemanticNode]:
        """Get the root user node."""
        root_id = f"user_{self.user_id}"
        return self._nodes.get(root_id)

    def add_entity_from_ingestion(
        self,
        node_type: str,
        label: str,
        properties: dict,
        relation_to_user: str = "HAS_SKILL",
        dimension: str = "cognitive",
        source: str = "ingestion",
        confidence: float = 0.6,
        **kwargs,
    ) -> tuple[SemanticNode, SemanticEdge]:
        """
        Convenience method to add an entity during ingestion and link it to the user root.
        Returns (node, edge). Checks for existing nodes of the same type and label to avoid duplication.
        """
        relation = kwargs.get("relation_type", relation_to_user)
        root = self.get_user_root()
        if not root:
            raise ValueError("User root node not found. Call create_user_root_node() first.")

        # Check for existing node with same node_type and label (case-insensitive)
        existing_nodes = self.get_nodes_by_type(node_type)
        existing_node = None
        target_label = label.strip().lower()
        for n in existing_nodes:
            if n.label.strip().lower() == target_label:
                existing_node = n
                break

        if existing_node:
            # Update properties if needed
            if properties:
                for k, v in properties.items():
                    if k not in existing_node.properties or (v and not existing_node.properties.get(k)):
                        existing_node.properties[k] = v
                    elif k == "proficiency":
                        # Keep the higher proficiency
                        try:
                            existing_node.properties[k] = max(int(existing_node.properties[k]), int(v))
                        except Exception:
                            existing_node.properties[k] = v
            # Update confidence if higher
            existing_node.confidence = max(existing_node.confidence, confidence)
            
            # Check if edge already exists
            existing_edges = self.get_edges_from(root.id)
            edge = None
            for e in existing_edges:
                if e.target_id == existing_node.id and e.relation_type == relation:
                    edge = e
                    break
            
            if not edge:
                edge = SemanticEdge(
                    id=str(uuid.uuid4()),
                    source_id=root.id,
                    target_id=existing_node.id,
                    relation_type=relation,
                )
                self.add_edge(edge)
            
            return existing_node, edge

        node = SemanticNode(
            id=str(uuid.uuid4()),
            node_type=node_type,
            label=label,
            properties=properties,
            dimension=dimension,
            source=source,
            confidence=confidence,
        )
        self.add_node(node)

        edge = SemanticEdge(
            id=str(uuid.uuid4()),
            source_id=root.id,
            target_id=node.id,
            relation_type=relation,
        )
        self.add_edge(edge)

        return node, edge

    def add_tension(
        self,
        user_claim: str,
        market_reality: str,
        tension_type: str = "aspiration_vs_reality",
        severity: float = 0.5,
        tension_id: Optional[str] = None,
        challenge_question: Optional[str] = None,
    ) -> SemanticNode:
        """
        Create a tension node when user belief conflicts with market data.
        Links it to the user root with CONFLICTS_WITH relation.
        """
        root = self.get_user_root()
        if not root:
            raise ValueError("User root node not found.")

        tension = SemanticNode(
            id=tension_id or str(uuid.uuid4()),
            node_type="tension",
            label=f"Tension: {tension_type}",
            properties={
                "user_claim": user_claim,
                "market_reality": market_reality,
                "tension_type": tension_type,
                "severity": severity,
                "status": "active",
                "challenge_question": challenge_question or "",
            },
            dimension="emotional",
            source="system",
            confidence=0.8,
        )
        self.add_node(tension)

        edge = SemanticEdge(
            id=str(uuid.uuid4()),
            source_id=root.id,
            target_id=tension.id,
            relation_type="CONFLICTS_WITH",
            weight=severity,
        )
        self.add_edge(edge)

        return tension

    def get_active_tensions(self) -> list[SemanticNode]:
        """Get all unresolved tension nodes."""
        tensions = self.get_nodes_by_type("tension")
        return [
            t for t in tensions
            if t.properties.get("status") == "active"
        ]

    def resolve_tension(self, tension_id: str, resolution: str):
        """Mark a tension as resolved."""
        node = self._nodes.get(tension_id)
        if node and node.node_type == "tension":
            node.properties["status"] = "resolved"
            node.properties["resolution"] = resolution
            node.properties["resolved_at"] = datetime.datetime.utcnow().isoformat()

    def to_summary(self) -> dict:
        """
        Generate a human-readable summary of the graph state.
        Used by the Orchestrator's Librarian agent.
        """
        frame = self.get_frame()
        summary = {
            "user_id": self.user_id,
            "total_nodes": self.node_count,
            "total_edges": self.edge_count,
            "nodes_count": self.node_count,
            "edges_count": self.edge_count,
        }

        for node_type in NODE_TYPES:
            nodes = self.get_nodes_by_type(node_type)
            if nodes:
                summary[node_type] = {
                    "count": len(nodes),
                    "labels": [n.label for n in nodes],
                    "avg_confidence": sum(n.confidence for n in nodes) / len(nodes),
                }

        tensions = self.get_active_tensions()
        if tensions:
            summary["active_tensions"] = [
                {
                    "type": t.properties.get("tension_type"),
                    "claim": t.properties.get("user_claim"),
                    "reality": t.properties.get("market_reality"),
                    "severity": t.properties.get("severity"),
                }
                for t in tensions
            ]

        # Add fallback structures to prevent schema mismatches in API/routers
        summary["skills"] = summary.get("skill", {}).get("labels", [])
        summary["ambitions"] = summary.get("ambition", {}).get("labels", [])

        return summary


def semantic_frame_to_profile_frame(frame: dict) -> dict:
    """Normalize a graph frame into {identity, ambition, capability, ...} maps."""
    nodes_by_type = frame.get("nodes_by_type", {})

    def nodes(node_type: str) -> list[dict]:
        return nodes_by_type.get(node_type, []) or []

    def merge_properties(node_type: str) -> dict:
        merged = {}
        labels = []
        for node in nodes(node_type):
            label = node.get("label")
            if label:
                labels.append(label)
            props = node.get("properties") or {}
            if isinstance(props, dict):
                for key, value in props.items():
                    if value not in (None, "", [], {}):
                        merged.setdefault(key, value)
        if labels:
            merged.setdefault("labels", labels)
        return merged

    skill_nodes = nodes("skill") + nodes("capability")
    skill_names = [node.get("label") for node in skill_nodes if node.get("label")]
    skill_depth = {}
    for node in skill_nodes:
        label = node.get("label")
        props = node.get("properties") or {}
        if not label:
            continue
        proficiency = props.get("proficiency") or props.get("level")
        details = props.get("details") or props.get("detail")
        if proficiency:
            skill_depth[label] = f"Proficiency level {proficiency}/10"
        elif details:
            skill_depth[label] = details

    ambition = merge_properties("ambition")
    ambition_labels = ambition.get("labels", [])
    ambition.setdefault("long_term_goals", ambition_labels)
    ambition.setdefault("dream_roles", ambition_labels)

    capability = merge_properties("capability")
    if skill_names:
        capability.setdefault("current_skills", skill_names)
    if skill_depth:
        capability.setdefault("skill_depth", skill_depth)
    gap_labels = [node.get("label") for node in nodes("gap") if node.get("label")]
    if gap_labels:
        capability.setdefault("identified_gaps", gap_labels)

    evidence = merge_properties("evidence")
    evidence_labels = evidence.get("labels", [])
    if evidence_labels:
        evidence.setdefault("projects", evidence_labels)

    return {
        "identity": merge_properties("identity"),
        "ambition": ambition,
        "capability": capability,
        "constraint": merge_properties("constraint"),
        "preference": merge_properties("preference"),
        "motivation": merge_properties("motivation"),
        "evidence": evidence,
    }
