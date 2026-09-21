-- Belong Migration: 006_add_name_to_profiles.sql
-- Description: Add optional name column to profiles table

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS name TEXT;
