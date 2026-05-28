-- Run in Supabase → SQL Editor (bucket name: Photos)
-- Fixes: "new row violates row-level security policy" on upload

INSERT INTO storage.buckets (id, name, public)
VALUES ('Photos', 'Photos', false)
ON CONFLICT (id) DO NOTHING;

-- Remove old policies if you ran a previous version
DROP POLICY IF EXISTS "Authenticated users can upload Photos" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated users can update Photos" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated users can read Photos" ON storage.objects;
DROP POLICY IF EXISTS "Users upload to own folder in Photos" ON storage.objects;
DROP POLICY IF EXISTS "Users update own files in Photos" ON storage.objects;
DROP POLICY IF EXISTS "Users read own files in Photos" ON storage.objects;

-- Path layout: {auth.uid()}/{photo_id}/original

CREATE POLICY "Users upload to own folder in Photos"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'Photos'
  AND (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Users update own files in Photos"
ON storage.objects
FOR UPDATE
TO authenticated
USING (
  bucket_id = 'Photos'
  AND (storage.foldername(name))[1] = auth.uid()::text
)
WITH CHECK (
  bucket_id = 'Photos'
  AND (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Users read own files in Photos"
ON storage.objects
FOR SELECT
TO authenticated
USING (
  bucket_id = 'Photos'
  AND (storage.foldername(name))[1] = auth.uid()::text
);
