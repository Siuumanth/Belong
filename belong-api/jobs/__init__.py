"""Jobs module for Belong service.

Handles async job queue lifecycle (pending -> running -> completed/failed)
using PostgreSQL row-level locks (SKIP LOCKED) for workers.
"""
