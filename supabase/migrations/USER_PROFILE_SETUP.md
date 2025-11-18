# User Profile Auto-Creation Setup

This document describes the migrations needed to automatically create user profiles and organizations when users sign up.

## Required Migrations (Run in Order)

### 1. `001_create_organizations_and_users.sql`
Creates the `organizations` and `users` tables with RLS policies.
- **Status**: ✅ Already applied
- **Purpose**: Base schema for multi-tenancy

### 2. `1001_user_profile_auto_creation.sql`
Creates database trigger to auto-create user profiles and organizations on signup.
- **Status**: ✅ Applied (updated version without `SET search_path`)
- **Purpose**:
  - Creates `handle_new_user()` trigger function
  - Creates `on_auth_user_created` trigger on `auth.users` table
  - Backfills any existing auth users without profiles
- **Key Fix**: Removed `SET search_path = public` which was preventing table access

### 3. `1002_fix_rls_for_user_creation.sql`
Adds INSERT policies to allow the trigger to create organizations and user profiles.
- **Status**: ✅ Applied
- **Purpose**:
  - Adds INSERT policy for `organizations` table
  - Adds INSERT policy for `users` table
  - Allows both `authenticated` and `anon` roles (needed during signup)

## How It Works

When a new user signs up:

1. Supabase creates entry in `auth.users` table
2. Trigger `on_auth_user_created` fires
3. Function `handle_new_user()` executes:
   - Extracts email from `auth.users`
   - Creates organization named "{username}'s Organization"
   - Creates user profile with `admin` role linked to the organization
4. User is fully set up and can access the application

## Troubleshooting

### Error: "relation 'organizations' does not exist"
**Solution**: Remove `SET search_path = public` from function definition. The explicit `public.` schema prefix in INSERT statements is sufficient.

### Error: "new row violates row-level security policy"
**Solution**: Ensure migration `1002_fix_rls_for_user_creation.sql` has been applied to add INSERT policies.

### Trigger not firing
**Verify**:
```sql
-- Check trigger exists
SELECT trigger_name FROM information_schema.triggers
WHERE trigger_name = 'on_auth_user_created';

-- Check function exists
SELECT routine_name FROM information_schema.routines
WHERE routine_name = 'handle_new_user';
```

## Testing

To verify the setup is working:

1. Sign up a new user via the web app
2. Check that all three entries are created:
   - Entry in `auth.users`
   - Entry in `organizations`
   - Entry in `users` (linked to the organization)

## Archived Files

The following test files were used during debugging and are now archived:
- `test_trigger.sql` - Comprehensive trigger testing script
- `test_trigger_simple.sql` - Simplified test queries
- `verify_tables.sql` - Table existence verification
- `1003_disable_rls_for_trigger.sql` - Alternative approach (not used)

These files are in `migrations/archive/` for reference.
