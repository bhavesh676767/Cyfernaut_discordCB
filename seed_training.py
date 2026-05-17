"""
seed_training.py
Run this ONCE to pre-train Cyfernaut's brain with server culture knowledge.

Usage:
    python seed_training.py

What it does:
  - Seeds long-term memories (memory.db) with key server facts
  - Seeds relationship entries (relationships.db) with known people & impressions
  - Safe to re-run: skips duplicates where possible
"""

import sqlite3
import os
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
MEMORY_DB_PATH        = os.path.join(BASE, "memory.db")
RELATIONSHIPS_DB_PATH = os.path.join(BASE, "relationships.db")

CHANNEL_CTX_ID = "channel_1505220178797920296"  # main channel context id


# ── Long-term Memories ─────────────────────────────────────────────────────────

SEED_MEMORIES = [
    # Server identity
    "This is a school/college-age friend group server. Most members know each other IRL.",
    "Bhavesh (bashoranges) created this server and organizes events. He is the creator and admin.",
    "Aazim (._.aazim_) is the co-admin. Chill, responsible, tells impatient people to wait.",


    # Slang facts
    "This group uses 'ts' to mean 'this/that situation', 'asw' for 'as well', 'icl' for 'I can't lie'.",
    "They use 'FIRRRR??' to mean 'then what?!' after someone shares a spicy reveal.",
    "They use 'acoustic' as a playful slang for 'weird' or odd — use cautiously.",
    "They use 'hain' (Hindi) to mean 'huh / wait what?' when surprised.",
    "They use 'pakka' to mean definitely/for sure in Hindi.",
    "'bc' in this group is casual Hinglish slang, not always an expletive.",
    "The group often DDoS-joke and say 'ok bet' as a challenge accepted response.",

    # Second batch — more specific school behavior patterns
    "Staying up until 6am playing Valorant and then missing school is normalized in this group.",
    "When someone misses school the explanation is often 'valorant + random existential crisis' — treated as completely valid.",
    "Teacher gossip follows a specific tragic format: 'he used to be a good student 😭💔 its over'.",
    "Noticing cringe guys at school is a group activity. Format: 'tall idiot with chain', 'bro thinks he's in a music video 24/7'.",
    "Homework denial is a known bit — 'did u do chem hw' → 'be serious' → 'right sorry'. Nobody ever did the homework.",
    "The group never actually does homework but everyone pretends there's a chance they might have.",
]


# ── Relationship Seeds (use placeholder IDs — these get updated on real interaction) ──

SEED_USERS = [
    # (fake_id, username, display_name, interactions, impression, impression_notes, relationship_score)
    # Note: real user_ids will overwrite these when users actually chat
    # Using placeholder IDs starting from 9000000000 to avoid collision
    (9000000001, "bashoranges",   "Bhavesh",   50, "smart",   "Creator. Organizes events. Sharp and senior. Don't glaze.",    100),
    (9000000002, "._.aazim_",    "Aazim",     30, "chill",   "Co-admin. Responsible. Calm energy. Tells people to chill.",    70),
    (9000000003, "namish",       "Namish",    20, "chill",   "Helped with WebOS case content and visuals.",                   45),
    (9000000004, "atharv",       "Atharv",    25, "funny",   "Got most lovers in server event. Close with Bhavesh.",          55),
    (9000000005, "devpriya",     "Devpriya",  15, "chaotic", "Gets haters. Drama-adjacent energy.",                           35),
    (9000000006, "indreni",      "Indreni",   10, "unknown", "Newer person. Group noticed her. Pretty, new admission.",       20),
    (9000000007, "kanushi",      "Kanushi",   10, "unknown", "In 11th grade. Discussed by the group casually.",               20),
    (9000000008, "whising",      "Whising",    5, "unknown", "Hard to reach on DM. Owes the group server access.",           10),
]


# ── Seeding Functions ──────────────────────────────────────────────────────────

def seed_memories():
    """Inject seed memories into memory.db for the main channel context."""
    with sqlite3.connect(MEMORY_DB_PATH) as conn:
        # Create table if it doesn't exist yet (safe to run before bot starts)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                context_id  TEXT    NOT NULL,
                fact        TEXT    NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Get existing facts to avoid duplicates
        existing = {row[0] for row in conn.execute(
            "SELECT fact FROM memories WHERE context_id = ?", (CHANNEL_CTX_ID,)
        ).fetchall()}

        inserted = 0
        for fact in SEED_MEMORIES:
            if fact not in existing:
                conn.execute(
                    "INSERT INTO memories (context_id, fact) VALUES (?, ?)",
                    (CHANNEL_CTX_ID, fact)
                )
                inserted += 1

        conn.commit()

    print(f"[Seed] OK Memories: {inserted} new facts added ({len(SEED_MEMORIES) - inserted} already existed).")


def seed_relationships():
    """Inject known people into relationships.db with preset impressions."""
    now = datetime.now().isoformat()

    with sqlite3.connect(RELATIONSHIPS_DB_PATH) as conn:
        # Create tables if they don't exist yet
        conn.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                display_name TEXT,
                total_interactions INTEGER DEFAULT 0,
                total_messages_count INTEGER DEFAULT 0,
                avg_interaction_length REAL DEFAULT 0,
                relationship_score REAL DEFAULT 0,
                first_interaction TEXT,
                last_interaction TEXT,
                impression TEXT DEFAULT 'unknown',
                impression_notes TEXT,
                favorite_topics_json TEXT,
                recent_activity_json TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inactivity_tracking (
                user_id INTEGER PRIMARY KEY,
                last_seen TEXT,
                inactivity_hours REAL DEFAULT 0,
                last_outreach_attempt TEXT,
                outreach_count INTEGER DEFAULT 0,
                responds_to_outreach INTEGER DEFAULT 0,
                best_time_to_reach TEXT
            )
        """)
        inserted = 0
        skipped  = 0
        for user_id, username, display_name, interactions, impression, notes, score in SEED_USERS:
            existing = conn.execute(
                "SELECT user_id FROM relationships WHERE user_id = ?", (user_id,)
            ).fetchone()

            if existing:
                skipped += 1
                continue

            conn.execute("""
                INSERT INTO relationships
                (user_id, username, display_name, total_interactions, total_messages_count,
                 relationship_score, first_interaction, last_interaction, impression, impression_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, username, display_name, interactions,
                interactions * 40,  # rough avg message length estimate
                score, now, now, impression, notes
            ))

            conn.execute("""
                INSERT OR IGNORE INTO inactivity_tracking (user_id, last_seen)
                VALUES (?, ?)
            """, (user_id, now))

            inserted += 1

        conn.commit()

    print(f"[Seed] OK Relationships: {inserted} users seeded ({skipped} already existed).")


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("[Seed] Starting Cyfernaut training seed...")
    print(f"[Seed] Target context: {CHANNEL_CTX_ID}")
    print()

    seed_memories()
    seed_relationships()

    print()
    print("[Seed] Done. Cyfernaut now knows the server culture from day 1.")
    print("[Seed] Real user IDs will update/overwrite placeholder relationships on first interaction.")
