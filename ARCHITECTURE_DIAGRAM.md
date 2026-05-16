# CYFERNAUT ADAPTIVE LEARNING ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                    DISCORD USER MESSAGE                         │
│                          (User sends)                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │   Message Processing & Context     │
        │   - Build conversation history     │
        │   - Get user & channel info        │
        └────────────┬───────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────┐
        │     Gemini AI Response Gen          │
        │     - Uses master prompt            │
        │     - Generates response            │
        └────────────┬───────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────┐
        │    TONE & CATEGORY DETECTION       │
        │  (detect_response_tone)            │
        │                                    │
        │  Analyzes response text:           │
        │  - Detects tone (6 types)          │
        │  - Detects category (7 types)      │
        └────────────┬───────────────────────┘
                     │
        ┌────────────┴───────────────┐
        │                            │
        ▼                            ▼
    ┌─────────────┐        ┌──────────────────┐
    │   Tone      │        │    Category      │
    ├─────────────┤        ├──────────────────┤
    │ • savage    │        │ • stupid         │
    │ • casual    │        │ • cringe         │
    │ • supportive│        │ • roast          │
    │ • disgusted │        │ • insane         │
    │ • hilarious │        │ • emotional      │
    │ • hindi_    │        │ • suspicious     │
    │   playful   │        │ • normal         │
    └─────────────┘        └──────────────────┘
        │                            │
        └────────────┬───────────────┘
                     │
                     ▼
    ┌──────────────────────────────────────────┐
    │  LEARNING ENGINE - Record Response       │
    │  (adaptive_learner.record_bot_response)  │
    │                                          │
    │  Creates unique response_id              │
    │  Stores: tone, category, user, channel   │
    │  Records timestamp                       │
    └────────────┬─────────────────────────────┘
                 │
        ┌────────▼────────────────────────────┐
        │   SEND RESPONSE TO DISCORD          │
        │   - Line by line                    │
        │   - Track message IDs               │
        │   - Optional: Send meme             │
        └────────┬───────────────────────────┘
                 │
                 ▼
    ┌────────────────────────────────────┐
    │  MESSAGE TRACKING                  │
    │  response_tracking dict:           │
    │  {message_id → response_id}        │
    └────────────┬───────────────────────┘
                 │
                 ▼
    ┌────────────────────────────────────┐
    │  WAITING FOR REACTIONS/REPLIES     │
    │  on_reaction_add event             │
    │                                    │
    │  Monitor incoming reactions        │
    │  Count reactions & replies         │
    └────────────┬───────────────────────┘
                 │
                 ▼
    ┌────────────────────────────────────────┐
    │  ENGAGEMENT CALCULATION                │
    │  Score = (reactions × 10)              │
    │        + (replies × 15)                │
    │  Result: 0-100 engagement score        │
    └────────────┬───────────────────────────┘
                 │
                 ▼
    ┌──────────────────────────────────────────┐
    │  UPDATE LEARNING DATABASE                │
    │  adaptive_learner.learn_from_reactions() │
    │                                          │
    │  1. Update response_metrics table        │
    │     - reactions_count                    │
    │     - replies_count                      │
    │     - engagement_score                   │
    └────────────┬─────────────────────────────┘
                 │
                 ▼
    ┌──────────────────────────────────────────┐
    │  2. UPDATE USER PROFILE                  │
    │     user_profiles table                  │
    │                                          │
    │     - If tone worked: increase weight    │
    │     - Update humor_sensitivity           │
    │     - Update roast_tolerance             │
    │     - Add to favorite_jokes              │
    └────────────┬─────────────────────────────┘
                 │
                 ▼
    ┌──────────────────────────────────────────┐
    │  3. UPDATE CHANNEL DYNAMICS              │
    │     channel_dynamics table               │
    │                                          │
    │     - Update avg_engagement              │
    │     - Update tone_preference             │
    │     - Update humor_level                 │
    │     - Update formality_level             │
    └────────────┬─────────────────────────────┘
                 │
                 ▼
    ┌────────────────────────────────────────────┐
    │  LEARNING COMPLETE                        │
    │  Console Output:                          │
    │  [Cyfernaut] 📚 Learning recorded:        │
    │  [Cyfernaut] 📊 Learning updated from:    │
    │                                           │
    │  Bot now has data for next interaction    │
    └────────────┬───────────────────────────────┘
                 │
        ┌────────┴─────────────────────────┐
        │                                  │
        ▼                                  ▼
    ┌──────────────────┐        ┌──────────────────────┐
    │  NEXT RESPONSE   │        │  CHANNEL SEES        │
    │  will use:       │        │  increasingly:       │
    │                  │        │                      │
    │  • User's        │        │ • Personalized tone  │
    │    preferred     │        │ • Appropriate style  │
    │    tone          │        │ • Better timing      │
    │  • Learned       │        │ • Funnier responses  │
    │    category      │        │ • Human-like humor   │
    │  • Channel       │        │                      │
    │    dynamics      │        │ BOT BECOMES MORE     │
    │  • User humor    │        │ HUMAN WITH EVERY     │
    │    sensitivity   │        │ INTERACTION          │
    └──────────────────┘        └──────────────────────┘


DATABASE SCHEMA
═════════════════════════════════════════════════════════════════

response_metrics                    user_profiles
┌──────────────────────┐          ┌──────────────────────┐
│ response_id (PK)     │          │ user_id (PK)         │
│ category             │          │ preferred_tone       │
│ user_id              │          │ humor_sensitivity    │
│ channel_id           │          │ roast_tolerance      │
│ timestamp            │          │ interaction_count    │
│ response_text        │          │ favorite_jokes_json  │
│ user_message         │          │ last_interaction     │
│ reactions_count      │          └──────────────────────┘
│ replies_count        │
│ engagement_score     │          channel_dynamics
│ humor_rating         │          ┌──────────────────────┐
│ tone                 │          │ channel_id (PK)      │
└──────────────────────┘          │ avg_engagement       │
                                  │ tone_preference      │
                                  │ best_response_type   │
                                  │ interaction_count    │
                                  │ humor_level          │
                                  │ formality_level      │
                                  └──────────────────────┘


COMMAND FLOW - !stats
═════════════════════════════════════════════════════════════════

!stats command
    ↓
Check if admin
    ↓
get_learning_stats()
    ├─ Total responses recorded
    ├─ Average engagement
    ├─ Most effective tone
    ├─ Best category
    └─ Unique users
    ↓
get_top_performing_responses(limit=3)
    ├─ Highest engagement score responses
    ├─ Top tone used
    └─ Top category
    ↓
Display formatted stats
    ├─ 📚 Total responses
    ├─ Average engagement /100
    ├─ 🔥 Most effective tone
    ├─ Best category
    ├─ Unique users learned
    └─ 🏆 Top 3 responses
    ↓
Send to Discord


ADAPTATION STAGES
═════════════════════════════════════════════════════════════════

Stage 1: First Chat (0-10 interactions)
┌─────────────────────────┐
│ • Generic responses     │
│ • Default personality   │
│ • No personalization    │
│ • Bot is learning...    │
└─────────────────────────┘

Stage 2: Early Learning (10-50 interactions)
┌─────────────────────────┐
│ • Detects humor type    │
│ • Learns channel vibe   │
│ • Basic adaptation      │
│ • Consistent tone       │
└─────────────────────────┘

Stage 3: Active Adaptation (50-200 interactions)
┌─────────────────────────┐
│ • Knows user well       │
│ • Personalized humor    │
│ • Adapts mid-convo      │
│ • Predicts reactions    │
└─────────────────────────┘

Stage 4: Expert Level (200+ interactions)
┌─────────────────────────┐
│ • Nearly human-like     │
│ • Perfect timing        │
│ • Inside jokes          │
│ • Genuine understanding │
└─────────────────────────┘
```
