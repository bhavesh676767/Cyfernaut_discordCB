"""
Relationship Tracking System
Tracks user interactions, frequency, activity patterns.
Enables proactive outreach (tags users after inactivity).
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

RELATIONSHIPS_DB_PATH = os.path.join(os.path.dirname(__file__), "relationships.db")

class RelationshipTracker:
    """Tracks bot's relationships with users and activity patterns."""
    
    def __init__(self):
        self.db_path = RELATIONSHIPS_DB_PATH
        self._init_db()
    
    def _init_db(self):
        """Initialize relationships database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # User relationship scores
        c.execute("""
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
        
        # User activity timeline
        c.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                timestamp TEXT,
                action_type TEXT,
                channel_id INTEGER,
                details_json TEXT
            )
        """)
        
        # Inactivity tracking (for proactive outreach)
        c.execute("""
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
        
        # User preferences learned
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,
                prefers_savagery INTEGER DEFAULT 0,
                prefers_support INTEGER DEFAULT 0,
                humor_type TEXT,
                active_hours_json TEXT,
                timezone TEXT
            )
        """)
        
        # Auto-migrate new columns if table already existed
        c.execute("PRAGMA table_info(relationships)")
        columns = [row[1] for row in c.fetchall()]
        if 'display_name' not in columns:
            c.execute("ALTER TABLE relationships ADD COLUMN display_name TEXT")
        if 'impression' not in columns:
            c.execute("ALTER TABLE relationships ADD COLUMN impression TEXT DEFAULT 'unknown'")
        if 'impression_notes' not in columns:
            c.execute("ALTER TABLE relationships ADD COLUMN impression_notes TEXT")
            
        conn.commit()
        conn.close()
    
    def record_interaction(self, user_id: int, username: str,
                          message_length: int, channel_id: int,
                          display_name: str = ""):
        """Record user interaction with bot."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        c.execute("SELECT total_interactions FROM relationships WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        
        if row:
            interactions = row[0] + 1
            c.execute("""
                UPDATE relationships
                SET total_interactions = ?,
                    total_messages_count = total_messages_count + ?,
                    last_interaction = ?,
                    display_name = ?,
                    relationship_score = relationship_score + 1
                WHERE user_id = ?
            """, (interactions, message_length, timestamp, display_name or username, user_id))
        else:
            c.execute("""
                INSERT INTO relationships
                (user_id, username, display_name, total_interactions,
                 total_messages_count, first_interaction, last_interaction,
                 relationship_score)
                VALUES (?, ?, ?, 1, ?, ?, ?, 5)
            """, (user_id, username, display_name or username, message_length, timestamp, timestamp))
        
        c.execute("""
            INSERT INTO activity_log
            (user_id, timestamp, action_type, channel_id, details_json)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, timestamp, "message", channel_id,
              f'{{"message_length": {message_length}}}'))
        
        c.execute("""
            INSERT OR REPLACE INTO inactivity_tracking
            (user_id, last_seen)
            VALUES (?, ?)
        """, (user_id, timestamp))
        
        conn.commit()
        conn.close()
    
    def get_top_users(self, limit: int = 10) -> List[Dict]:
        """Get users the bot talks to most."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            SELECT user_id, username, total_interactions, relationship_score,
                   last_interaction
            FROM relationships
            ORDER BY relationship_score DESC
            LIMIT ?
        """, (limit,))
        
        rows = c.fetchall()
        conn.close()
        
        return [
            {
                "user_id": r[0],
                "username": r[1],
                "interactions": r[2],
                "relationship_score": r[3],
                "last_interaction": r[4],
            }
            for r in rows
        ]
    
    def get_inactive_users(self, hours: int = 24) -> List[Dict]:
        """Get users inactive for X hours (candidates for outreach)."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        c.execute("""
            SELECT r.user_id, r.username, r.relationship_score, 
                   i.last_seen, i.outreach_count, i.responds_to_outreach
            FROM relationships r
            LEFT JOIN inactivity_tracking i ON r.user_id = i.user_id
            WHERE i.last_seen < ?
            AND r.relationship_score > 10
            ORDER BY r.relationship_score DESC
        """, (cutoff_time,))
        
        rows = c.fetchall()
        conn.close()
        
        return [
            {
                "user_id": r[0],
                "username": r[1],
                "relationship_score": r[2],
                "last_seen": r[3],
                "outreach_attempts": r[4],
                "responds": r[5],
            }
            for r in rows
        ]
    
    def record_outreach_attempt(self, user_id: int) -> bool:
        """Record when bot reaches out to user."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        c.execute("""
            UPDATE inactivity_tracking
            SET last_outreach_attempt = ?,
                outreach_count = outreach_count + 1
            WHERE user_id = ?
        """, (timestamp, user_id))
        
        conn.commit()
        conn.close()
        
        return True
    
    def record_outreach_response(self, user_id: int, responded: bool):
        """Record if user responded to outreach."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            UPDATE inactivity_tracking
            SET responds_to_outreach = ?
            WHERE user_id = ?
        """, (1 if responded else 0, user_id))
        
        conn.commit()
        conn.close()
    
    def get_user_relationship(self, user_id: int) -> Optional[Dict]:
        """Get complete relationship data for a user."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            SELECT r.user_id, r.username, r.total_interactions,
                   r.relationship_score, r.last_interaction,
                   i.last_seen, i.outreach_count, i.responds_to_outreach
            FROM relationships r
            LEFT JOIN inactivity_tracking i ON r.user_id = i.user_id
            WHERE r.user_id = ?
        """, (user_id,))
        
        row = c.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "user_id": row[0],
            "username": row[1],
            "total_interactions": row[2],
            "relationship_score": row[3],
            "last_interaction": row[4],
            "last_seen": row[5],
            "outreach_attempts": row[6],
            "responds_to_outreach": row[7],
        }
    
    def get_relationship_stats(self) -> Dict:
        """Get overall relationship statistics."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Total users
        c.execute("SELECT COUNT(*) FROM relationships")
        total_users = c.fetchone()[0]
        
        # Total interactions
        c.execute("SELECT SUM(total_interactions) FROM relationships")
        total_interactions = c.fetchone()[0] or 0
        
        # Average relationship score
        c.execute("SELECT AVG(relationship_score) FROM relationships")
        avg_score = c.fetchone()[0] or 0
        
        # Most active user
        c.execute("""
            SELECT username, total_interactions 
            FROM relationships 
            ORDER BY total_interactions DESC LIMIT 1
        """)
        most_active = c.fetchone()
        
        conn.close()
        
        return {
            "total_users": total_users,
            "total_interactions": total_interactions,
            "avg_relationship_score": round(avg_score, 2),
            "most_active_user": most_active[0] if most_active else "None",
            "most_active_count": most_active[1] if most_active else 0,
        }

    def get_server_reputation_summary(self) -> str:
        """Returns a string block summarizing the top users and their impressions/stats."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            SELECT display_name, username, total_interactions, impression, impression_notes, first_interaction
            FROM relationships
            ORDER BY total_interactions DESC
            LIMIT 15
        """)
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            return "No server data yet."
            
        summary = []
        for r in rows:
            name = r[0] if r[0] else r[1]
            interactions = r[2]
            impression = r[3]
            notes = f" ({r[4]})" if r[4] else ""
            first_seen = r[5][:10] if r[5] else "unknown"
            
            summary.append(f"- {name}: {interactions} interactions. Impression: {impression}{notes}. First seen: {first_seen}")
            
        return "\n".join(summary)
    
    def should_reach_out(self, user_id: int, hours: int = 24) -> bool:
        """Determine if bot should reach out to this user."""
        rel = self.get_user_relationship(user_id)
        
        if not rel:
            return False
        
        # Only reach out to close relationships
        if rel["relationship_score"] < 20:
            return False
        
        # Check if inactive long enough
        if not rel["last_seen"]:
            return False
        
        last_seen = datetime.fromisoformat(rel["last_seen"])
        hours_inactive = (datetime.now() - last_seen).total_seconds() / 3600
        
        if hours_inactive < hours:
            return False
        
        # Don't spam with outreach
        if rel["outreach_attempts"] > 3:
            return False
        
        return True

    def update_user_impression(self, user_id: int, impression: str, note: str = ""):
        """
        Update the bot's evolving impression of a user.
        impression: one of funny/annoying/chaotic/chill/cringe/dry/aggressive/smart/menace/etc.
        Impressions evolve slowly — not reset on every interaction.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            UPDATE relationships
            SET impression = ?, impression_notes = ?
            WHERE user_id = ?
        """, (impression, note, user_id))
        conn.commit()
        conn.close()

    def get_user_impression(self, user_id: int) -> dict:
        """
        Get the bot's current impression of a user for injecting into the AI prompt.
        Returns a dict with impression label, score, and interaction count.
        """
        rel = self.get_user_relationship(user_id)
        if not rel:
            return {
                "impression": "unknown", 
                "notes": "",
                "interactions": 0, 
                "score": 0, 
                "display_name": "",
                "last_seen": ""
            }
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT impression, impression_notes, display_name FROM relationships WHERE user_id = ?",
            (user_id,)
        )
        row = c.fetchone()
        conn.close()
        
        return {
            "impression":    row[0] if row and row[0] else "unknown",
            "notes":         row[1] if row and row[1] else "",
            "display_name":  row[2] if row and row[2] else "",
            "interactions":  rel.get("total_interactions", 0),
            "score":         rel.get("relationship_score", 0),
            "last_seen":     rel.get("last_interaction", ""),
        }


# Global instance
relationship_tracker = RelationshipTracker()
