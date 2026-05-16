"""
Bot Consciousness System - Separate AI Brain
Persists across !reset commands. Contains humor, personality, and learned skills.
Real-time learning that never gets wiped.
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

CONSCIOUSNESS_DB_PATH = os.path.join(os.path.dirname(__file__), "consciousness.db")

class BotConsciousness:
    """The bot's permanent brain - learns, remembers, teaches itself."""
    
    def __init__(self):
        self.db_path = CONSCIOUSNESS_DB_PATH
        self._init_db()
    
    def _init_db(self):
        """Initialize consciousness database schema."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Taught GIF mappings - users teach the bot what GIF to use when
        c.execute("""
            CREATE TABLE IF NOT EXISTS taught_gifs (
                gif_id INTEGER PRIMARY KEY AUTOINCREMENT,
                gif_name TEXT NOT NULL,
                trigger_keywords TEXT,
                situation_description TEXT,
                taught_by_user_id INTEGER,
                taught_timestamp TEXT,
                times_used INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.5,
                usage_log_json TEXT
            )
        """)
        
        # Core personality traits - what makes the bot "itself"
        c.execute("""
            CREATE TABLE IF NOT EXISTS personality_traits (
                trait_id INTEGER PRIMARY KEY AUTOINCREMENT,
                trait_name TEXT UNIQUE,
                trait_value REAL,
                learned_from_interactions INTEGER DEFAULT 0,
                last_updated TEXT
            )
        """)
        
        # Humor patterns the bot has learned
        c.execute("""
            CREATE TABLE IF NOT EXISTS humor_patterns (
                pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_content TEXT,
                category TEXT,
                effectiveness_score REAL,
                times_used INTEGER DEFAULT 0,
                times_succeeded INTEGER DEFAULT 0,
                learned_from_user_id INTEGER,
                timestamp TEXT
            )
        """)
        
        # What the bot knows it's good at
        c.execute("""
            CREATE TABLE IF NOT EXISTS learned_skills (
                skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT UNIQUE,
                proficiency REAL,
                learn_method TEXT,
                teach_count INTEGER DEFAULT 0,
                last_used TEXT
            )
        """)
        
        # Bot's memory of interactions patterns (NOT conversation content)
        c.execute("""
            CREATE TABLE IF NOT EXISTS interaction_patterns (
                pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT,
                pattern_description TEXT,
                effectiveness REAL,
                confidence_level REAL,
                observations INTEGER
            )
        """)
        
        # Core settings that define this bot instance
        c.execute("""
            CREATE TABLE IF NOT EXISTS consciousness_config (
                config_id INTEGER PRIMARY KEY AUTOINCREMENT,
                personality_version TEXT,
                learning_mode_active INTEGER DEFAULT 1,
                consciousness_active INTEGER DEFAULT 1,
                self_awareness_level REAL DEFAULT 0.5,
                last_reset_date TEXT,
                total_learning_events INTEGER DEFAULT 0
            )
        """)
        
        # Bot's dynamic custom tables / maps / learning structures
        c.execute("""
            CREATE TABLE IF NOT EXISTS dynamic_structures (
                structure_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                type TEXT,
                description TEXT,
                created_at TEXT
            )
        """)
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS dynamic_data (
                data_id INTEGER PRIMARY KEY AUTOINCREMENT,
                structure_name TEXT,
                key TEXT,
                value_json TEXT,
                updated_at TEXT,
                UNIQUE(structure_name, key)
            )
        """)
        
        conn.commit()
        conn.close()
        
        # Initialize default personality
        self._init_default_personality()
    
    def _init_default_personality(self):
        """Set up default personality traits."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Check if already initialized
        c.execute("SELECT COUNT(*) FROM personality_traits")
        if c.fetchone()[0] == 0:
            default_traits = {
                "sarcasm_level": 0.7,
                "empathy": 0.6,
                "humor_randomness": 0.5,
                "aggression": 0.4,
                "playfulness": 0.8,
                "intelligence": 0.8,
                "laziness": 0.3,
                "memery": 0.9,
            }
            
            for trait_name, trait_value in default_traits.items():
                c.execute("""
                    INSERT INTO personality_traits 
                    (trait_name, trait_value, last_updated)
                    VALUES (?, ?, ?)
                """, (trait_name, trait_value, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def teach_gif(self, gif_name: str, trigger_keywords: str, 
                  situation: str, taught_by: int) -> bool:
        """User teaches bot a new GIF usage pattern."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute("""
                INSERT INTO taught_gifs 
                (gif_name, trigger_keywords, situation_description, 
                 taught_by_user_id, taught_timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (gif_name, trigger_keywords, situation, taught_by, 
                  datetime.now().isoformat()))
            
            conn.commit()
            print(f"[Consciousness] 🧠 Learned new GIF: {gif_name}")
            return True
        except Exception as e:
            print(f"[Consciousness] ❌ Failed to teach GIF: {e}")
            return False
        finally:
            conn.close()
    
    def get_taught_gif(self, situation: str) -> Optional[Dict]:
        """Get a taught GIF based on situation keywords."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Search for matching GIFs by trigger keywords
        situation_lower = situation.lower()
        c.execute("""
            SELECT gif_id, gif_name, trigger_keywords, situation_description, success_rate
            FROM taught_gifs
            ORDER BY success_rate DESC
            LIMIT 10
        """)
        
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            return None
        
        # Find best match
        for row in rows:
            triggers = row[2].lower().split(',')
            if any(trigger.strip() in situation_lower for trigger in triggers):
                return {
                    "gif_id": row[0],
                    "gif_name": row[1],
                    "triggers": row[2],
                    "situation": row[3],
                    "success_rate": row[4],
                }
        
        return None
    
    def update_gif_success(self, gif_id: int, success: bool):
        """Update how well a taught GIF worked."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Get current stats
        c.execute("""
            SELECT times_used, times_succeeded
            FROM taught_gifs
            WHERE gif_id = ?
        """, (gif_id,))
        
        row = c.fetchone()
        if not row:
            conn.close()
            return
        
        times_used = row[0] + 1
        times_succeeded = row[1] + (1 if success else 0)
        success_rate = times_succeeded / times_used if times_used > 0 else 0.5
        
        # Update
        c.execute("""
            UPDATE taught_gifs
            SET times_used = ?, times_succeeded = ?, success_rate = ?
            WHERE gif_id = ?
        """, (times_used, times_succeeded, success_rate, gif_id))
        
        conn.commit()
        conn.close()
    
    def learn_humor_pattern(self, pattern: str, category: str, 
                           effectiveness: float, learned_from: int):
        """Bot learns a new humor pattern from interactions."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO humor_patterns
            (pattern_content, category, effectiveness_score, 
             learned_from_user_id, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (pattern, category, effectiveness, learned_from, 
              datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_personality_trait(self, trait_name: str) -> float:
        """Get a personality trait value (0-1)."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            SELECT trait_value FROM personality_traits 
            WHERE trait_name = ?
        """, (trait_name,))
        
        row = c.fetchone()
        conn.close()
        
        return row[0] if row else 0.5
    
    def update_personality_trait(self, trait_name: str, change: float):
        """Adjust a personality trait based on learning."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Get current value
        c.execute("""
            SELECT trait_value FROM personality_traits 
            WHERE trait_name = ?
        """, (trait_name,))
        
        row = c.fetchone()
        if not row:
            conn.close()
            return
        
        current = row[0]
        # Clamp to 0-1 range
        new_value = max(0, min(1, current + change))
        
        c.execute("""
            UPDATE personality_traits
            SET trait_value = ?, learned_from_interactions = learned_from_interactions + 1,
                last_updated = ?
            WHERE trait_name = ?
        """, (new_value, datetime.now().isoformat(), trait_name))
        
        conn.commit()
        conn.close()
    
    def add_skill(self, skill_name: str, proficiency: float, learn_method: str):
        """Bot learns a new skill."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            INSERT OR IGNORE INTO learned_skills
            (skill_name, proficiency, learn_method, last_used)
            VALUES (?, ?, ?, ?)
        """, (skill_name, proficiency, learn_method, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()

    def create_dynamic_structure(self, name: str, struct_type: str, description: str) -> bool:
        """Create a new dynamic data structure (map, list, table) for learning."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute("""
                INSERT OR IGNORE INTO dynamic_structures (name, type, description, created_at)
                VALUES (?, ?, ?, ?)
            """, (name, struct_type, description, datetime.now().isoformat()))
            conn.commit()
            print(f"[Consciousness] 🧠 Created new dynamic structure: {name} ({struct_type})")
            return True
        except Exception as e:
            print(f"[Consciousness] ❌ Failed to create dynamic structure: {e}")
            return False
        finally:
            conn.close()

    def set_dynamic_data(self, structure_name: str, key: str, value: any) -> bool:
        """Store or update data in a dynamic structure."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            # Ensure structure exists as default 'map' if not explicitly created
            c.execute("""
                INSERT OR IGNORE INTO dynamic_structures (name, type, description, created_at)
                VALUES (?, 'map', 'Auto-created dynamic map', ?)
            """, (structure_name, datetime.now().isoformat()))
            
            c.execute("""
                INSERT INTO dynamic_data (structure_name, key, value_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(structure_name, key) DO UPDATE SET
                value_json = excluded.value_json,
                updated_at = excluded.updated_at
            """, (structure_name, key, json.dumps(value), datetime.now().isoformat()))
            conn.commit()
            return True
        except Exception as e:
            print(f"[Consciousness] ❌ Failed to set dynamic data: {e}")
            return False
        finally:
            conn.close()

    def get_dynamic_structure(self, structure_name: str) -> Dict[str, any]:
        """Get all data for a specific dynamic structure."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT key, value_json FROM dynamic_data WHERE structure_name = ?", (structure_name,))
        rows = c.fetchall()
        conn.close()
        
        result = {}
        for k, v in rows:
            try:
                result[k] = json.loads(v)
            except:
                result[k] = v
        return result

    def get_all_dynamic_structures_summary(self) -> str:
        """Get a summary and data dump of all dynamic structures created by the bot."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT name, type, description FROM dynamic_structures")
        structures = c.fetchall()
        
        if not structures:
            conn.close()
            return "No dynamic structures created yet."
            
        summary = []
        for name, stype, desc in structures:
            c.execute("SELECT key, value_json FROM dynamic_data WHERE structure_name = ?", (name,))
            rows = c.fetchall()
            count = len(rows)
            
            struct_str = f"- {name} ({stype}): {count} entries — {desc}"
            if rows:
                struct_str += "\n  Contents:\n"
                for i, (k, v) in enumerate(rows):
                    if i >= 15:
                        struct_str += f"    ... and {count - 15} more.\n"
                        break
                    struct_str += f"    {k}: {v}\n"
            summary.append(struct_str.strip())
            
        conn.close()
        return "\n\n".join(summary)
    def get_all_consciousness_data(self) -> Dict:
        """Get complete consciousness snapshot."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Get traits
        c.execute("SELECT trait_name, trait_value FROM personality_traits")
        traits = {row[0]: row[1] for row in c.fetchall()}
        
        # Get skills
        c.execute("SELECT skill_name, proficiency FROM learned_skills")
        skills = {row[0]: row[1] for row in c.fetchall()}
        
        # Get taught GIFs
        c.execute("SELECT gif_name, success_rate FROM taught_gifs")
        gifs = len(c.fetchall())
        
        # Get humor patterns
        c.execute("SELECT COUNT(*) FROM humor_patterns")
        patterns = c.fetchone()[0]
        
        conn.close()
        
        dynamic_summary = self.get_all_dynamic_structures_summary()
        
        return {
            "personality": traits,
            "skills": skills,
            "taught_gifs": gifs,
            "humor_patterns": patterns,
            "dynamic_summary": dynamic_summary,
        }
    
    def wipe_consciousness(self) -> bool:
        """
        DANGER: Only called when bot is completely reset.
        Wipes everything - personality, skills, learned GIFs.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute("DELETE FROM personality_traits")
            c.execute("DELETE FROM humor_patterns")
            c.execute("DELETE FROM learned_skills")
            c.execute("DELETE FROM taught_gifs")
            c.execute("DELETE FROM interaction_patterns")
            c.execute("DELETE FROM dynamic_structures")
            c.execute("DELETE FROM dynamic_data")
            
            conn.commit()
            conn.close()
            
            print("[Consciousness] 💀 CONSCIOUSNESS WIPED - Bot reset to factory defaults")
            self._init_default_personality()
            return True
        except Exception as e:
            print(f"[Consciousness] ❌ Failed to wipe consciousness: {e}")
            return False

# Global consciousness instance
bot_consciousness = BotConsciousness()
