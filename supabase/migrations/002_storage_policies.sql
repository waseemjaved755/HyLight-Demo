-- Storage bucket + RLS policies for photo uploads
-- Run in Supabase → SQL Editor (after 001_initial_schema.sql)

-- 1) Create the bucket (skip if you already created "photos" in the Dashboard)
INSERT INTO storage.buckets (id, name, public)
VALUES ('photos', 'photos', false)
ON CONFLICT (id) DO NOTHING;

-- 2) Policies — allow signed-in users to upload/read in the photos bucket
CREATE POLICY "Authenticated users can upload photos"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'photos');

-- Allow signed-in users to update (upsert) their uploads
CREATE POLICY "Authenticated users can update photos"
ON storage.objects
FOR UPDATE
TO authenticated
USING (bucket_id = 'photos')
WITH CHECK (bucket_id = 'photos');

-- Allow signed-in users to read objects in the photos bucket
CREATE POLICY "Authenticated users can read photos"
ON storage.objects
FOR SELECT
TO authenticated
USING (bucket_id = 'photos');
