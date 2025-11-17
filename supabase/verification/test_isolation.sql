-- ============================================================================
-- MULTI-TENANCY ISOLATION TEST
-- ============================================================================
-- This script demonstrates what users in different orgs can and cannot see
-- ============================================================================

-- SCENARIO: Two users in different organizations
-- User A in Organization A
-- User B in Organization B

-- ============================================================================
-- SETUP: Get two different users (if they exist)
-- ============================================================================

-- Find the first two users in different organizations
WITH user_sample AS (
  SELECT
    u.id as user_id,
    u.organization_id,
    o.name as org_name,
    ROW_NUMBER() OVER (PARTITION BY u.organization_id ORDER BY u.created_at) as rn
  FROM users u
  JOIN organizations o ON o.id = u.organization_id
)
SELECT
  user_id,
  organization_id,
  org_name,
  'User ' || ROW_NUMBER() OVER (ORDER BY organization_id, user_id) as label
FROM user_sample
WHERE rn = 1
LIMIT 2;

-- ============================================================================
-- TEST 1: Articles are GLOBALLY READABLE
-- ============================================================================
-- Both users can see all articles in the articles table
-- (This query would work for any authenticated user)

SELECT
  'Global Article Access' as test_name,
  'All users can read all articles' as expected_result,
  COUNT(*) as total_articles_visible
FROM articles;

-- ============================================================================
-- TEST 2: "My Articles" are ORGANIZATION-SCOPED
-- ============================================================================
-- Each user only sees their own saved articles via article_users

-- User A's saved articles (replace with actual user_id to test)
-- SELECT
--   'User A Saved Articles' as test_name,
--   COUNT(*) as user_a_saved_count,
--   organization_id
-- FROM article_users
-- WHERE user_id = 'USER-A-ID'
-- GROUP BY organization_id;

-- User B's saved articles (replace with actual user_id to test)
-- SELECT
--   'User B Saved Articles' as test_name,
--   COUNT(*) as user_b_saved_count,
--   organization_id
-- FROM article_users
-- WHERE user_id = 'USER-B-ID'
-- GROUP BY organization_id;

-- ============================================================================
-- TEST 3: Content Sources are ORGANIZATION-SCOPED
-- ============================================================================
-- Each organization has its own RSS feeds and newsletter subscriptions

SELECT
  o.name as organization,
  COUNT(cs.id) as content_sources_count,
  STRING_AGG(cs.url, ', ') as source_urls
FROM organizations o
LEFT JOIN content_sources cs ON cs.organization_id = o.id
GROUP BY o.id, o.name
ORDER BY o.name;

-- ============================================================================
-- TEST 4: Content Queue is ORGANIZATION-SCOPED
-- ============================================================================
-- Each organization has its own discovery queue

SELECT
  o.name as organization,
  COUNT(cq.id) as queued_items_count
FROM organizations o
LEFT JOIN content_queue cq ON cq.organization_id = o.id
GROUP BY o.id, o.name
ORDER BY o.name;

-- ============================================================================
-- SUMMARY: What Multi-Tenancy Means
-- ============================================================================
/*
1. SHARED GLOBALLY (All Organizations):
   - articles table (everyone can read all articles)
   - Processing is done once, saved once

2. ISOLATED PER ORGANIZATION:
   - "My Articles" bookmarks (article_users)
   - RSS/Newsletter subscriptions (content_sources)
   - Content discovery queue (content_queue)
   - Organization settings (organizations.metadata)

3. ISOLATED PER USER:
   - User profile (users table)
   - Chat conversations (conversations)
   - Chat messages (messages)

BUSINESS LOGIC:
- If you're in Org A and I'm in Org B:
  ✅ We both see the same article library (all articles)
  ❌ We don't see each other's saved articles
  ❌ We don't see each other's RSS feeds
  ❌ We don't see each other's content queue

- This allows:
  ✅ Cost efficiency (process articles once)
  ✅ Data privacy (your saved items are private)
  ✅ Team collaboration (share sources within org)
*/
