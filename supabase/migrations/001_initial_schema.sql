-- Run in Supabase SQL Editor (Dashboard → SQL → New query)
-- Enable PostGIS first: Database → Extensions → postgis → Enable

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supabase_user_id UUID NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    avatar_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS photos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    storage_key_original TEXT NOT NULL,
    storage_key_medium TEXT,
    storage_key_thumb TEXT,
    mime_type VARCHAR(64) NOT NULL,
    size_bytes BIGINT NOT NULL,
    width INTEGER,
    height INTEGER,
    taken_at TIMESTAMPTZ,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    altitude_m REAL,
    ai_description TEXT,
    ai_status VARCHAR(16) NOT NULL DEFAULT 'pending'
        CHECK (ai_status IN ('pending', 'done', 'failed', 'skipped')),
    ai_provider VARCHAR(32),
    exif JSONB,
    visibility VARCHAR(16) NOT NULL DEFAULT 'private'
        CHECK (visibility IN ('private', 'unlisted', 'public')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    photo_id UUID NOT NULL REFERENCES photos(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body TEXT NOT NULL CHECK (length(body) BETWEEN 1 AND 2000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_photos_location ON photos USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_photos_owner ON photos (owner_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_photos_created ON photos (created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_comments_photo ON comments (photo_id, created_at DESC) WHERE deleted_at IS NULL;

-- Supabase Storage: create bucket "photos" (public or private per your policy)
