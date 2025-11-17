# Database Migrations

This directory contains all Supabase database migrations for the Automate Life project.

## Migration Structure

Migrations are numbered sequentially and should be run in order.

### Core Schema (001-020)
Foundation tables and features:
- **001-004**: Multi-tenant organization system
- **009-013**: User authentication and content tables
- **014-015**: Earnings insights and video frames
- **016-020**: Known channels and content queue

### Consolidated Migrations (1000-1002)
**These replace migrations 992-999** (see archive):
- **1000**: Complete RLS policy implementation
- **1001**: Auto-create user profiles on signup
- **1002**: Security hardening (function search paths)

## Current Active Migrations

```
001_create_organizations_and_users.sql          # Multi-tenant foundation
002_backfill_existing_users.sql                  # Migrate existing users
003_add_organization_id_to_tables.sql            # Add org scoping
003_add_organization_id_to_tables_fixed.sql      # Fix for 003
004_update_rls_policies.sql                      # Initial RLS policies
009_add_chat_rls_policies.sql                    # Chat feature RLS
010_add_user_authentication.sql                  # User auth setup
011_add_user_scoping_content_tables.sql          # Content table scoping
012_article_user_many_to_many.sql                # Article-user junction
013_cleanup_content_sources_schema.sql           # Schema cleanup
014_create_earnings_tables.sql                   # Earnings insights
015_add_video_frames_support.sql                 # Video frame extraction
016_rename_known_podcasts_to_known_channels.sql  # Rename for flexibility
017_refactor_known_channels_url_based.sql        # URL-based matching
018_add_audio_url_to_content_queue.sql           # Audio URL field
019_add_source_to_content_queue.sql              # Source tracking
020_optimize_known_channels_primary_key.sql      # Performance optimization

1000_consolidated_rls_policies.sql               # ✅ Complete RLS policies
1001_user_profile_auto_creation.sql              # ✅ Auto user profiles
1002_security_hardening.sql                      # ✅ Security improvements
```

## Running Migrations

### Fresh Database
Run all migrations in order (001 → 020 → 1000 → 1001 → 1002)

### Existing Database
If you've already run migrations 992-999, you can skip them and just run:
1. `1000_consolidated_rls_policies.sql`
2. `1001_user_profile_auto_creation.sql`
3. `1002_security_hardening.sql`

## Archived Migrations

The `archive_2025_11_17/` directory contains 14 migration files from the RLS debugging process. These are kept for historical reference but should NOT be run. See the archive README for details.

## Key Design Principles

### Multi-Tenancy
- Each user belongs to one organization
- Content is scoped by organization (sources, queue)
- Articles are global, ownership via `article_users` junction table

### Row Level Security (RLS)
- All policies use `(select auth.uid())` for performance
- Users table has NO recursive queries (prevents infinite loops)
- Articles readable by everyone (public)
- Article modification only by owners (via article_users)

### Security
- All functions use `SET search_path = public`
- SECURITY DEFINER functions for RLS bypass where needed
- Auto-create user profiles on signup
- Trigger-based audit trails (updated_at)

## Troubleshooting

### If you see "infinite recursion detected"
This means RLS policies are querying the same table they protect. Check the `users` table policies - they should ONLY use `auth.uid()` directly, not subqueries on users.

### If articles don't load
1. Check RLS policies on `articles` table (should be publicly readable)
2. Verify no duplicate policies exist
3. Run the diagnostics from archive if needed

### If user profiles aren't created
Check that the `on_auth_user_created` trigger exists and the `handle_new_user()` function is working.

## Adding New Migrations

1. Number sequentially (next number: 1003)
2. Use descriptive names: `1003_add_feature_name.sql`
3. Include verification queries at the end
4. Document changes in this README
5. Test on dev before running on production
