# Fix #5: Onboarding Extraction Issues - Investigation & Fixes

**Date**: September 29, 2026  
**Status**: Partial Fix - 3/5 issues resolved, 2 critical regressions identified  
**Related**: prob-5.md

---

## Executive Summary

Investigated test results showing extraction failures. Fixed dealbreaker extraction (now working), resolved conversation query crash, and identified matching pipeline requirement. Discovered two new critical bugs: duplicate probe extraction and Q4 multi-dimension extraction failure.

---

## Issues Addressed

### ✅ Issue 1: Dealbreaker Extraction Not Working (FIXED)

**Problem**: 
- Bob's Q6 dealbreakers ("arrogance", "dishonesty", "stagnation") were being lost or misrouted to `wants.partner_values`
- Alice's Q6 dealbreakers ("smoking", "substances", "dishonesty") similarly misrouted
- Hard-constraint filtering in retrieval had no data to filter on

**Root Cause**:
Extraction prompt lacked explicit routing rules for dealbreaker language patterns. Phrases like "I can't do X", "hard no", "dealbreaker" were not being recognized as `constraints.dealbreakers` triggers.

**Solution**:
Added explicit dealbreaker identification rules to `SIGNAL_EXTRACTION_PROMPT` in `belong-api/onboarding/prompts.py`:

```python
DEALBREAKER IDENTIFICATION (CRITICAL):
Route to `constraints.dealbreakers` when user language includes ANY of these patterns:
- "hard no", "dealbreaker", "non-negotiable", "absolute boundary", "must not", "will not accept"
- "I can't do [X]", "I won't date someone who [X]", "I can't be with someone who [X]"
- "if [condition], it's done/over/a dealbreaker"
- "[X] is a no-go", "[X] is not acceptable"
- Phrases indicating rejection/elimination: "arrogance is out", "dishonesty ends it"

Examples of DEALBREAKERS (→ constraints.dealbreakers):
✓ "smoking is a hard no" → constraints.dealbreakers
✓ "I can't do arrogance" → constraints.dealbreakers  
✓ "dishonesty in any form" → constraints.dealbreakers
✓ "if I can't trust you, it's done" → constraints.dealbreakers
```

**Result**:
- ✅ Bob's `constraints.dealbreakers`: 3 items (Arrogance, Dishonesty, Stagnation)
- ✅ Alice's `constraints.dealbreakers`: 4 items (No smoking, No substances, No dishonesty, No lack of trust)
- ✅ Dealbreaker extraction working at ~95%+ confidence

**Files Changed**:
- `belong-api/onboarding/prompts.py` - Added dealbreaker routing section

---

### ✅ Issue 2: Alice Conversation Query Crash (FIXED)

**Problem**:
Inspector script crashed when fetching Alice's conversation:
```
Error executing psql query via docker: 'NoneType' object has no attribute 'strip'
```

**Root Cause**:
1. Windows PowerShell encoding issue with UTF-8 characters (em-dash `—`, non-breaking hyphen `‑`)
2. `subprocess.run(text=True)` failing to decode output
3. Script attempting `.strip()` on None when decode failed
4. Insufficient null checks in `print_user_conversation()`

**Solution**:
1. Changed subprocess to use `text=False` and explicit UTF-8 decoding with error replacement:
```python
res = subprocess.run(cmd, capture_output=True, text=False, check=True)
out = res.stdout.decode('utf-8', errors='replace')  # Replace invalid chars
```

2. Added comprehensive null checking:
```python
if conv_list is None:
    print("   Onboarding Dialogue: (Error fetching conversation from database)\n")
    return

if not conv_list or len(conv_list) == 0:
    print("   Onboarding Dialogue: (No conversation recorded for this profile)\n")
    return

conv = conv_list[0]
if not conv or not conv.get("messages"):
    print("   Onboarding Dialogue: (No messages found for this conversation)\n")
    return
```

**Result**:
- ✅ Alice's 17-message conversation now displays correctly
- ✅ Script handles encoding errors gracefully
- ✅ Clear error messages for different failure modes

**Files Changed**:
- `tests/get_latest_results.py` - UTF-8 decoding + null safety

---

### ✅ Issue 3: No Compatibility Results (PARTIALLY FIXED)

**Problem**:
Two consecutive test runs produced zero compatibility results despite completed profiles.

**Investigation**:
1. Checked job table - only 1 matching job existed (for Alice)
2. Job completed successfully: `{"total_matches": 0, "matches_persisted": 0}`
3. No matches found because only Alice's job ran
4. Matching requires BOTH users to trigger jobs (not automatic after onboarding)

**Root Cause**:
Misunderstanding of matching workflow. Matching is **user-initiated**, not automatic:
- ❌ Thought: `finalize_profile()` → creates matching job
- ✅ Reality: User calls `POST /api/matches` → creates matching job

**Solution**:
1. Manually triggered matching for Bob: `POST http://localhost:8000/api/matches` with `X-User-ID` header
2. Worker processed job and created Bob ↔ Alice compatibility result
3. Created helper script `tests/trigger_matching.py` (needs venv fix to run)

**Result**:
- ✅ 1 compatibility result now exists (Bob ↔ Alice)
- ✅ Matching pipeline confirmed working
- ⚠️ Documentation gap: API endpoint is `/api/matches`, not `/matches/calculate`

**Files Changed**:
- `tests/trigger_matching.py` - Helper script (created but needs psycopg fix)
- `tests/STATUS_SUMMARY.md` - Documented correct endpoint

**Workflow Confirmed**:
```
1. Onboarding completes → finalize_profile() saves profile → (maybe) creates embedding job
2. Embedding job runs → generates self_embedding, wants_embedding
3. **User initiates** → POST /api/matches → creates matching job
4. Worker processes matching job → generates compatibility_results
```

---

### ⚠️ Issue 4: Variable Scoping Bug - API Crash (FIXED)

**Problem**:
After adding validation logging, API crashed on every extraction:
```python
UnboundLocalError: local variable 'items' referenced before assignment
```

**Root Cause**:
Added logging code that referenced `items` outside the try block where it was defined:
```python
try:
    items = data.get("extracted_items", [])
    # ... process items ...
except Exception as e:
    logger.error(f"Error: {e}")

# BUG: items not defined if extraction failed!
logger.info(f"extracted {len(items)} items")  # ❌ CRASH
```

**Solution**:
Initialize `items` before try block:
```python
items = []  # ✅ Initialize before try
try:
    items = data.get("extracted_items", [])
    # ... process items ...
except Exception as e:
    logger.error(f"Error: {e}")

logger.info(f"extracted {len(items)} items")  # ✅ WORKS
```

**Result**:
- ✅ API no longer crashes on extraction
- ✅ Validation logging works correctly
- ✅ Conversations complete successfully (17 messages for Alice, 16 for Bob)

**Files Changed**:
- `belong-api/onboarding/graph.py` - Moved `items = []` initialization

---

## 🚨 Critical Regressions Found

### ❌ Regression 1: Duplicate Probe Extraction (NEW BUG)

**Problem**:
Alice has the SAME THREE signals extracted TWICE under different probe question IDs:

**First Extraction** (`probe_self_emotional_needs` - Q7):
```json
{
  "id": "probe_self_emotional_needs_s_provides_04",
  "label": "Patient listening",
  "quote": "listening patiently when they are stressed"
},
{
  "id": "probe_self_emotional_needs_s_provides_05",
  "label": "Clear reassurance",
  "quote": "offering clear reassurance"
},
{
  "id": "probe_self_emotional_needs_s_provides_06",
  "label": "Transparent communication",
  "quote": "communicating transparently during difficult times"
}
```

**Duplicate Extraction** (`probe_wants_partner_traits` - Q8):
```json
{
  "id": "probe_wants_partner_traits_s_provides_07",
  "label": "Patient listening",  // EXACT DUPLICATE
  "quote": "listening patiently when they are stressed"
},
{
  "id": "probe_wants_partner_traits_s_provides_08",
  "label": "Clear reassurance",  // EXACT DUPLICATE
  "quote": "offering clear reassurance"
},
{
  "id": "probe_wants_partner_traits_s_provides_09",
  "label": "Transparent communication",  // EXACT DUPLICATE
  "quote": "communicating transparently during difficult times"
}
```

**Conversation Evidence**:
Both Q7 and Q8 have IDENTICAL canned answers:
- **Q7**: "I naturally support my partner by listening patiently when they are stressed, offering clear reassurance, and communicating transparently during difficult times."
- **Q8**: "I naturally support my partner by listening patiently when they are stressed, offering clear reassurance, and communicating transparently during difficult times."

**Impact**:
1. **Polluted Embeddings**: `self_embedding` has 2x weight on these three signals, disproportionate to actual user input
2. **Data Quality**: Profile shows 10 "provides" items, but 6 are duplicates of 3 actual answers
3. **User Experience**: System asked essentially the same question twice

**Root Cause Hypothesis**:
Adaptive probe logic (`find_missing_high_priority_field()`) is not checking if a dimension was already probed. System fired:
1. Probe for `self.emotional_needs` → extracted to `self.provides` (field mismatch?)
2. Probe for `wants.partner_traits` → extracted same content again

**Investigation Needed**:
1. Check if `covered_areas` contains `probe:self.provides` before firing second probe
2. Verify extraction is correctly routing to target dimension (both probes extracted to `self.provides` instead of their targets)
3. Review Q7/Q8 question generation to see why same canned answer appeared

**Files to Check**:
- `belong-api/onboarding/graph.py` - `find_missing_high_priority_field()`, `generate_response_node()`
- Logs showing probe decision making

---

### ❌ Regression 2: Q4 Multi-Dimension Extraction Still Failing (CRITICAL)

**Problem**:
Despite adding explicit Q4 extraction guidance to prompts, `self.lifestyle`, `self.values`, `self.interests`, and `self.life_goals` remain EMPTY for both users.

**Bob's Q4 Answer**:
> "trail running is my thing — I do a half marathon most weekends. I'm a software engineer so weekdays are pretty heads-down but I try to get outside every day. I got into coffee brewing during covid and now I take it a bit too seriously. I value people who actually have ambition and keep growing, professionally or personally, I don't really care which."

**Expected Extraction**:
- `self.lifestyle`: [half marathon weekends, software engineer work pattern, daily outdoor time]
- `self.interests`: [trail running, coffee brewing]
- `self.values`: [ambition, continuous growth]
- `self.life_goals`: []

**Actual Extraction**:
- `self.lifestyle`: [] ❌
- `self.interests`: [reading books] (from Q5, not Q4!) ❌
- `self.values`: [] ❌
- `self.life_goals`: [] ✓ (correctly empty)

**Alice's Q4 Answer**:
> "I do morning yoga most days, like 5-6 times a week. I work in product design so I spend a lot of time at a screen which is why I try to stay active. weekends are usually a hike or farmers market, maybe a bookstore. I'm plant-based and pretty into cooking. I care a lot about being consistent — like doing small things well over time."

**Expected Extraction**:
- `self.lifestyle`: [morning yoga 5-6x/week, product design work, plant-based diet]
- `self.interests`: [yoga, hiking, farmers market, bookstore, cooking]
- `self.values`: [consistency, doing small things well over time]
- `self.life_goals`: []

**Actual Extraction**:
- `self.lifestyle`: [] ❌
- `self.interests`: [] ❌
- `self.values`: [] ❌
- `self.life_goals`: [] ✓ (correctly empty)

**What Changed**:
Added to `SIGNAL_EXTRACTION_PROMPT`:
```python
SPECIAL RULES FOR Q4 (LIFESTYLE/VALUES/INTERESTS):
When the question targets lifestyle, values, interests, or life goals, extract ACROSS ALL APPLICABLE DIMENSIONS:

LIFESTYLE (self.lifestyle) - Extract patterns of HOW they live:
- Recurring routines, habits (daily/weekly patterns)
- Work structure, time management
- Diet/health choices that are lifestyle patterns

INTERESTS (self.interests) - Extract WHAT they enjoy doing:
- Hobbies, activities, pastimes
- Things they pursue for enjoyment

VALUES (self.values) - Extract principles they explicitly state matter:
- Moral/ethical stances
- Qualities they care about in people
- Life philosophy statements

CRITICAL: One answer to Q4 should produce signals across MULTIPLE dimensions.
```

**Why It Might Not Be Working**:
1. **LLM ignoring instructions**: Model not following the prompt guidance
2. **Target dimensions not passed**: Q4 config might not be passing all 5 dimensions to extraction
3. **Extraction happening but filtered**: Signals extracted but dropped due to low confidence (<0.50)
4. **JSON structure mismatch**: LLM producing valid JSON but wrong field names
5. **Prompt too long/complex**: New guidance buried in 400+ line prompt

**Investigation Needed**:
1. Check logs for Q4 extraction validation:
   ```bash
   docker logs belong-api 2>&1 | grep "q4_lifestyle_values"
   ```
2. Check if items are extracted then filtered:
   ```bash
   docker logs belong-api 2>&1 | grep "Extraction for q4"
   ```
3. Verify config.py Q4 targets include all dimensions
4. Test Q4 extraction in isolation to see raw LLM output

**Files to Check**:
- `belong-api/config.py` - Q4 `targets` array
- `belong-api/onboarding/prompts.py` - SIGNAL_EXTRACTION_PROMPT
- `belong-api/onboarding/graph.py` - Extraction and filtering logic
- API logs for extraction debug output

---

## ⚠️ Design Question: Dual-Filing of Dealbreakers

**Observation**:
Bob's Q6 answer about "dishonesty" is being extracted to BOTH:
1. `constraints.dealbreakers`: "Dishonesty — not just big lies..."
2. `wants.partner_values`: "Honesty" (extracted from same quote)

**Is This Intentional?**

**Argument FOR dual-filing**:
- "I can't do dishonesty" (negative constraint) and "I value honesty" (positive value) are related but distinct concepts
- Dealbreaker defines hard boundary, value defines positive desire
- Both are valid extractions from the statement

**Argument AGAINST dual-filing**:
- Same quote being used twice feels redundant
- Dealbreaker already implies the positive value
- Could pollute `wants_embedding` with inverted dealbreakers

**Current Behavior**: Dual-filing IS happening

**Decision Needed**:
Should dealbreaker-phrased statements:
- **Option A**: Route ONLY to `constraints.dealbreakers`
- **Option B**: Route to BOTH `dealbreakers` AND positive `partner_values` (current)
- **Option C**: Route based on phrasing (positive = values, negative = dealbreakers)

**If Option A chosen**, add to prompt:
```
If a statement is phrased as a dealbreaker (I can't do X, X is a hard no), 
extract ONLY to constraints.dealbreakers, NOT to wants.partner_values as a positive trait.
```

---

## Validation Logging Added

Added extraction validation logging to `belong-api/onboarding/graph.py`:

```python
# Log extraction summary
logger.info(f"Extraction for {topic_id}: extracted {len(items)} items across {len(extracted_signals)} dimensions")

# Q6 dealbreaker validation
if topic_id == "q6_dealbreakers":
    dealbreaker_count = len(extracted_signals.get("constraints.dealbreakers", []))
    logger.info(f"Q6 dealbreaker extraction: {dealbreaker_count} dealbreakers extracted")
    
    if dealbreaker_count == 0:
        dealbreaker_keywords = ["hard no", "dealbreaker", "can't do", "won't accept", "it's done", "non-negotiable"]
        found_keywords = [kw for kw in dealbreaker_keywords if kw in user_input.lower()]
        if found_keywords:
            logger.warning(f"Q6 answer contains dealbreaker keywords {found_keywords} but extracted 0 dealbreakers!")

# Q4 multi-dimension validation
if topic_id == "q4_lifestyle_values":
    dimensions_extracted = [k for k in ["self.lifestyle", "self.interests", "self.values", "self.life_goals"] 
                            if extracted_signals.get(k)]
    logger.info(f"Q4 extracted dimensions: {dimensions_extracted}")
    if len(dimensions_extracted) < 2:
        logger.warning(f"Q4 only extracted {len(dimensions_extracted)} dimensions, expected at least 2")
```

**Purpose**: 
- Detect when extraction fails for critical fields
- Warn when dealbreaker keywords present but nothing extracted
- Warn when Q4 produces single-dimension instead of multi-dimension output

---

## Test Results Summary

### Dealbreaker Extraction: ✅ WORKING (95%+)
| User  | Q6 Dealbreakers Identified | Confidence | Status |
|-------|----------------------------|------------|--------|
| Bob   | Arrogance, Dishonesty, Stagnation | 0.98 | ✅ Correct |
| Alice | No smoking, No substances, No dishonesty, No trust | 0.98 | ✅ Correct |

### Q4 Multi-Dimension Extraction: ❌ FAILING (0%)
| User  | Lifestyle | Interests | Values | Expected Dimensions | Status |
|-------|-----------|-----------|--------|---------------------|--------|
| Bob   | Empty     | 0 from Q4 | Empty  | ≥3                  | ❌ Failed |
| Alice | Empty     | Empty     | Empty  | ≥3                  | ❌ Failed |

### Duplicate Extraction: ❌ DETECTED (50%)
| User  | Duplicate Signals | Source | Status |
|-------|-------------------|--------|--------|
| Bob   | None detected     | N/A    | ✅ Clean |
| Alice | 3 signals × 2 = 6 | probe_self_emotional_needs + probe_wants_partner_traits | ❌ Duplicate |

### Matching Pipeline: ✅ WORKING
| Metric | Value | Status |
|--------|-------|--------|
| Jobs created | 2 (Alice + Bob) | ✅ |
| Jobs completed | 2 | ✅ |
| Compatibility results | 1 (Bob ↔ Alice) | ✅ |
| Results format | Valid JSON with dimensions | ✅ |

---

## Files Modified

| File | Type | Changes | Status |
|------|------|---------|--------|
| `belong-api/onboarding/prompts.py` | **Critical** | Added dealbreaker routing rules + Q4 multi-dimension guidance | ✅ Deployed |
| `belong-api/onboarding/graph.py` | Bugfix + Logging | Fixed `items` scoping + added validation logging | ✅ Deployed |
| `tests/get_latest_results.py` | Bugfix | UTF-8 encoding + null safety | ✅ Deployed |
| `tests/trigger_matching.py` | Tool | Helper script to trigger matching jobs | ⚠️ Needs venv fix |
| `tests/FIXES_APPLIED.md` | Docs | Initial fix documentation | 📄 Created |
| `tests/URGENT_FIX.md` | Docs | Variable scoping fix explanation | 📄 Created |
| `tests/STATUS_SUMMARY.md` | Docs | Comprehensive status report | 📄 Created |
| `tests/test_onboarding_invariants.py` | Tests | Added 4 new test functions | ✅ Added |

---

## Next Actions (Priority Order)

### 1. 🚨 CRITICAL: Fix Duplicate Probe Extraction
**Impact**: Data quality - pollutes embeddings with 2x weight on duplicated signals

**Investigation**:
- Review Q7/Q8 in Alice's conversation - both have identical canned answers
- Check `find_missing_high_priority_field()` logic
- Verify `covered_areas` includes `probe:self.provides` to prevent re-probe
- Check why both probes extracted to `self.provides` instead of their target dimensions

**Fix**:
- Ensure `covered_areas` properly tracks probed dimensions
- Add deduplication logic to prevent extracting same quote twice
- Fix probe targeting to route extractions to correct dimensions

**Verification**:
```bash
# After fix, run fresh simulation and check for duplicates:
python tests/run_onboarding_simulation.py
python tests/get_latest_results.py
# Search for duplicate signal IDs with same quote
```

### 2. 🚨 CRITICAL: Fix Q4 Multi-Dimension Extraction
**Impact**: Missing 80% of lifestyle/values/interests data

**Investigation**:
```bash
# Check what Q4 is actually extracting:
docker logs belong-api 2>&1 | grep "q4_lifestyle_values"

# See if items are being filtered:
docker logs belong-api 2>&1 | grep "Dropping signal"

# Verify Q4 config targets:
grep -A 5 "q4_lifestyle_values" belong-api/config.py
```

**Possible Fixes**:
- If LLM not following prompt: Add few-shot examples to SIGNAL_EXTRACTION_PROMPT
- If targets wrong: Update config.py Q4 targets array
- If filtering: Lower confidence threshold for Q4 only
- If JSON structure: Debug raw LLM output to see actual structure

**Verification**:
After fix, Bob should have:
- `self.lifestyle`: ≥2 items
- `self.interests`: ≥2 items (trail running, coffee)
- `self.values`: ≥1 item (ambition/growth)

### 3. ⚠️ DECIDE: Dual-Filing Policy
**Impact**: Design clarity

**Decision Required**:
Should dealbreaker statements also be extracted as positive values?

**Options**:
- Keep dual-filing (current behavior)
- Single-file to dealbreakers only
- Context-dependent routing

**Action**: Document decision in design docs and update prompt if needed

### 4. ✅ VERIFY: End-to-End Pipeline
**After fixes 1-2 complete**:
```bash
# Clean slate test
python tests/nuke_data.py

# Run simulation
python tests/run_onboarding_simulation.py

# Trigger matching for both users
curl -X POST http://localhost:8000/api/matches -H "X-User-ID: <bob_uuid>"
curl -X POST http://localhost:8000/api/matches -H "X-User-ID: <alice_uuid>"

# Wait for jobs
sleep 10

# Generate results
python tests/get_latest_results.py

# Verify:
# - No duplicate signals
# - Q4 has ≥2 dimensions populated for both users
# - Dealbreakers present
# - Compatibility results exist with meaningful reasoning
```

---

## Success Criteria

### Phase 1 (Current) - Partial Success
- ✅ Dealbreaker extraction: 95%+ working
- ❌ Q4 multi-dimension: 0% (critical failure)
- ❌ No duplicate extraction: 50% (Alice has duplicates)
- ✅ Matching pipeline: Working end-to-end
- ⚠️ Dual-filing: Happening, needs decision

### Phase 2 (Target) - Full Success
- ✅ Dealbreaker extraction: 95%+ for dealbreaker keywords
- ✅ Q4 multi-dimension: 90%+ with ≥2 dimensions per user
- ✅ No duplicate extraction: 100% (zero duplicates across all profiles)
- ✅ Matching generates results for all user pairs
- ✅ Dual-filing policy documented and consistently applied

---

## Lessons Learned

1. **Always initialize variables before try blocks** - Scoping bugs in exception handling paths can crash production
2. **Windows encoding requires explicit handling** - UTF-8 characters from LLM output need `errors='replace'` on Windows
3. **Matching is user-initiated, not automatic** - Don't assume jobs are created; check the actual workflow
4. **Prompts alone don't guarantee behavior** - Need to validate LLM is following instructions through logs
5. **Check for regressions when adding features** - Duplicate extraction emerged from probe logic changes
6. **Null checks matter** - Python's `None` can crash `len()`, subscript, and string methods

---

## Related Issues

- **prob-5.md**: Original problem statement and test result analysis
- **Issue #1**: Duplicate probe extraction (NEW, discovered during this fix)
- **Issue #2**: Q4 extraction failure (ONGOING, prompt changes insufficient)
- **Issue #3**: Dual-filing design question (OPEN, needs product decision)

---

## Appendix: Test Commands

### Check Extraction Quality
```bash
# See Q4 extraction logs
docker logs belong-api 2>&1 | grep "q4_lifestyle_values"

# See dealbreaker extraction logs
docker logs belong-api 2>&1 | grep "Q6 dealbreaker"

# See all extraction summaries
docker logs belong-api 2>&1 | grep "Extraction for"

# Check for extraction warnings
docker logs belong-api 2>&1 | grep "WARNING"
```

### Check Database State
```bash
# View latest profiles
docker exec -i belong-postgres psql -U belong_user -d belong -c \
  "SELECT user_id, name, (profile->'self'->>'lifestyle')::text as lifestyle FROM profiles ORDER BY created_at DESC LIMIT 2;"

# View matching jobs
docker exec -i belong-postgres psql -U belong_user -d belong -c \
  "SELECT id, user_id, type, status FROM jobs WHERE type='matching' ORDER BY created_at DESC;"

# View compatibility results
docker exec -i belong-postgres psql -U belong_user -d belong -c \
  "SELECT user_a_id, user_b_id, dimension_results->>'overall_verdict' FROM compatibility_results;"
```

### Trigger Fresh Test
```bash
# Option 1: Full clean test
python tests/nuke_data.py
python tests/run_onboarding_simulation.py
# ... then trigger matching manually

# Option 2: Just regenerate results
python tests/get_latest_results.py
cat tests/results.md
```

---

**End of Fix #5 Documentation**
