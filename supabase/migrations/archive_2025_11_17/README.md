# Archived Migrations - November 17, 2025

This directory contains migrations that were created during the RLS policy implementation and debugging process but are no longer needed.

## Why These Were Archived

During the implementation of multi-tenant Row Level Security (RLS) policies, we went through several iterations:

1. **Initial attempts** (992-997): Multiple attempts to fix RLS policies with various approaches
2. **Debugging scripts** (993, 996, 998 diagnostics): Temporary scripts to understand the state
3. **Security fixes** (998, 999): Function search path and duplicate policy fixes

All of these have been **consolidated** into three clean migrations:

- **1000_consolidated_rls_policies.sql** - Complete RLS policy implementation
- **1001_user_profile_auto_creation.sql** - Auto-create user profiles
- **1002_security_hardening.sql** - Security improvements and cleanup

## Archived Files

### RLS Policy Iterations
- `992_clean_slate_rls.sql` - Early attempt to clean and rebuild policies
- `994_fix_all_rls_policies.sql` - Comprehensive policy fix attempt
- `994_fix_users_infinite_recursion.sql` - Fixed infinite recursion bug
- `995_fix_rls_completely.sql` - Another comprehensive attempt
- `996_complete_rls_reset.sql` - Complete reset approach
- `996_debug_current_state.sql` - Debugging script
- `997_comprehensive_rls_final.sql` - The successful final version (now in 1000)
- `997_fix_articles_rls_policy.sql` - Partial fix attempt

### Diagnostic Scripts
- `993_show_current_policies.sql` - Show current policy state
- `998_diagnose_rls_issue.sql` - Diagnostic queries
- `999_verify_migration.sql` - Verification script

### User Profile Creation
- `995_auto_create_user_profile.sql` - Now consolidated into 1001

### Security Fixes
- `998_fix_function_search_path.sql` - Now consolidated into 1002
- `999_fix_known_channels_duplicate_policy.sql` - Now included in 1000

## What To Use Going Forward

**Only use the consolidated migrations:**

1. **1000_consolidated_rls_policies.sql** - Run this for RLS policies
2. **1001_user_profile_auto_creation.sql** - Run this for user profile automation
3. **1002_security_hardening.sql** - Run this for security improvements

These three files contain all the working, tested logic from the 14 archived files, cleaned up and organized logically.

## If You Need to Reference These

These files are kept for historical reference only. If you need to understand:
- How we debugged the infinite recursion issue → See `994_fix_users_infinite_recursion.sql`
- How RLS policies evolved → Compare `992` through `997`
- What diagnostic queries we used → See `993`, `996`, `998`, `999` diagnostic files

**Do not run these migrations** - they may conflict with the consolidated versions.
