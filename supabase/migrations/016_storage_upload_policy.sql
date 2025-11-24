-- Migration: Add RLS policy for direct frontend uploads to uploaded-media bucket
--
-- Background: Previously, file uploads went through the backend which used the service role key
-- (bypasses RLS). Now we upload directly from frontend using TUS protocol with the user's
-- access token, which requires explicit RLS policies.
--
-- Run: Applied via Supabase SQL editor or CLI

-- Allow authenticated users to upload files to the uploaded-media bucket
CREATE POLICY "Authenticated users can upload media"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'uploaded-media');

-- Allow authenticated users to read files from the uploaded-media bucket
-- (needed for the public URL to work with authenticated requests)
CREATE POLICY "Authenticated users can read uploaded media"
ON storage.objects
FOR SELECT
TO authenticated
USING (bucket_id = 'uploaded-media');
