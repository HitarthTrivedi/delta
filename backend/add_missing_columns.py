import sqlite3
import os

db_path = r"c:\Users\Shank\Documents\Delta\delta\backend\delta.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}. No migration needed as it will be created fresh.")
else:
    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check existing columns in career_memory_profiles
    cursor.execute("PRAGMA table_info(career_memory_profiles)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"Current columns in career_memory_profiles: {columns}")
    
    # Add graph_version if missing
    if "graph_version" not in columns:
        print("Adding graph_version column...")
        cursor.execute("ALTER TABLE career_memory_profiles ADD COLUMN graph_version INTEGER DEFAULT 0")
        conn.commit()
        print("[OK] graph_version added successfully!")
    else:
        print("graph_version column already exists.")
        
    # Add tension_nodes if missing
    if "tension_nodes" not in columns:
        print("Adding tension_nodes column...")
        cursor.execute("ALTER TABLE career_memory_profiles ADD COLUMN tension_nodes TEXT")
        conn.commit()
        print("[OK] tension_nodes added successfully!")
    else:
        print("tension_nodes column already exists.")
        
    conn.close()
    print("Migration script completed successfully!")
