# Cyfernaut Discord Bot

A Hinglish Gen-X Discord bot powered by **Gemini 1.5 Flash** with persistent SQLite memory.

---

## Project Structure

```
Cyfernaut_discordCB/
├── .env                ← Your secret keys (never share or commit this)
├── .env.example        ← Template — copy to .env and fill in values
├── bot.py              ← Main logic: Discord events + Gemini integration
├── database.py         ← SQLite memory layer
├── master_prompt.txt   ← Bot personality & language instructions
├── requirements.txt    ← Python dependencies
└── memory.db           ← Auto-created on first run
```

---

## Setup

### 1. Get your keys

| Key | Where to get it |
|---|---|
| `GEMINI_KEY` | [Google AI Studio](https://aistudio.google.com/) → Get API Key |
| `DISCORD_TOKEN` | [Discord Developer Portal](https://discord.com/developers/applications) → Your App → Bot → Reset Token |

### 2. Enable the Message Content Intent
In the Developer Portal → your app → **Bot** → scroll to **Privileged Gateway Intents** → enable **Message Content Intent**.

### 3. Invite the bot to your server
Developer Portal → **OAuth2** → **URL Generator** → select `bot` scope → select permissions (`Send Messages`, `Read Message History`) → open the generated URL.

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment

```bash
# Windows
copy .env.example .env
notepad .env

# Fill in:
# GEMINI_KEY=AIza...
# DISCORD_TOKEN=MTI...
```

### 6. Run

```bash
python bot.py
```

---

## Commands

| Command | What it does |
|---|---|
| Any message | Cyfernaut replies with memory of the last 15 messages |
| `!reset` | Clears conversation memory for this channel/DM |
| `!ping` | Health check — returns current latency |

---

## Memory Behaviour

- **In a server channel** — the whole channel shares one memory context (feels like a group conversation).
- **In a DM** — each user has their own private memory.
- Memory persists across bot restarts (SQLite file on disk).
- Stores the last **15 turns** per context to balance recall vs. API cost.

---

## Notes

- Long replies are automatically split at the 2000-character Discord limit.
- The master prompt is read once at startup — edit `master_prompt.txt` and restart to change the personality.
- `memory.db` is auto-created on first run. Add it to `.gitignore` if you don't want to commit chat history.
