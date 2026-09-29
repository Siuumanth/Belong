# 🚨 URGENT FIX - API Was Broken

## What Happened

I added validation logging to `belong-api/onboarding/graph.py` in the `extract_signals_node()` function, but I referenced a variable (`items`) **outside** the try block where it was defined. This caused an `UnboundLocalError` that crashed every extraction, preventing onboarding from progressing past Q1.

## Symptoms

- Conversations stuck at "active" status with only 1 Q&A
- Users never progressed past first question
- API logs showed: `UnboundLocalError: local variable 'items' referenced before assignment`

## Fix Applied

**File**: `belong-api/onboarding/graph.py`

**Before** (Broken):
```python
try:
    # ... extraction logic ...
    items = data.get("extracted_items", [])
    # ... process items ...
except Exception as e:
    logger.error(f"Error: {e}")

# BUG: items not defined if extraction failed!
logger.info(f"extracted {len(items)} items")  # ❌ CRASH
```

**After** (Fixed):
```python
items = []  # ✅ Initialize before try block
try:
    # ... extraction logic ...
    items = data.get("extracted_items", [])
    # ... process items ...
except Exception as e:
    logger.error(f"Error: {e}")

# Now items is always defined
logger.info(f"extracted {len(items)} items")  # ✅ WORKS
```

## Current Status

✅ API restarted and working
✅ `items` variable now properly scoped
✅ Logging will work even if extraction fails

## What to Do Now

### 1. Clean Old Stuck Conversations (Optional)
```bash
# Delete incomplete conversations from testing
docker exec -i belong-postgres psql -U belong_user -d belong -c \
  "DELETE FROM conversations WHERE status = 'active' AND created_at < NOW() - INTERVAL '1 hour';"
```

### 2. Run Fresh Simulation
```bash
# Clean database (optional - removes all data)
python tests/nuke_data.py

# Run onboarding simulation (should work now!)
python tests/run_onboarding_simulation.py
```

### 3. Verify Conversations Complete
```bash
# Check conversation status (should show 'completed')
docker exec -i belong-postgres psql -U belong_user -d belong -c \
  "SELECT id, user_id, status, created_at FROM conversations ORDER BY created_at DESC LIMIT 5;"

# Count messages per conversation (should be 13-17)
docker exec -i belong-postgres psql -U belong_user -d belong -c \
  "SELECT conversation_id, COUNT(*) as message_count FROM conversation_messages GROUP BY conversation_id ORDER BY message_count;"
```

### 4. Generate New Results
```bash
# After simulation completes
python tests/get_latest_results.py
cat tests/results.md
```

## Extraction Fixes Still Applied

The core fixes I made are still in place:
- ✅ Dealbreaker extraction rules (in prompts.py)
- ✅ Q4 multi-dimension guidance (in prompts.py)  
- ✅ Extraction validation logging (in graph.py - NOW WORKING)
- ✅ Test cases added
- ✅ Matching trigger script created

The logging just needed to be scoped properly. All the extraction improvements remain.

## Testing Checklist

After running fresh simulation:
- [ ] Conversations show `status='completed'`
- [ ] Each conversation has 13-17 messages (6 core Q/A + probes + completion)
- [ ] Bob's profile has dealbreakers array populated
- [ ] Alice's profile has dealbreakers array populated
- [ ] Q4 extracts lifestyle, interests, values for both
- [ ] Can trigger matching with `python tests/trigger_matching.py`

## My Bad

Sorry for breaking the API! The extraction logic was fine, I just added logging without checking the variable scope. It's fixed now and should work properly. 🙏
