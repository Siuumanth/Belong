# TestAB — Individual 2-User Persona Simulation Suite

This directory contains standalone test scripts for isolated **2-user (Alice & Bob)** persona simulations.

## File Overview

- **`run_custom_simulation.py`**: Customizable interactive script that runs Alice & Bob through:
  1. Profile Creation (`POST /profiles`)
  2. Multi-turn AI Onboarding dialogue
  3. Trait extraction & vector embeddings (`pgvector`)
  4. Pairwise compatibility matching & score retrieval

## How to Run

Make sure `belong-api` is running on port 8000, then execute:

```bash
python tests/testAB/run_custom_simulation.py
```
