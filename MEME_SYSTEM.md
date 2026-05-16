# Meme Usage System Documentation

## Overview

The Meme Usage System is a natural, intelligent reaction meme engine for your Discord bot. It analyzes user messages and sends reaction images at rare, well-timed intervals—making the bot feel like a funny Discord user who occasionally drops the perfect reaction, not a meme-spamming bot.

## How It Works

### Frequency Control
- **Target**: ~1 meme per 15-30 messages (6% per message when checked)
- **Check Rate**: Only evaluates messages every 3-5 messages to reduce computation
- **Result**: Memes feel unexpected and impactful

### Message Analysis
When a meme check occurs, the system analyzes the user's message against patterns for:

- **Stupid**: Excessive laughing, dumb takes, obvious ignorance claims
- **Cringe**: Simping language, asterisk actions, overused slang
- **Weak Roast**: "Your mom" jokes, "no u", failed comebacks
- **Insane**: Unhinged claims, mental breakdown language
- **Emotional**: Getting upset after being roasted, claiming hurt feelings
- **Suspicious**: Sus behavior, gross/weird messages, disturbing content
- **Embarrassed**: Admitting mistakes, claiming something was embarrassing

### Meme Selection & Sending
1. If a category matches, a random meme from that category is selected
2. The system finds the meme file (supports .jpg, .png, .gif, .jpeg, .webp)
3. A short, optional caption is selected from the category's caption pool
4. Meme is sent with a small delay after the reply for natural pacing

## File Structure

```
meme.py                 # Main meme system module
memes/                  # Meme image directory
├── dumb1.jpg
├── dumb2.jpg
├── pls_stop.jpg
├── sad_baby.jpg
└── ... (25+ meme files)
```

## Customization

### Adding New Memes

1. Add your meme image to the `memes/` folder (any supported format)
2. Update `MEME_CATEGORIES` in `meme.py`:
```python
MEME_CATEGORIES = {
    "stupid": ["dumb1", "dumb2", "dumb3", "dumb4", "your_new_meme"],  # Add here
    # ... other categories
}
```
3. Optional: Add captions to `CAPTIONS_BY_CATEGORY` if desired

### Adjusting Frequency

Edit the `should_send_meme()` function in `meme.py`:
```python
def should_send_meme() -> bool:
    # Currently 6% = roughly 1 per 15-20 messages
    # Change to 0.10 for 10% (more frequent)
    # Change to 0.03 for 3% (less frequent)
    return random.random() < 0.06
```

### Adjusting Check Rate

Edit the `should_check_for_meme()` function:
```python
def should_check_for_meme(channel_id: int) -> bool:
    counter = update_counter(channel_id)
    # Currently checks every 3-5 messages
    # Lower number = more frequent checks
    # Higher number = fewer checks
    return counter % random.randint(3, 5) == 0
```

### Tweaking Detection Patterns

Edit the `analyze_message()` function to add or modify regex patterns for each category:
```python
stupid_patterns = [
    r"(lol|haha|xd|rofl).*" * 3,  # excessive laughing
    r"(ur|your|u are)\s+(so\s+)?(stupid|dumb)",  # stupid take
    # Add more patterns here...
]
```

## Integration Points

The system integrates at one place in `bot.py`:
- After each reply is sent, `send_reaction_meme()` is called with the user's original message
- If conditions are met, a meme is sent to the channel

## Key Design Principles

✅ **Implemented**:
- Memes feel natural and unexpected
- Rare frequency (1 per 15-30 messages)
- Context-aware selection based on message content
- Short captions only, never explain the meme
- Graceful failure (silently skips if no meme available)
- Support for multiple image formats

✅ **Never Happens**:
- Memes are never sent consecutively
- Multiple memes aren't sent in one reply
- Memes don't appear during normal conversations
- The bot personality isn't meme-heavy

## Debugging

Enable logging by checking console output:
```
[Cyfernaut] Meme sending failed (non-critical): [error message]
```

If memes aren't sending:
1. Check file extensions in `memes/` folder (must match supported formats)
2. Verify meme filenames match exactly what's in `MEME_CATEGORIES`
3. Check that `MEMES_DIR` points to correct folder
4. Ensure bot has file permissions to read meme files

## Performance Impact

- Minimal: Message analysis uses simple regex patterns
- Checked infrequently (every 3-5 messages)
- File I/O only happens when meme is actually selected (~6% chance when checked)
- Graceful timeout if file operations fail

## Example Meme Interactions

**Good Example** (natural & rare):
```
User: "lol no ur stupid"
Bot: [1-2 line reply]
Bot: [5 seconds later] "no u" [weak roast meme]
```

**Bad Example** (would NOT happen):
```
User: "hey"
Bot: [reply]
Bot: [meme immediately]
Bot: [another meme]
```

## Statistics

Current meme count: 25 unique images across 7 categories

- Stupid: 4 memes (dumb1, dumb2, dumb3, dumb4)
- Cringe: 4 memes (pls stop, disappointed, wtf, wtf2)
- Weak Roast: 5 memes (stay shut, son, random kid, innocent1, innocent2)
- Insane: 6 memes (wow, wow2, wtf, cvcxvcxv, xcvzcxvczxv, etc.)
- Emotional: 3 memes (sad baby, son, innocent1)
- Suspicious: 3 memes (mymomhomeless, wtf2, disappointed)
- Embarrassed: 3 memes (random kid, dumb4, disappointed)

## Future Enhancements

Possible improvements:
- User-specific tracking (don't spam same user)
- Channel mood detection (less memes during serious conversations)
- Blacklisting certain patterns (don't react to certain topics)
- Meme rating system (learn which memes got reactions)
