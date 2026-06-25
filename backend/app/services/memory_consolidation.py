"""Memory consolidation pass for delta's semantic graph.

This is the system's lightweight "sleep cycle": it decays stale activation,
merges duplicate concepts, and returns a report the weekly loop can store.
"""

import re
from collections import defaultdict

from sqlalchemy.orm import Session

from app.services.memory_graph import MemoryGraph, SemanticEdge


_MERGEABLE_NODE_TYPES = {
    "ambition",
    "skill",
    "constraint",
    "preference",
    "motivation",
    "evidence",
    "gap",
    "inference",
}


def consolidate_user_memory(db: Session, user_id: str) -> dict:
    graph = MemoryGraph.load_from_db(db, user_id)
    before = graph.to_summary()

    graph.decay_weights()
    merge_report = _merge_duplicate_nodes(graph)
    graph.save_to_db(db)

    after = graph.to_summary()
    return {
        "status": "completed",
        "nodes_before": before.get("total_nodes", 0),
        "edges_before": before.get("total_edges", 0),
        "nodes_after": after.get("total_nodes", 0),
        "edges_after": after.get("total_edges", 0),
        "activation_decay_applied": True,
        "merged_nodes": merge_report["merged_nodes"],
        "merge_groups": merge_report["merge_groups"][:8],
    }


def _merge_duplicate_nodes(graph: MemoryGraph) -> dict:
    groups = defaultdict(list)
    for node in list(graph._nodes.values()):
        if node.node_type not in _MERGEABLE_NODE_TYPES:
            continue
        normalized = _normalize_label(node.label)
        if normalized:
            groups[(node.node_type, normalized)].append(node)

    merged_nodes = 0
    merge_groups = []
    for (node_type, normalized), nodes in groups.items():
        if len(nodes) < 2:
            continue

        nodes.sort(
            key=lambda item: (
                item.confidence,
                item.activation_weight,
                item.access_count,
            ),
            reverse=True,
        )
        primary = nodes[0]
        duplicates = nodes[1:]
        duplicate_ids = {node.id for node in duplicates}

        aliases = set(primary.properties.get("aliases", []))
        aliases.update(node.label for node in duplicates if node.label != primary.label)
        merged_from = set(primary.properties.get("merged_node_ids", []))
        merged_from.update(duplicate_ids)

        for duplicate in duplicates:
            primary.properties.update({
                key: value
                for key, value in duplicate.properties.items()
                if value and key not in primary.properties
            })
            primary.confidence = max(primary.confidence, duplicate.confidence)
            primary.activation_weight = max(primary.activation_weight, duplicate.activation_weight)
            primary.access_count += duplicate.access_count

        if aliases:
            primary.properties["aliases"] = sorted(aliases)
        primary.properties["merged_node_ids"] = sorted(merged_from)

        _reroute_edges(graph, duplicate_ids, primary.id)
        for duplicate in duplicates:
            graph.remove_node(duplicate.id)

        merged_nodes += len(duplicates)
        merge_groups.append({
            "node_type": node_type,
            "label": primary.label,
            "merged_count": len(duplicates),
            "normalized_key": normalized,
        })

    return {"merged_nodes": merged_nodes, "merge_groups": merge_groups}


def _reroute_edges(graph: MemoryGraph, duplicate_ids: set[str], primary_id: str):
    existing_signatures = {
        (edge.source_id, edge.target_id, edge.relation_type)
        for edge in graph._edges.values()
        if edge.source_id not in duplicate_ids and edge.target_id not in duplicate_ids
    }

    for edge in list(graph._edges.values()):
        if edge.source_id not in duplicate_ids and edge.target_id not in duplicate_ids:
            continue

        source_id = primary_id if edge.source_id in duplicate_ids else edge.source_id
        target_id = primary_id if edge.target_id in duplicate_ids else edge.target_id
        if source_id == target_id:
            continue

        signature = (source_id, target_id, edge.relation_type)
        if signature in existing_signatures:
            continue

        existing_signatures.add(signature)
        graph.add_edge(SemanticEdge(
            id=edge.id,
            source_id=source_id,
            target_id=target_id,
            relation_type=edge.relation_type,
            properties=edge.properties,
            weight=edge.weight,
            created_at=edge.created_at,
        ))


def _normalize_label(label: str) -> str:
    normalized = re.sub(r"[^a-z0-9+#.]+", " ", (label or "").lower()).strip()
    return re.sub(r"\s+", " ", normalized)
