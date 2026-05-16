"""
Adaptive Learning Database for Cyfernaut Discord Bot
Tracks interactions, metrics, and learns patterns to develop humor and style.
Persists learning across all conversations.
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

LEARNING_DB_PATH = os.path.join(os.path.dirname(__file__), "learning.db")

@dataclass
class ResponseMetric:
    """Tracks how well a response performed."""
    response_id: str
    category: str  # "stupid", "cringe", "roast", "normal", etc.
    user_id: int
    channel_id: int
    timestamp: str
    response_text: str
    user_message: str
    reactions_count: int  # Total reactions
    replies_count: int    # How many people replied to this
    engagement_score: float  # Calculated score (0-100)
    humor_rating: int  # 1-5 scale (learns which responses are funniest)
    tone: str  # "casual", "savage", "cringe", "supportive", etc.

class LearningDatabase:
    """Manages all learning and adaptation data."""
    
    def __init__(self):
        self.db_path = LEARNING_DB_PATH
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Response metrics table - tracks performance of each response
        c.execute("""
            CREATE TABLE IF NOT EXISTS response_metrics (
                response_id TEXT PRIMARY KEY,
                category TEXT,
                user_id INTEGER,
                channel_id INTEGER,
                timestamp TEXT,
                response_text TEXT,
                user_message TEXT,
                reactions_count INTEGER DEFAULT 0,
                replies_count INTEGER DEFAULT 0,
                engagement_score REAL DEFAULT 0,
                humor_rating INTEGER DEFAULT 0,
                tone TEXT
            )
        """)
        
        # User profile table - learns per-user preferences
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                preferred_tone TEXT,
                humor_sensitivity REAL DEFAULT 0.5,
                roast_tolerance REAL DEFAULT 0.5,
                interaction_count INTEGER DEFAULT 0,
                favorite_jokes_json TEXT,
                last_interaction TEXT
            )
        """)
        
        # Channel dynamics table - learns what works in each channel
        c.execute("""
            CREATE TABLE IF NOT EXISTS channel_dynamics (
                channel_id INTEGER PRIMARY KEY,
                avg_engagement REAL DEFAULT 0,
                tone_preference TEXT,
                best_response_type TEXT,
                interaction_count INTEGER DEFAULT 0,
                humor_level REAL DEFAULT 0.5,
                formality_level REAL DEFAULT 0.3
            )
        """)
        
        # Learned patterns table - stores effective response patterns
        c.execute("""
            CREATE TABLE IF NOT EXISTS learned_patterns (
                pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_keywords TEXT,
                response_template TEXT,
                category TEXT,
                effectiveness_score REAL,
                usage_count INTEGER DEFAULT 0,
                last_used TEXT
            )
        """)
        
        # Humor database - tracks what jokes/responses work best
        c.execute("""
            CREATE TABLE IF NOT EXISTS humor_database (
                joke_id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                category TEXT,
                success_rate REAL,
                times_used INTEGER DEFAULT 0,
                times_got_reaction INTEGER DEFAULT 0,
                avg_engagement REAL DEFAULT 0,
                variants_json TEXT
            )
        """)
        
        # Conversation history for context learning
        c.execute("""
            CREATE TABLE IF NOT EXISTS conversation_context (
                conversation_id TEXT PRIMARY KEY,
                channel_id INTEGER,
                user_id INTEGER,
                topic TEXT,
                tone_used TEXT,
                messages_count INTEGER,
                effectiveness REAL,
                timestamp TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_response(self, metric: ResponseMetric):
        """Record a bot response and its initial data."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            INSERT OR REPLACE INTO response_metrics 
            (response_id, category, user_id, channel_id, timestamp, response_text, 
             user_message, reactions_count, engagement_score, tone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metric.response_id,
            metric.category,
            metric.user_id,
            metric.channel_id,
            metric.timestamp,
            metric.response_text,
            metric.user_message,
            metric.reactions_count,
            metric.engagement_score,
            metric.tone
        ))
        
        conn.commit()
        conn.close()
    
    def update_engagement(self, response_id: str, reactions: int, replies: int):
        """Update engagement metrics for a response."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Calculate engagement score (0-100)
        engagement_score = min(100, (reactions * 10) + (replies * 15))
        
        c.execute("""
            UPDATE response_metrics 
            SET reactions_count = ?, replies_count = ?, engagement_score = ?
            WHERE response_id = ?
        """, (reactions, replies, engagement_score, response_id))
        
        conn.commit()
        conn.close()
    
    def get_user_profile(self, user_id: int) -> Dict:
        """Get learned profile for a user."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            return self._create_default_user_profile(user_id)
        
        return {
            "user_id": row[0],
            "preferred_tone": row[1],
            "humor_sensitivity": row[2],
            "roast_tolerance": row[3],
            "interaction_count": row[4],
            "favorite_jokes": json.loads(row[5]) if row[5] else [],
            "last_interaction": row[6],
        }
    
    def _create_default_user_profile(self, user_id: int) -> Dict:
        """Create a new user profile with default values."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO user_profiles 
            (user_id, preferred_tone, humor_sensitivity, roast_tolerance, favorite_jokes_json)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, "casual", 0.5, 0.5, json.dumps([])))
        
        conn.commit()
        conn.close()
        
        return {
            "user_id": user_id,
            "preferred_tone": "casual",
            "humor_sensitivity": 0.5,
            "roast_tolerance": 0.5,
            "interaction_count": 0,
            "favorite_jokes": [],
            "last_interaction": None,
        }
    
    def update_user_profile(self, user_id: int, updates: Dict):
        """Update user profile with learning data."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Build dynamic update query
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [user_id]
        
        c.execute(f"UPDATE user_profiles SET {set_clause} WHERE user_id = ?", values)
        
        conn.commit()
        conn.close()
    
    def get_channel_dynamics(self, channel_id: int) -> Dict:
        """Get learned dynamics for a channel."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("SELECT * FROM channel_dynamics WHERE channel_id = ?", (channel_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            return self._create_default_channel_dynamics(channel_id)
        
        return {
            "channel_id": row[0],
            "avg_engagement": row[1],
            "tone_preference": row[2],
            "best_response_type": row[3],
            "interaction_count": row[4],
            "humor_level": row[5],
            "formality_level": row[6],
        }
    
    def _create_default_channel_dynamics(self, channel_id: int) -> Dict:
        """Create default channel dynamics."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO channel_dynamics 
            (channel_id, tone_preference, humor_level, formality_level)
            VALUES (?, ?, ?, ?)
        """, (channel_id, "casual", 0.5, 0.3))
        
        conn.commit()
        conn.close()
        
        return {
            "channel_id": channel_id,
            "avg_engagement": 0,
            "tone_preference": "casual",
            "best_response_type": None,
            "interaction_count": 0,
            "humor_level": 0.5,
            "formality_level": 0.3,
        }
    
    def get_top_responses(self, category: str = None, limit: int = 10) -> List[Dict]:
        """Get highest-performing responses."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        if category:
            c.execute("""
                SELECT response_id, response_text, category, engagement_score, tone
                FROM response_metrics
                WHERE category = ?
                ORDER BY engagement_score DESC
                LIMIT ?
            """, (category, limit))
        else:
            c.execute("""
                SELECT response_id, response_text, category, engagement_score, tone
                FROM response_metrics
                ORDER BY engagement_score DESC
                LIMIT ?
            """, (limit,))
        
        rows = c.fetchall()
        conn.close()
        
        return [
            {
                "response_id": r[0],
                "response_text": r[1],
                "category": r[2],
                "engagement_score": r[3],
                "tone": r[4],
            }
            for r in rows
        ]
    
    def get_learning_summary(self) -> Dict:
        """Get overall learning statistics."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Total responses recorded
        c.execute("SELECT COUNT(*) FROM response_metrics")
        total_responses = c.fetchone()[0]
        
        # Average engagement
        c.execute("SELECT AVG(engagement_score) FROM response_metrics WHERE engagement_score > 0")
        avg_engagement = c.fetchone()[0] or 0
        
        # Most successful tone
        c.execute("""
            SELECT tone, AVG(engagement_score) as avg_score
            FROM response_metrics
            WHERE tone IS NOT NULL
            GROUP BY tone
            ORDER BY avg_score DESC
            LIMIT 1
        """)
        best_tone_row = c.fetchone()
        best_tone = best_tone_row[0] if best_tone_row else "casual"
        
        # Most successful category
        c.execute("""
            SELECT category, AVG(engagement_score) as avg_score
            FROM response_metrics
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY avg_score DESC
            LIMIT 1
        """)
        best_category_row = c.fetchone()
        best_category = best_category_row[0] if best_category_row else None
        
        # Unique users interacted with
        c.execute("SELECT COUNT(DISTINCT user_id) FROM response_metrics")
        unique_users = c.fetchone()[0]
        
        conn.close()
        
        return {
            "total_responses": total_responses,
            "avg_engagement": round(avg_engagement, 2),
            "best_tone": best_tone,
            "best_category": best_category,
            "unique_users": unique_users,
        }

# Global instance
learning_db = LearningDatabase()
