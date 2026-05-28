import sqlite3
import os

db_path = r"c:\Users\Shank\Documents\Delta\delta\backend\delta.db"


def ensure_columns(cursor, table, specs):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"Current columns in {table}: {columns}")
    for name, definition in specs.items():
        if name not in columns:
            print(f"Adding {table}.{name}...")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
            print(f"[OK] {table}.{name} added successfully!")
        else:
            print(f"{table}.{name} already exists.")


def ensure_table(cursor, name, ddl):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    )
    if cursor.fetchone():
        print(f"Table {name} already exists.")
        return
    print(f"Creating table {name}...")
    cursor.execute(ddl)
    print(f"[OK] {name} created successfully!")

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}. No migration needed as it will be created fresh.")
else:
    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    ensure_table(cursor, "career_memory_profiles", """
        CREATE TABLE career_memory_profiles (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR NOT NULL UNIQUE,
            identity TEXT,
            ambitions TEXT,
            capabilities TEXT,
            constraints TEXT,
            preferences TEXT,
            behavior TEXT,
            evidence TEXT,
            open_questions TEXT,
            confidence_score FLOAT DEFAULT 0.55,
            graph_version INTEGER DEFAULT 0,
            tension_nodes TEXT,
            created_at DATETIME,
            updated_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users (id)
        )
    """)
    ensure_columns(cursor, "career_memory_profiles", {
        "identity": "TEXT",
        "ambitions": "TEXT",
        "capabilities": "TEXT",
        "constraints": "TEXT",
        "preferences": "TEXT",
        "behavior": "TEXT",
        "evidence": "TEXT",
        "open_questions": "TEXT",
        "confidence_score": "FLOAT DEFAULT 0.55",
        "graph_version": "INTEGER DEFAULT 0",
        "tension_nodes": "TEXT",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    })

    ensure_table(cursor, "journey_events", """
        CREATE TABLE journey_events (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR NOT NULL,
            event_type VARCHAR NOT NULL,
            summary TEXT NOT NULL,
            evidence TEXT,
            impact TEXT,
            event_date DATE,
            created_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users (id)
        )
    """)

    ensure_table(cursor, "roadmap_states", """
        CREATE TABLE roadmap_states (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR NOT NULL UNIQUE,
            destination TEXT,
            phases TEXT,
            active_phase_id VARCHAR,
            weekly_focus TEXT,
            resource_graph TEXT,
            proof_requirements TEXT,
            last_replanned_reason TEXT,
            created_at DATETIME,
            updated_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users (id)
        )
    """)
    ensure_columns(cursor, "roadmap_states", {
        "resource_graph": "TEXT",
        "proof_requirements": "TEXT",
        "last_replanned_reason": "TEXT",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    })

    ensure_table(cursor, "semantic_nodes", """
        CREATE TABLE semantic_nodes (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR NOT NULL,
            node_type VARCHAR NOT NULL,
            label VARCHAR NOT NULL,
            properties TEXT,
            embedding BLOB,
            activation_weight FLOAT DEFAULT 1.0,
            dimension VARCHAR DEFAULT 'cognitive',
            source VARCHAR,
            confidence FLOAT DEFAULT 0.5,
            access_count INTEGER DEFAULT 0,
            created_at DATETIME,
            last_accessed DATETIME,
            FOREIGN KEY(user_id) REFERENCES users (id)
        )
    """)

    ensure_table(cursor, "semantic_edges", """
        CREATE TABLE semantic_edges (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR NOT NULL,
            source_id VARCHAR NOT NULL,
            target_id VARCHAR NOT NULL,
            relation_type VARCHAR NOT NULL,
            properties TEXT,
            weight FLOAT DEFAULT 1.0,
            created_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users (id),
            FOREIGN KEY(source_id) REFERENCES semantic_nodes (id),
            FOREIGN KEY(target_id) REFERENCES semantic_nodes (id)
        )
    """)

    ensure_table(cursor, "tension_nodes", """
        CREATE TABLE tension_nodes (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR NOT NULL,
            source_belief_node_id VARCHAR,
            tension_type VARCHAR NOT NULL,
            user_claim TEXT NOT NULL,
            market_reality TEXT NOT NULL,
            severity FLOAT DEFAULT 0.5,
            challenge_question TEXT,
            resolution TEXT,
            status VARCHAR DEFAULT 'active',
            created_at DATETIME,
            resolved_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users (id),
            FOREIGN KEY(source_belief_node_id) REFERENCES semantic_nodes (id)
        )
    """)

    ensure_table(cursor, "ingestion_sessions", """
        CREATE TABLE ingestion_sessions (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'active',
            current_round INTEGER DEFAULT 0,
            confidence_score FLOAT DEFAULT 0.0,
            gaps_total INTEGER DEFAULT 0,
            gaps_filled INTEGER DEFAULT 0,
            tensions_total INTEGER DEFAULT 0,
            tensions_resolved INTEGER DEFAULT 0,
            journey_type VARCHAR,
            conversation_log TEXT,
            market_context_used TEXT,
            created_at DATETIME,
            completed_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users (id)
        )
    """)

    conn.commit()
        
    conn.close()
    print("Migration script completed successfully!")
