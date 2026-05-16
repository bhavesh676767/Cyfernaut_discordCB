"""
Adaptive Learning Engine for Cyfernaut
Learns from interactions and adapts humor, tone, and response style.
Develops a personalized personality over time.
"""

import uuid
from datetime import datetime
from typing import Optional, Tuple, Dict
from learning_db import learning_db, ResponseMetric
import random

class AdaptiveLearner:
    """Analyzes interactions and learns optimal response patterns."""
    
    def __init__(self):
        self.learning_db = learning_db
    
    def create_response_id(self) -> str:
        """Generate unique ID for tracking responses."""
        return str(uuid.uuid4())
    
    def record_bot_response(self, 
                           user_id: int, 
                           channel_id: int,
                           user_message: str,
                           bot_response: str,
                           category: str,
                           tone: str) -> str:
        """Record a response from the bot for learning."""
        response_id = self.create_response_id()
        
        metric = ResponseMetric(
            response_id=response_id,
            category=category,
            user_id=user_id,
            channel_id=channel_id,
            timestamp=datetime.now().isoformat(),
            response_text=bot_response,
            user_message=user_message,
            reactions_count=0,
            replies_count=0,
            engagement_score=0,
            humor_rating=0,
            tone=tone
        )
        
        self.learning_db.record_response(metric)
        return response_id
    
    def get_user_adjusted_tone(self, user_id: int) -> str:
        """Get the learned tone to use for this user."""
        profile = self.learning_db.get_user_profile(user_id)
        
        # If we have data, use learned preference
        if profile["interaction_count"] > 5:
            return profile["preferred_tone"]
        
        # Default based on humor sensitivity
        if profile["humor_sensitivity"] > 0.7:
            return random.choice(["casual", "savage", "sarcastic"])
        else:
            return "casual"
    
    def get_channel_adapted_response_style(self, channel_id: int) -> Dict:
        """Get optimal response style for this channel."""
        dynamics = self.learning_db.get_channel_dynamics(channel_id)
        
        return {
            "humor_level": dynamics["humor_level"],  # 0-1 (how funny to be)
            "formality": dynamics["formality_level"],  # 0-1 (how formal)
            "preferred_tone": dynamics["tone_preference"],
            "best_type": dynamics["best_response_type"],
        }
    
    def should_use_savage_mode(self, user_id: int, message: str) -> bool:
        """Decide if user has high roast tolerance."""
        profile = self.learning_db.get_user_profile(user_id)
        
        # Only go savage if user has shown tolerance in past
        if profile["roast_tolerance"] > 0.6 and profile["interaction_count"] > 3:
            # Also check if message warrants it
            aggressive_indicators = ["stupid", "dumb", "cringe", "wtf", "ew"]
            return any(indicator in message.lower() for indicator in aggressive_indicators)
        
        return False
    
    def learn_from_reactions(self, 
                            response_id: str,
                            reaction_count: int,
                            reply_count: int):
        """Update learning based on reaction metrics."""
        self.learning_db.update_engagement(response_id, reaction_count, reply_count)
    
    def get_personalized_captions(self, user_id: int, category: str) -> list[str]:
        """Get captions tailored to user preferences."""
        profile = self.learning_db.get_user_profile(user_id)
        
        # Base captions
        base_captions = {
            "stupid": ["speechless", "negative iq activities", "bro...", "what am i witnessing"],
            "cringe": ["holy cornball", "seek sunlight", "never say ts again", "😭"],
            "weak_roast": ["😭👉🪞", "no u", "awww lil bro mad", "thats nice bro"],
            "insane": ["aint no way 😭", "crazy scenes", "good heavens", "nah this cant be real"],
            "emotional": ["ale ale mera bacha gussa ho gaya?", "awww lil bro upset", "beta calm down 😭"],
            "suspicious": ["ew", "what possessed u to type this", "mods.", "im washing my eyes"],
            "embarrassed": ["bro thought he cooked", "this was NOT it", "public humiliation"],
        }
        
        captions = base_captions.get(category, ["📸"])
        
        # If user has favorites, weight them higher
        if profile["favorite_jokes"]:
            captions = profile["favorite_jokes"][:3] + captions
        
        return captions
    
    def get_top_performing_responses(self, limit: int = 5) -> list[Dict]:
        """Get the best responses bot has learned."""
        return self.learning_db.get_top_responses(limit=limit)
    
    def get_learning_stats(self) -> Dict:
        """Get bot's learning progress."""
        return self.learning_db.get_learning_summary()
    
    def optimize_response_length(self, channel_id: int) -> int:
        """Learn optimal response length for channel."""
        dynamics = self.learning_db.get_channel_dynamics(channel_id)
        
        # More formal = longer; more casual = shorter
        formality = dynamics["formality_level"]
        
        if formality > 0.7:
            return 150  # Longer responses
        elif formality > 0.4:
            return 100  # Medium
        else:
            return 50   # Short and snappy
    
    def get_humor_style_for_user(self, user_id: int) -> str:
        """Learn what type of humor works for this user."""
        profile = self.learning_db.get_user_profile(user_id)
        
        humor_types = ["dry", "observational", "self-deprecating", "absurdist", "sarcastic"]
        
        # If learned, use best type for user
        if profile["interaction_count"] > 10:
            # Could implement more sophisticated selection here
            return random.choice(humor_types)
        
        return "dry"  # Default safe choice

# Global learner instance
adaptive_learner = AdaptiveLearner()
