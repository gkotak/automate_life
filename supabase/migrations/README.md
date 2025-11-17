# Organizations and User Roles Migration Guide

## Overview

This migration adds multi-tenancy support to Particles with organizations and user roles (admin/member). Each user belongs to one organization, and data is isolated per organization for security.

## Architecture Decisions

### 1. **One User = One Organization**
- Simplified model: Users have a direct foreign key to their organization
- No junction table needed
- Easier RLS policies and better performance

### 2. **Articles Remain Global**
- Articles are processed once and shared across organizations (cost efficient)
- Access is controlled via `article_users` junction table with org validation
- Future-ready for private/org-specific articles if needed

### 3. **Organization-Scoped Tables**
- `article_users`: Has org_id for defense-in-depth security
- `content_sources`: Team-wide RSS/newsletter subscriptions
- `content_queue`: Team-wide content discovery queue
- `conversations`: Remain user-scoped for now (private chat history)

## Migration Steps

### Step 1: Run Core Tables Migration

Run `001_create_organizations_and_users.sql` in Supabase SQL Editor.

This creates:
- `organizations` table (org info, billing, metadata)
- `users` profile table (extends auth.users with org_id and role)
- Helper functions (`get_user_organization_id()`, `is_user_admin()`)
- Initial RLS policies for organizations and users

**Expected outcome**: Two new tables with RLS enabled, no data yet.

### Step 2: Backfill Existing Users

Run `002_backfill_existing_users.sql` in Supabase SQL Editor.

This creates:
- Personal organization for each existing auth.users
- User profile record with 'admin' role for each user
- Validates migration succeeded (count checks)

**Expected outcome**: All existing users have organizations and profiles.

**Verification**:
```sql
-- Check user count matches
SELECT COUNT(*) FROM auth.users;
SELECT COUNT(*) FROM users;

-- Should show same number
```

### Step 3: Add Organization IDs to Tables

Run `003_add_organization_id_to_tables.sql` in Supabase SQL Editor.

This adds `organization_id` to:
- `article_users` (defense in depth)
- `content_sources` (team subscriptions, changes UNIQUE constraint)
- `content_queue` (team discovery)

Backfills data from user's organization.

**Expected outcome**: All three tables have organization_id populated.

**Verification**:
```sql
-- Check for NULL values (should be 0)
SELECT COUNT(*) FROM article_users WHERE organization_id IS NULL;
SELECT COUNT(*) FROM content_sources WHERE organization_id IS NULL;
SELECT COUNT(*) FROM content_queue WHERE organization_id IS NULL;
```

### Step 4: Update RLS Policies

Run `004_update_rls_policies.sql` in Supabase SQL Editor.

This updates RLS policies for:
- `articles` - Access via article_users with org validation
- `article_users` - Organization-scoped
- `content_sources` - Organization-scoped
- `content_queue` - Organization-scoped
- `conversations` - User-scoped (unchanged)
- `messages` - Via conversation ownership (unchanged)

**Expected outcome**: All tables have organization-aware RLS policies.

**Verification**:
```sql
-- List all policies
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('articles', 'article_users', 'content_sources', 'content_queue')
ORDER BY tablename, policyname;
```

## Frontend Integration

### 1. TypeScript Types

Created in `web-apps/article-summarizer/src/types/database.ts`:

```typescript
import { UserProfile, Organization, UserRole } from '@/types/database'
import { isAdmin, getUserPermissions } from '@/types/database'
```

### 2. AuthContext Updates

The `AuthContext` now provides:
- `user` - Supabase auth user (existing)
- `userProfile` - User profile with organization_id and role
- `organization` - Organization data
- `refreshProfile()` - Refresh profile/org data

Example usage:
```typescript
const { user, userProfile, organization } = useAuth()

// Check if admin
if (userProfile?.role === 'admin') {
  // Admin-only features
}

// Access organization data
console.log(organization?.name)
```

## Database Schema

### Organizations Table
```sql
CREATE TABLE organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  billing_id TEXT, -- For future Stripe integration
  metadata JSONB DEFAULT '{}', -- Custom settings
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Users Profile Table
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('admin', 'member')),
  display_name TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Modified Tables

**article_users**:
- Added `organization_id UUID REFERENCES organizations(id)`
- Changed unique constraint to `(user_id, article_id, organization_id)`

**content_sources**:
- Added `organization_id UUID REFERENCES organizations(id)`
- Changed unique constraint from `(user_id, url)` to `(organization_id, url)`
- Enables team-wide subscriptions

**content_queue**:
- Added `organization_id UUID REFERENCES organizations(id)`
- Team-wide content discovery

## User Roles

### Admin Role
Permissions:
- ✅ Read/write all org data
- ✅ Update organization settings
- ✅ Manage other users (future)
- ✅ Delete content sources
- ✅ Manage billing (future)

### Member Role
Permissions:
- ✅ Read/write own articles
- ✅ Read org content sources and queue
- ✅ Add content sources
- ❌ Delete org content sources
- ❌ Update organization settings

## Security Model

### Multi-Tenancy Enforcement

1. **RLS Policies**: All tables check organization membership
2. **Helper Functions**: `get_user_organization_id()` and `is_user_admin()` enforce rules
3. **Defense in Depth**: `article_users` has org_id even though articles are global
4. **Unique Constraints**: Prevent duplicate org+resource combinations

### Query Pattern
```sql
-- Example: Users can only see articles in their org
SELECT * FROM articles
WHERE id IN (
  SELECT article_id FROM article_users
  WHERE organization_id = get_user_organization_id()
);
```

## Testing

### 1. Test User Profile Loading
```typescript
const { userProfile, organization } = useAuth()
console.log('Role:', userProfile?.role)
console.log('Org:', organization?.name)
```

### 2. Test RLS Policies
```sql
-- As authenticated user, try to read articles
SET ROLE authenticated;
SET request.jwt.claims.sub = 'user-uuid-here';

SELECT * FROM articles; -- Should only show org articles
SELECT * FROM content_sources; -- Should only show org sources
```

### 3. Test Organization Isolation
Create two users in different orgs, verify they can't see each other's data.

## Rollback Plan

If something goes wrong, run migrations in reverse:

```sql
-- 1. Remove organization_id from tables
ALTER TABLE article_users DROP COLUMN IF EXISTS organization_id;
ALTER TABLE content_sources DROP COLUMN IF EXISTS organization_id;
ALTER TABLE content_queue DROP COLUMN IF EXISTS organization_id;

-- 2. Restore old RLS policies (from git history)

-- 3. Drop new tables
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;
```

## Future Enhancements

1. **Team Invitations**: Admin can invite users to their org
2. **Billing Integration**: Connect Stripe billing_id
3. **Custom Metadata**: Store org-specific AI prompts, preferences
4. **Shared Conversations**: Enable team chat rooms
5. **Private Articles**: Option for org-specific article processing
6. **Audit Logs**: Track admin actions

## Troubleshooting

### Users table doesn't exist
- Run `001_create_organizations_and_users.sql` first

### NULL organization_id errors
- Run `002_backfill_existing_users.sql` to create profiles
- Run `003_add_organization_id_to_tables.sql` to backfill data

### RLS blocking queries
- Check user is in `users` table with valid organization_id
- Verify RLS policies are created: `SELECT * FROM pg_policies WHERE tablename = 'articles'`

### Frontend not showing userProfile
- Check network tab for failed `/users` query
- Verify RLS policies allow user to read their own profile
- Check browser console for errors

## Support

If you encounter issues:
1. Check migration logs in Supabase SQL Editor
2. Verify all migrations ran successfully
3. Test RLS policies with sample queries
4. Check AuthContext is loading profile data

## Migration Checklist

- [ ] Run `001_create_organizations_and_users.sql`
- [ ] Verify organizations and users tables created
- [ ] Run `002_backfill_existing_users.sql`
- [ ] Verify all auth.users have profiles
- [ ] Run `003_add_organization_id_to_tables.sql`
- [ ] Verify no NULL organization_id values
- [ ] Run `004_update_rls_policies.sql`
- [ ] Verify RLS policies created
- [ ] Test frontend loads userProfile and organization
- [ ] Test multi-tenancy (create second user, verify isolation)
- [ ] Deploy frontend changes

---

**Migration Complete!** 🎉

Your Particles application now supports multi-tenant organizations with role-based access control.
