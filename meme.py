"""
Meme Usage System for Cyfernaut Discord Bot
Intelligently selects and sends reaction memes at natural intervals.
"""

import os
import random
import re
from pathlib import Path
from typing import Optional, Tuple

# -- Configuration ------------------------------------------------------------

MEMES_DIR = r"C:\Users\bhave\Downloads\memes"
SUPPORTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp"]

# Per-channel message counters (channel_id -> message_count since last meme)
_msg_since_meme: dict = {}        # channel_id -> int
_next_meme_threshold: dict = {}   # channel_id -> int (random gap required)

# Pre-compiled regex patterns (compiled once at module load)
COMPILED_PATTERNS = {}

# -- Meme Mappings by Category ------------------------------------------------

MEME_CATEGORIES = {
    "stupid": ["dumb1", "dumb2", "dumb3", "dumb4"],
    "cringe": ["pls stop", "dissapointed", "wtf", "wtf2"],
    "weak_roast": ["stay shut", "son", "random kid", "innocent1", "innocent2"],
    "insane": ["wow", "wow2", "wtf", "cvcxvcxv", "xcvzcxvczxv"],
    "emotional": ["sad baby", "son", "innocent1"],
    "suspicious": ["mymomhomeless", "wtf2", "dissapointed"],
    "embarrassed": ["random kid", "dumb4", "dissapointed"],
}

CAPTIONS_BY_CATEGORY = {
    "stupid": ["speechless", "negative iq activities", "bro...", "what am i witnessing"],
    "cringe": ["holy cornball", "seek sunlight", "never say ts again", "😭"],
    "weak_roast": ["😭👉🪞", "no u", "awww lil bro mad", "thats nice bro"],
    "insane": ["aint no way 😭", "crazy scenes", "good heavens", "nah this cant be real"],
    "emotional": ["ale ale mera bacha gussa ho gaya?", "awww lil bro upset", "beta calm down 😭"],
    "suspicious": ["ew", "what possessed u to type this", "mods.", "im washing my eyes"],
    "embarrassed": ["bro thought he cooked", "this was NOT it", "public humiliation"],
}

# Pre-compile all regex patterns at module load time (performance optimization)
def _compile_patterns():
    """Compile all regex patterns once at startup."""
    patterns = {
        "stupid": [
            r"(lol|haha|xd|rofl).*" * 3,
            r"(ur|your|u are)\s+(so\s+)?(stupid|dumb|retard|idiot)",
            r"(that's|thats)\s+the\s+(most|stupidest|dumbest)",
            r"never heard of",
            r"(i don't|i dont|idnt)\s+(know|get|understand)",
        ],
        "cringe": [
            r"(simp|uwu|cute|kawaii)",
            r"(daddy|mommy)\s+(please|pls)",
            r"i\s+(love|adore)\s+you\s+so\s+much",
            r"(kisses|hugs|\*[a-z]+\*)",
            r"(no cap|no lie|fr fr|deadass)",
        ],
        "weak_roast": [
            r"(your mom|ur mom)\s+",
            r"(no u|no you)",
            r"(says|said)\s+(the|one)\s+who\s+",
            r"(lmao|lmfao)\s+(got\s+)?(roasted|burned)",
            r"(that's|thats)\s+not\s+funny",
        ],
        "insane": [
            r"(never seen|never heard)\s+of\s+(someone|people)\s+(so|this)\s+",
            r"(straight up|literally)\s+(insane|unhinged|crazy|mental)",
            r"(i'm|im)\s+(gonna|going to)\s+(commit|do something|end it)",
            r"(this is|thats)\s+(insane|unhinged|wild|crazy|unhinged)",
        ],
        "emotional": [
            r"(i'm|im)\s+(sad|upset|crying|hurt|mad|angry)",
            r"(that's|thats)\s+(mean|hurtful|rude)",
            r"(why would you|how dare you)",
            r"(leave me alone|stop it)",
        ],
        "suspicious": [
            r"(sus|sus|kinda sus|lowkey sus)",
            r"(ew|eww|gross|disgusting|nasty)",
            r"(tf|what\s+the|what\s+the\s+fuck)",
            r"(weird|creepy|disturbing)",
        ],
        "embarrassed": [
            r"(i thought|i was|seemed like)",
            r"(didn't|didnt)\s+(realize|know|see)",
            r"(my bad|oops|sorry|my mistake)",
            r"(that was|was\s+that)\s+(cringe|embarrassing|stupid)",
        ],
    }
    
    compiled = {}
    for category, pattern_list in patterns.items():
        compiled[category] = [re.compile(pat, re.IGNORECASE) for pat in pattern_list]
    return compiled

COMPILED_PATTERNS = _compile_patterns()

# Meme file cache (path -> exists)
_MEME_FILE_CACHE = {}

# -- Utility Functions --------------------------------------------------------

def find_meme_file(meme_name: str) -> Optional[str]:
    """
    Find a meme file by name, automatically detecting the correct extension.
    Returns the full path to the file, or None if not found.
    Uses cache to avoid filesystem checks.
    """
    if meme_name in _MEME_FILE_CACHE:
        return _MEME_FILE_CACHE[meme_name]
    
    for ext in SUPPORTED_EXTENSIONS:
        file_path = os.path.join(MEMES_DIR, f"{meme_name}{ext}")
        if os.path.exists(file_path):
            _MEME_FILE_CACHE[meme_name] = file_path
            return file_path
    
    _MEME_FILE_CACHE[meme_name] = None
    return None


def should_send_meme() -> bool:
    """
    Determine if a meme should be sent based on frequency rules.
    Target: ~1 meme per 15-30 messages.
    """
    # 5-8% chance per message (roughly 1 in 15-20 messages)
    return random.random() < 0.06


def analyze_message(text: str) -> Optional[str]:
    """
    Analyze message content to determine if it's stupid/cringe/insane/etc.
    Returns the category name, or None if no match found.
    Uses pre-compiled patterns for performance.
    """
    text_lower = text.lower().strip()
    
    # Check each category using pre-compiled patterns
    for category, compiled_pats in COMPILED_PATTERNS.items():
        if any(pat.search(text_lower) for pat in compiled_pats):
            return category
    
    return None


def select_meme(category: str) -> Optional[Tuple[str, Optional[str]]]:
    """
    Select a meme and caption for the given category.
    Returns (meme_file_path, caption) or (None, None) if meme not found.
    """
    if category not in MEME_CATEGORIES:
        return None, None
    
    meme_names = MEME_CATEGORIES[category]
    random.shuffle(meme_names)
    
    # Try to find a meme file that exists
    for meme_name in meme_names:
        meme_path = find_meme_file(meme_name)
        if meme_path:
            caption = random.choice(CAPTIONS_BY_CATEGORY.get(category, ["📸"]))
            return meme_path, caption
    
    return None, None


def _tick_channel(channel_id: int) -> bool:
    """
    Increment per-channel message counter.
    Returns True if we've passed the meme gap threshold (safe to consider sending).
    """
    _msg_since_meme[channel_id] = _msg_since_meme.get(channel_id, 0) + 1
    threshold = _next_meme_threshold.get(channel_id, random.randint(15, 35))
    return _msg_since_meme[channel_id] >= threshold


def _reset_channel_counter(channel_id: int):
    """Reset the message counter after a meme is sent."""
    _msg_since_meme[channel_id] = 0
    _next_meme_threshold[channel_id] = random.randint(15, 35)


def get_meme_for_explicit(meme_name: str, channel_id: int) -> tuple[str | None, str]:
    """
    Resolve a meme by exact filename (AI chose it via [MEME: filename]).
    Bypasses frequency throttle since the AI already decided timing.
    """
    path = find_meme_file(meme_name)
    if path:
        _reset_channel_counter(channel_id)  # Still reset so we enforce gap after
    return path, ""


def clear_meme_cache():
    """Clear the file existence cache (call if memes folder changes at runtime)."""
    _MEME_FILE_CACHE.clear()


def get_meme_for_message(text: str, channel_id: int) -> Optional[Tuple[str, Optional[str]]]:
    """
    Fallback meme selector — called when AI didn't emit a [MEME: ...] tag.
    Uses pattern detection + frequency throttle.
    Returns (meme_file_path, caption) or (None, None).
    """
    # Enforce gap between memes
    if not _tick_channel(channel_id):
        return None, None
    
    # Small secondary random gate so not EVERY qualifying message gets one
    if not should_send_meme():
        return None, None
    
    # Analyze the message to determine category
    category = analyze_message(text)
    if not category:
        return None, None
    
    meme_path, caption = select_meme(category)
    if meme_path:
        _reset_channel_counter(channel_id)
    return meme_path, caption
