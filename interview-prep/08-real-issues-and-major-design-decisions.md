# 08. Real Problems I Faced & How I Solved Them

These are the actual bugs, head-scratching moments, and design choices I worked through while building and testing Belong. When an interviewer asks about challenges, bugs, or trade-offs, I can talk through any of these naturally in simple English.

---

## 1. The 11-second race condition where matching returned zero people

When I was running end-to-end simulation tests, onboarding went great and the bot scored traits with high confidence. But as soon as the test checked for matches, the system returned zero candidates. The matching table was completely empty.

I looked at the logs and found a silly race condition. My automated test script had a simple 5-second sleep after onboarding, assuming 5 seconds was plenty of time for background tasks. But inside Docker, the worker was trying to call the Hugging Face API to generate text embeddings, and a DNS lookup delay caused it to hang for 16 seconds before timing out. Because my test checked the database after only 5 seconds, no vector embeddings had been saved yet. The SQL query asked for rows where embeddings were not null, found nothing, and returned zero. 11 seconds later, the worker finally finished and saved the vectors—way too late.

To fix it, I removed the dumb sleep timer. I made the test actively poll the database until the vectors are actually written before triggering the matching query. I also cut the Hugging Face timeout from 30 seconds down to 3 seconds and added a fast local model fallback. If the network or DNS lags, the worker generates local vectors in 50 milliseconds, so it never gets stuck waiting on an external API.

---

## 2. Groq cutting off JSON mid-sentence and crashing the parser

During Stage 2 matching, Groq suddenly started failing with a 400 error saying tool use failed. The fallback code tried to recover, but that immediately hit a 429 rate limit, and then Python crashed with a JSON decode error.

The problem was that my compatibility prompt asked for a lot of detail: evaluating four relationship dimensions, citing verbatim quotes, and writing a narrative summary. I had Groq's maximum output tokens set to 2048. Because the response was so long, Groq ran out of token room and cut the JSON off right in the middle of a sentence. Groq's own validator couldn't parse the broken JSON, so it threw a 400 error. My fallback code naively sent another request right away, which blew past Groq's burst rate limit. When Groq finally responded, it returned an empty string, which completely crashed Python's JSON parser.

I fixed this in three ways:
1. I increased the token limit from 2048 to 4096 so Groq never runs out of space.
2. I noticed that when Groq throws that 400 error, it actually leaves the half-finished JSON text inside the error message under a key called `failed_generation`. So instead of burning another API call, I wrote a small regex helper to pull the JSON straight out of the error message and repair the closing brackets.
3. I added a check for empty responses in the retry loop so an empty string retries cleanly instead of crashing the worker.

---

## 3. The trap of matching people just because they wanted the same thing

Early in testing, the system recommended two users as an amazing "Strong Match" because both were anxious daters who desperately needed constant emotional reassurance. 

My initial prompt told the LLM to do "bidirectional evaluation" without clear rules. The model looked at both profiles and thought: Alice wants reassurance, and Bob also wants reassurance, so they want the same thing! Perfect match! But that is a disaster in relationship psychology. Wanting the same thing doesn't mean you can give it. If both partners panic during stress and need constant reassurance, neither one is able to comfort the other, and they end up clashing.

I fixed this by adding a strict rule to the prompt: never use "they want the same thing" as proof of compatibility. The LLM must strictly check: does what Bob naturally provides match what Alice needs, and does what Alice naturally provides match what Bob needs? I also split the output into two clear buckets: complementary alignments (she needs calm, he provides calm) versus shared alignments (both like hiking and good coffee).

---

## 4. The LLM giving a 0.98 confidence score to wild guesses

The onboarding bot was assigning confidence scores of 0.95 to 0.99 to almost everything a user said. If a user casually mentioned *"I walk my dog on weekends,"* the model extracted *"Values an active outdoor lifestyle"* with a 0.98 confidence score! The system was treating a wild guess with the same weight as a core life value.

The issue was that my prompt just asked for a float between 0.8 and 1.0 without giving the model any boundaries. Naturally, the model just defaulted to the very top of that range for everything.

I fixed this with three changes:
1. I gave the LLM a clear 5-band rubric in the prompt: 0.95 to 1.0 is only for exact word-for-word quotes, 0.80 to 0.94 is for clear paraphrases, 0.60 to 0.79 is for reasonable guesses, and anything below 0.50 is pure speculation.
2. In my Python code, I added a hard filter: any trait with confidence below 0.50 gets thrown away immediately.
3. I added an evidence type flag (`explicit` vs `inference`) so downstream matching knows whether the user literally said it or the bot inferred it.

---

## 5. The LLM stuffing hobbies into values because it hated empty fields

Users who mentioned weekend hiking or cooking were getting those hobbies filed under core values. Other times, things they said about themselves were getting saved under what they wanted in a partner.

LLMs really hate returning empty lists in JSON. When the prompt listed all the trait categories, the model felt pressured to fill every single box, even if it had to force a square peg into a round hole.

To fix it:
1. I added explicit "Do" and "Don't" examples to the prompt (for instance, moral beliefs go in values, but hobbies and weekend activities do not).
2. I added a bold instruction: empty lists are totally fine, and never move information into the wrong category just to fill it up.
3. I added an automatic check at the end of onboarding. If high-priority traits like conflict style or emotional support were left empty, the bot asks one or two gentle follow-up questions so the user can answer them directly, instead of having the AI guess.

---

## 6. Cutting prompt tokens in half to speed up matching and stay under rate limits

When the worker was evaluating 15 candidate pairs in Stage 2, it was taking around 30 seconds, and I was getting uncomfortably close to Groq's tokens-per-minute limit.

I realized I was dumping the entire raw profile JSON straight into the prompt. That JSON had database UUIDs, question codes, timestamps, and confidence numbers. The LLM didn't need any of that technical noise to judge compatibility.

I wrote a small helper function called `_slim_profile()`. Before sending profiles to Groq, it strips out all the IDs, numbers, and timestamps, keeping only the plain text: label, summary, quote, age, and gender. That cut the prompt tokens in half, sped up matching by 40%, and kept API costs under a penny per run.

---

## 7. Giving users an escape hatch for unique personality traits

If a user talked about something unique—like sensory preferences from ADHD, or a specific spiritual tradition—that didn't fit into my eight standard categories, the bot either ignored it or shoved it into the wrong place.

The extractor was too rigidly tied to a fixed list of categories.

To solve this, I added an `other_signals` field to the profile schema as a flexible escape hatch. If a user shares something important that doesn't fit standard boxes, the bot captures it under `other_signals`. It gets included in their text embeddings and passed to the Stage 2 reasoning agent so unique parts of their personality are never lost.

---

## 8. Making match cards sound like a human talking, not a clinical lab report

My earliest match summaries sounded like a cold psychology report: *"User A is quiet when stressed. User B provides active listening. User A values communication."* Nobody wants to read that on a dating app.

The prompt had told the LLM to analyze the pair in the third person using "User A" and "User B".

I rewrote the prompt to speak directly to the user in the second person ("You") and use their match's real first name:
> *"You need quiet space to recharge when stressed, which Alex naturally honors by giving you calm, steady support without rushing to fix things."*

This made the match cards feel warm, personal, and genuinely helpful to read.

---

## How to Talk About Any of These in an Interview

When an interviewer asks: *"Tell me about a bug you ran into"* or *"What was a big engineering challenge you solved?"*, keep it to three simple sentences:

1. **What broke:** *"During full simulation tests, matching was returning zero people even though onboarding finished successfully."*
2. **Why it broke:** *"I found an 11-second race condition. Docker DNS had a delay reaching Hugging Face for embeddings, but my test script checked the database after only 5 seconds before the vectors were saved."*
3. **How I fixed it:** *"I replaced the sleep timer with database polling, and cut the API timeout to 3 seconds with a local fallback so the worker never gets stuck."*
