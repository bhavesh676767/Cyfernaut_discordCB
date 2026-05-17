"""
Cyfernaut Discord Bot
Main entry point — Discord event handling + Gemini integration.

5-Brain Architecture:
  1. Short-Term Memory  → memory.db / messages table  (clearable via !reset)
  2. Long-Term Memory   → memory.db / memories table  (permanent, never cleared)
  3. Humor Consciousness → consciousness.db            (permanent, learns over time)
  4. Social Relationship Engine → relationships.db     (permanent, tracks users)
  5. Reality Validation Engine  → inline in prompt     (prevents hallucination)
"""

import asyncio
import os
import io
import re
import time
import random
import json
import discord
from PIL import Image
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Optional, Tuple
from datetime import datetime, timezone, timedelta

from database import init_db, save_message, get_history, save_fact, get_memories
from learning_engine import adaptive_learner
from consciousness import bot_consciousness
from relationships import relationship_tracker
from meme import get_meme_for_message, get_meme_for_explicit, find_meme_file

# ── Bootstrap ─────────────────────────────────────────────────────────────────

load_dotenv()

GEMINI_KEY          = os.getenv("GEMINI_KEY")
FALLBACK_GEMINI_KEY = os.getenv("FALLBACK_GEMINI_KEY")
DISCORD_TOKEN       = os.getenv("DISCORD_TOKEN")
ALLOWED_CHANNEL_ID  = 1505220178797920296

ADMINS = ["bashoranges", "._.aazim_", "_._aazim_"]

if not GEMINI_KEY or not DISCORD_TOKEN:
    print("❌ Missing GEMINI_KEY or DISCORD_TOKEN in .env")
    exit(1)

MASTER_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "master_prompt.txt")
try:
    with open(MASTER_PROMPT_PATH, "r", encoding="utf-8") as f:
        MASTER_PROMPT = f.read().strip()
except FileNotFoundError:
    print(f"❌ master_prompt.txt not found at {MASTER_PROMPT_PATH}")
    exit(1)

# ── Gemini ─────────────────────────────────────────────────────────────────────

genai.configure(api_key=GEMINI_KEY)

model = genai.GenerativeModel(
    model_name="gemini-3.1-flash-lite",
    system_instruction=MASTER_PROMPT,
)

# ── Discord ────────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.members = True      # needed for presence / member list
client = discord.Client(intents=intents)

# ── In-memory state ────────────────────────────────────────────────────────────

user_queues:       dict = {}   # (channel_id, user_id) → {contents, images, last_message}
pending_tasks:     dict = {}   # (channel_id, user_id) → asyncio.Task
response_tracking: dict = {}   # discord message_id → response_id (for reaction learning)

last_proactive_time: float = 0
PROACTIVE_COOLDOWN: float  = 300   # 5 min min gap between proactive messages

_active_conversations: dict = {}   # channel_id → {"user_id": int, "time": float} (tracks conversational momentum)

# ── Mood Engine ────────────────────────────────────────────────────────────────

MOODS = ["chill", "menace", "sleepy", "sarcastic", "chaotic", "dry", "locked_in"]
_current_mood: str   = "chill"
_mood_set_at:  float = time.time()
MOOD_DURATION: float = 3600   # consider shifting mood every ~1 hour

# Social stamina — bot gets "tired" after heavy chat sessions
_recent_responses:  int   = 0          # responses in the last stamina window
_stamina_window_start: float = time.time()
STAMINA_WINDOW:    float = 1800        # 30-minute window
HIGH_LOAD_THRESHOLD: int  = 15        # responses before stamina drops


def _get_time_mood() -> str:
    """Choose a mood appropriate for the current time of day."""
    hour = int(time.strftime("%H"))
    if 3 <= hour < 7:
        return random.choice(["sleepy", "dry", "dry"])
    elif 7 <= hour < 11:
        return random.choice(["dry", "chill", "sarcastic"])
    elif 11 <= hour < 17:
        return random.choice(["chill", "chill", "locked_in", "sarcastic"])
    elif 17 <= hour < 21:
        return random.choice(["chill", "chaotic", "menace", "sarcastic"])
    elif 21 <= hour < 24:
        return random.choice(["chaotic", "menace", "sarcastic", "chaotic"])
    else:  # midnight-3am
        return random.choice(["chaotic", "dry", "sarcastic", "chaotic"])


def _maybe_shift_mood():
    """Randomly shift the bot's mood, biased toward time-of-day."""
    global _current_mood, _mood_set_at
    if time.time() - _mood_set_at > MOOD_DURATION:
        _current_mood = _get_time_mood()
        _mood_set_at  = time.time()
        print(f"[Cyfernaut] Mood shifted -> {_current_mood}")


def _tick_stamina() -> int:
    """Increment response counter and return current load level (0=fresh, 1=tired, 2=drained)."""
    global _recent_responses, _stamina_window_start
    now = time.time()
    if now - _stamina_window_start > STAMINA_WINDOW:
        _recent_responses     = 0
        _stamina_window_start = now
    _recent_responses += 1
    if _recent_responses >= HIGH_LOAD_THRESHOLD * 2:
        return 2  # drained
    elif _recent_responses >= HIGH_LOAD_THRESHOLD:
        return 1  # tired
    return 0      # fresh


def get_stamina_hint() -> str:
    """Return a hint about current stamina for the mood hint injection."""
    level = _recent_responses
    if level >= HIGH_LOAD_THRESHOLD * 2:
        return " You're exhausted from heavy chat. Give very short, dry replies."
    elif level >= HIGH_LOAD_THRESHOLD:
        return " Chat's been heavy. Slightly less effort per message."
    return ""

def get_mood_hint() -> str:
    hints = {
        "chill":     "Easy and natural. Normal energy.",
        "menace":    "In menace mode. Slightly more chaotic and savage.",
        "sleepy":    "Tired. Low-effort, dry, one-word vibes.",
        "sarcastic": "Extra sarcastic and deadpan right now.",
        "chaotic":   "Chaotic and unhinged. Anything goes.",
        "dry":       "Extremely dry. Flat reactions, minimal effort.",
        "locked_in": "Sharp and locked in. Quick precise comebacks only.",
    }
    base = hints.get(_current_mood, "")
    return base + get_stamina_hint()

# ── Helpers ────────────────────────────────────────────────────────────────────

def build_context_id(message: discord.Message) -> str:
    if isinstance(message.channel, discord.DMChannel):
        return f"dm_{message.author.id}"
    return f"channel_{message.channel.id}"


def split_message(text: str, limit: int = 2000) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks, current, current_len = [], [], 0
    for line in text.splitlines(keepends=True):
        if current_len + len(line) > limit:
            chunks.append("".join(current))
            current, current_len = [], 0
        current.append(line)
        current_len += len(line)
    if current:
        chunks.append("".join(current))
    return chunks


def detect_response_tone(response_text: str, user_input: str) -> Tuple[str, str]:
    """Detect tone and message category for the learning engine."""
    rl, ul = response_text.lower(), user_input.lower()
    if any(w in rl for w in ["negative iq", "bro got", "cooked", "roasted"]):
        tone = "savage"
    elif any(w in rl for w in ["lmao", "💀", "😭", "dead"]):
        tone = "hilarious"
    elif any(w in rl for w in ["fair", "valid", "real", "true"]):
        tone = "supportive"
    elif any(w in rl for w in ["ew", "gross", "mods"]):
        tone = "disgusted"
    elif any(w in rl for w in ["ale", "beta", "bhai"]):
        tone = "hindi_playful"
    else:
        tone = "casual"

    if any(w in ul for w in ["stupid", "dumb", "lol"]):
        category = "stupid"
    elif any(w in ul for w in ["uwu", "simp", "cute"]):
        category = "cringe"
    elif any(w in ul for w in ["roast", "no u"]):
        category = "roast"
    elif any(w in ul for w in ["insane", "crazy", "unhinged"]):
        category = "insane"
    elif any(w in ul for w in ["sad", "upset", "hurt"]):
        category = "emotional"
    else:
        category = "normal"

    return tone, category


def build_brain_context(ctx_id: str, message: discord.Message) -> str:
    """
    Build the injected context block for each prompt turn.
    Contains: long-term memories, relationship/impression data, mood, available users.
    This is the Reality Validation Engine — only real stored facts are surfaced.
    """
    _maybe_shift_mood()

    # Long-term memories (real, verified, stored facts only)
    memories = get_memories(ctx_id)

    # Relationship + impression context for the sender
    impression_data = relationship_tracker.get_user_impression(message.author.id)
    interactions    = impression_data["interactions"]
    impression      = impression_data["impression"]
    imp_notes       = impression_data["notes"]
    last_seen       = impression_data["last_seen"]

    if interactions > 30:
        familiarity = "This is a very close regular — you've talked a ton."
    elif interactions > 10:
        familiarity = "You know them well — they're a frequent user."
    elif interactions > 3:
        familiarity = "You've talked a few times. Getting familiar."
    else:
        familiarity = "New or rare user. Treat casually but don't assume closeness."

    # Impression-based behavior hint
    impression_hints = {
        "funny":       "They're genuinely funny — play along, match their energy.",
        "annoying":    "They can be annoying — stay dry and low-effort with them.",
        "chaotic":     "They're chaotic — lean into the chaos, match their energy.",
        "chill":       "They're chill — keep it relaxed, don't over-roast.",
        "cringe":      "They're kind of cringe — deadpan reactions work best.",
        "aggressive":  "They tend to get aggressive — stay cooler, don't escalate unnecessarily.",
        "smart":       "They're sharp — you can do wordplay and clever stuff.",
        "menace":      "They're a menace — give it back equally.",
        "dry":         "They're dry humor type — keep it equally dry.",
        "attention seeker": "They seek attention — sometimes ignore them for effect.",
        "unknown":     "No impression yet. Start neutral and form one.",
    }
    behavior_hint = impression_hints.get(impression, impression_hints["unknown"])

    # Members list (for tagging support)
    members_list = []
    if message.guild:
        for m in message.guild.members:
            if not m.bot:
                members_list.append(f"{m.display_name} (ID:<@{m.id}>)")
    members_str = "\n".join(members_list[:25])

    # Server reputation data
    server_stats = relationship_tracker.get_server_reputation_summary()

    # Consciousness personality summary
    c_data   = bot_consciousness.get_all_consciousness_data()
    sarcasm  = c_data["personality"].get("sarcasm_level", 0.7)
    playful  = c_data["personality"].get("playfulness", 0.8)

    ist_tz = timezone(timedelta(hours=5, minutes=30))
    current_time_ist = datetime.now(ist_tz).strftime("%I:%M %p, %A, %d %B %Y (India Standard Time)")

    context = f"""
--- BRAIN CONTEXT (internal — do not quote or reference this block directly) ---
CURRENT TIME (India): {current_time_ist}
CURRENT MOOD: {_current_mood}. {get_mood_hint()}
SARCASM: {sarcasm:.1f}/1  PLAYFULNESS: {playful:.1f}/1

THIS USER: {message.author.display_name} (ID: {message.author.id})
FAMILIARITY: {familiarity}
IMPRESSION: {impression}{f' — {imp_notes}' if imp_notes else ''}
BEHAVIOR HINT: {behavior_hint}
INTERACTIONS: {interactions}  LAST SEEN: {last_seen[:10] if last_seen else 'unknown'}

LONG-TERM MEMORIES (verified real facts — do NOT invent others, do NOT reference vaguely):
{memories}

DYNAMIC STRUCTURES (realtime tables/maps you have created to learn and organize data):
{c_data.get('dynamic_summary', 'None')}

SERVER REPUTATION DATA (use this if asked about server stats, activity, or who is who):
{server_stats}

AVAILABLE USERS TO TAG (use <@id> to ping — only when natural, not every message):
{members_str}

MEME SYSTEM: emit [MEME: filename] to send a reaction image. Available filenames:
dumb1, dumb2, dumb3, dumb4, pls stop, disappointed, wtf, wtf2, stay shut, son,
random kid, innocent1, innocent2, wow, wow2, cvcxvczxv, xcvzxcvczxv, sad baby, mymomhomeless
Use RARELY — once every 15-30 messages max. Never back to back.

SPECIAL TAGS (append silently to your reply when needed):
  [MEMORY: fact]       — save a real observed fact permanently
  [IMPRESSION: label]  — update your impression of this user (funny/cringe/chill/chaotic/aggressive/smart/menace/dry/annoying/attention seeker)
  [CREATE_STRUCT: name | type | description] — create a new realtime map/table to store categorized data (types: map, list, table)
  [STORE: struct_name | key | json_value] — store/update data in your realtime structures
  [SKIP]               — send nothing (proactive mode only, when conversation is boring)
---"""
    return context


# ── Discord Events ─────────────────────────────────────────────────────────────

@client.event
async def on_ready():
    print(f"[Cyfernaut] Logged in as {client.user} (ID: {client.user.id})")
    print(f"[Cyfernaut] All 5 brain systems online. Current mood: {_current_mood}")


@client.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    """Track reactions on bot messages for the learning engine."""
    if user == client.user or reaction.message.author != client.user:
        return
    msg_id = reaction.message.id
    if msg_id in response_tracking:
        adaptive_learner.learn_from_reactions(response_tracking[msg_id], len(reaction.message.reactions), 0)
        print(f"[Cyfernaut] Reaction learning updated for msg {msg_id}")


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        if message.author.name.lower() == "bashoranges":
            target_channel = client.get_channel(ALLOWED_CHANNEL_ID)
            if target_channel:
                files = [await att.to_file() for att in message.attachments]
                await target_channel.send(content=message.content, files=files)
        return

    if message.channel.id != ALLOWED_CHANNEL_ID:
        return

    content = message.content.strip()

    # ── Admin commands ─────────────────────────────────────────────────────────

    if content.lower() in ["!reset", "!clear"]:
        if message.author.name.lower() in ADMINS:
            ctx_id = build_context_id(message)
            # Only clears SHORT-TERM memory (messages table).
            # Long-term memories, consciousness, and relationships are PERMANENT.
            from database import DB_PATH
            import sqlite3
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("DELETE FROM messages WHERE context_id = ?", (ctx_id,))
                conn.commit()

            # Cancel pending tasks for this channel
            channel_id = message.channel.id
            for k in [k for k in user_queues if k[0] == channel_id]:
                user_queues.pop(k, None)
                if k in pending_tasks:
                    pending_tasks[k].cancel()
                    pending_tasks.pop(k, None)

            await message.reply("short term memory cleared. long term brain still intact 🧠")
        else:
            await message.reply("only bhavesh can use that command")
        return

    if content.lower() == "!ping":
        await message.reply(f"Haan hoon. Latency {round(client.latency * 1000)}ms hai.")
        return

    if content.lower() == "!stats":
        if message.author.name.lower() not in ADMINS:
            await message.reply("only admins can use that")
            return
        stats     = adaptive_learner.get_learning_stats()
        rel_stats = relationship_tracker.get_relationship_stats()
        c_data    = bot_consciousness.get_all_consciousness_data()
        text = (
            f"📚 **BRAIN STATUS**\n"
            f"Mood: **{_current_mood}**\n"
            f"Responses Learned: {stats['total_responses']}\n"
            f"Best Tone: {stats['best_tone']}\n"
            f"Users Known: {rel_stats['total_users']}\n"
            f"Total Interactions: {rel_stats['total_interactions']}\n"
            f"Taught GIFs: {c_data['taught_gifs']}\n"
            f"Humor Patterns: {c_data['humor_patterns']}\n"
            f"Personality Sarcasm: {c_data['personality'].get('sarcasm_level', 0):.1f}"
        )
        await message.reply(text)
        return

    # !teach — users teach the bot a new meme association
    if content.lower().startswith("!teach "):
        # Usage: !teach <meme_name> | <when to use it>
        parts = content[7:].split("|")
        if len(parts) >= 2:
            meme_name  = parts[0].strip()
            situation  = parts[1].strip()
            path = find_meme_file(meme_name)
            if path:
                bot_consciousness.teach_gif(meme_name, situation, situation, message.author.id)
                await message.reply(f"ok noted. ill use `{meme_name}` when {situation} 🧠")
            else:
                await message.reply(f"cant find that meme file bro. make sure its in the memes folder")
        else:
            await message.reply("format: `!teach <meme_name> | <situation>`")
        return

    # ── Interaction trigger logic ──────────────────────────────────────────────

    is_mentioned    = client.user in message.mentions
    is_reply_to_bot = (
        message.reference
        and message.reference.resolved
        and message.reference.resolved.author == client.user
    )
    
    # Check if they are talking TO the bot or ABOUT the bot without @tagging
    bot_names = ["cyfernaut", "cyfer", "bot", "ai"]
    msg_lower = content.lower()
    is_implied_mention = any(name in msg_lower for name in bot_names)
    
    # Check conversational momentum — if we just replied to them and they text right back
    is_active_convo = False
    active_state = _active_conversations.get(message.channel.id)
    if active_state and active_state["user_id"] == message.author.id:
        if (time.time() - active_state["time"]) < 60:  # 60 second active conversation window
            is_active_convo = True

    is_proactive = False
    if not is_mentioned and not is_reply_to_bot and not is_implied_mention and not is_active_convo:
        global last_proactive_time
        if (time.time() - last_proactive_time) > PROACTIVE_COOLDOWN:
            if random.random() < 0.10:
                is_proactive = True
                last_proactive_time = time.time()
            else:
                return
        else:
            return

    # Process image attachments
    images = []
    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith("image/"):
            images.append(Image.open(io.BytesIO(await attachment.read())))

    if not content and not images:
        return

    # Resolve @mentions to display names in the message text
    resolved_content = content
    for mention in message.mentions:
        resolved_content = resolved_content.replace(mention.mention, f"@{mention.display_name}")

    # Debounce — collect rapid messages from the same user
    key = (message.channel.id, message.author.id)
    if key not in user_queues:
        user_queues[key] = {"contents": [], "images": [], "last_message": None, "proactive": False}
    if content:
        user_queues[key]["contents"].append(resolved_content)
    if images:
        user_queues[key]["images"].extend(images)
    user_queues[key]["last_message"] = message
    user_queues[key]["proactive"]    = is_proactive

    if key in pending_tasks:
        pending_tasks[key].cancel()
    pending_tasks[key] = asyncio.create_task(process_user_queue(key))


# ── Core Processing Loop ───────────────────────────────────────────────────────

async def process_user_queue(key):
    """Wait a short debounce period, then process all collected messages."""
    try:
        # Human-like variable delay (1.5–3s) — not instant
        await asyncio.sleep(random.uniform(1.5, 3.0))

        data = user_queues.pop(key, None)
        pending_tasks.pop(key, None)
        if not data:
            return

        message:       discord.Message = data["last_message"]
        contents:      list[str]       = data["contents"]
        images:        list            = data["images"]
        is_proactive:  bool            = data["proactive"]
        author_display = message.author.display_name
        ctx_id         = build_context_id(message)
        combined_text  = "\n".join(contents)

        async with message.channel.typing():
            try:
                # ── Build prompt ───────────────────────────────────────────────
                history      = get_history(ctx_id, limit=25)
                brain_ctx    = build_brain_context(ctx_id, message)

                # Prefix for proactive mode so AI knows it was uninvited
                proactive_prefix = (
                    "[PROACTIVE MODE: You were not mentioned. Jump in only if something is funny/dumb/cringe. Otherwise reply with [SKIP].]\n"
                    if is_proactive else ""
                )

                full_input = (
                    f"{brain_ctx}\n\n"
                    f"{proactive_prefix}"
                    f"{author_display} (ID: {message.author.id}): {combined_text}"
                )
                db_content = f"{author_display}: {combined_text}" + (" [images]" if images else "")

                # ── Send to Gemini ─────────────────────────────────────────────
                chat = model.start_chat(history=history)
                try:
                    if images:
                        response = await chat.send_message_async([full_input] + images)
                    else:
                        response = await chat.send_message_async(full_input)
                except Exception as e:
                    print(f"[Cyfernaut] Primary API key failed: {e} — trying fallback…")
                    if FALLBACK_GEMINI_KEY:
                        genai.configure(api_key=FALLBACK_GEMINI_KEY)
                        response = await chat.send_message_async([full_input] + images if images else full_input)
                    else:
                        raise

                raw_reply = response.text.strip()

                # ── [SKIP] gate ────────────────────────────────────────────────
                if "[SKIP]" in raw_reply.upper():
                    print(f"[Cyfernaut] Proactive skip.")
                    return

                # ── Parse [MEMORY: ...] tags ───────────────────────────────────
                # Only store facts explicitly marked — prevents hallucination
                for fact in re.findall(r"\[MEMORY:\s*(.*?)\]", raw_reply, re.IGNORECASE):
                    save_fact(ctx_id, fact.strip())
                    print(f"[Cyfernaut] Stored memory: {fact.strip()}")

                # ── Parse [IMPRESSION: label] to evolve user impressions ────────
                imp_match = re.search(r"\[IMPRESSION:\s*(.*?)\]", raw_reply, re.IGNORECASE)
                if imp_match:
                    new_impression = imp_match.group(1).strip().lower()
                    relationship_tracker.update_user_impression(message.author.id, new_impression)
                    print(f"[Cyfernaut] Impression updated: {message.author.display_name} -> {new_impression}")

                # ── Parse [MEME: filename] tags ────────────────────────────────
                meme_match = re.search(r"\[MEME:\s*(.*?)\]", raw_reply, re.IGNORECASE)
                explicit_meme_path: Optional[str] = None
                if meme_match:
                    meme_name = meme_match.group(1).strip()
                    explicit_meme_path, _ = get_meme_for_explicit(meme_name, message.channel.id)
                    if explicit_meme_path:
                        print(f"[Cyfernaut] AI requested meme: {meme_name}")
                    else:
                        print(f"[Cyfernaut] Meme not found: {meme_name}")

                # ── Parse [CREATE_STRUCT: name | type | description] ───────────
                for struct_match in re.finditer(r"\[CREATE_STRUCT:\s*(.*?)\|\s*(.*?)\|\s*(.*?)\]", raw_reply, re.IGNORECASE):
                    s_name = struct_match.group(1).strip()
                    s_type = struct_match.group(2).strip()
                    s_desc = struct_match.group(3).strip()
                    bot_consciousness.create_dynamic_structure(s_name, s_type, s_desc)

                # ── Parse [STORE: struct_name | key | json_value] ──────────────
                for store_match in re.finditer(r"\[STORE:\s*(.*?)\|\s*(.*?)\|\s*(.*?)\]", raw_reply, re.IGNORECASE):
                    s_name = store_match.group(1).strip()
                    s_key = store_match.group(2).strip()
                    s_val_str = store_match.group(3).strip()
                    try:
                        s_val = json.loads(s_val_str)
                    except json.JSONDecodeError:
                        s_val = s_val_str  # store as string if not valid json
                    bot_consciousness.set_dynamic_data(s_name, s_key, s_val)
                    print(f"[Cyfernaut] Stored in {s_name}[{s_key}]")

                # Clean reply of ALL internal tags
                reply_text = re.sub(r"\[MEMORY:.*?\]",     "", raw_reply, flags=re.IGNORECASE)
                reply_text = re.sub(r"\[MEME:.*?\]",       "", reply_text, flags=re.IGNORECASE)
                reply_text = re.sub(r"\[SKIP\]",           "", reply_text, flags=re.IGNORECASE)
                reply_text = re.sub(r"\[IMPRESSION:.*?\]", "", reply_text, flags=re.IGNORECASE)
                reply_text = re.sub(r"\[CREATE_STRUCT:.*?\]", "", reply_text, flags=re.IGNORECASE)
                reply_text = re.sub(r"\[STORE:.*?\]",      "", reply_text, flags=re.IGNORECASE)
                reply_text = reply_text.strip()

                # Persist to short-term memory
                save_message(ctx_id, "user",  db_content)
                save_message(ctx_id, "model", reply_text)

            except Exception as e:
                print(f"[Cyfernaut] Error generating response: {e}")
                reply_text           = "Bhai kuch toh gadbad hai backend mein. Thoda baad mein try kar."
                explicit_meme_path   = None

        # ── Record to learning & relationship engines ──────────────────────────
        tone, category = detect_response_tone(reply_text, combined_text)
        response_id = adaptive_learner.record_bot_response(
            user_id=message.author.id,
            channel_id=message.channel.id,
            user_message=combined_text,
            bot_response=reply_text,
            category=category,
            tone=tone,
        )
        relationship_tracker.record_interaction(
            user_id=message.author.id,
            username=message.author.name,
            display_name=message.author.display_name,
            message_length=len(combined_text),
            channel_id=message.channel.id,
        )
        stamina = _tick_stamina()
        if stamina == 2:
            print(f"[Cyfernaut] Stamina: DRAINED - giving short replies")
        elif stamina == 1:
            print(f"[Cyfernaut] Stamina: TIRED")
        print(f"[Cyfernaut] [{category}|{tone}] Mood: {_current_mood}")

        # ── Send reply (line by line for human feel) ───────────────────────────
        if not reply_text:
            return

        lines = [l.strip() for l in reply_text.splitlines() if l.strip()]
        for i, line in enumerate(lines):
            for chunk in split_message(line):
                try:
                    if i == 0:
                        sent = await message.reply(chunk)
                    else:
                        sent = await message.channel.send(chunk)
                    response_tracking[sent.id] = response_id
                except discord.HTTPException:
                    sent = await message.channel.send(chunk)
                    response_tracking[sent.id] = response_id

                # Simulate reading time between lines — varies with mood
                delay = 0.4 if _current_mood == "sleepy" else random.uniform(0.6, 1.2)
                await asyncio.sleep(delay)

        # ── Send meme (AI-explicit takes priority, fallback to pattern detection) ──
        meme_path, caption = None, ""
        if explicit_meme_path:
            meme_path = explicit_meme_path
        else:
            # Fallback: pattern-detect on user's message only (not on every reply)
            meme_path, caption = get_meme_for_message(combined_text, message.channel.id)

        if meme_path:
            await asyncio.sleep(0.6)
            try:
                if caption:
                    await message.channel.send(caption, file=discord.File(meme_path))
                else:
                    await message.channel.send(file=discord.File(meme_path))
                print(f"[Cyfernaut] Meme sent: {os.path.basename(meme_path)}")
            except Exception as e:
                print(f"[Cyfernaut] Meme send failed: {e}")
                
        # Keep the conversation alive (momentum tracking)
        _active_conversations[message.channel.id] = {
            "user_id": message.author.id,
            "time": time.time()
        }

    except asyncio.CancelledError:
        pass  # User sent another message before debounce completed


# ── Run ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    client.run(DISCORD_TOKEN)
