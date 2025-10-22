# Authentication Implementation Plan

**Project:** Automate Life - Article Summarizer Web App
**Date:** October 22, 2025
**Status:** Planning Phase

---

## Table of Contents
1. [Current State](#current-state)
2. [Requirements](#requirements)
3. [Recommendation: Supabase Auth](#recommendation-supabase-auth)
4. [Implementation Plan - Phase 1](#implementation-plan---phase-1)
5. [Implementation Plan - Phase 2](#implementation-plan---phase-2)
6. [Migration Strategy](#migration-strategy)
7. [Code Examples](#code-examples)

---

## Current State

### What We Have
- ✅ **Supabase Database** - PostgreSQL with RLS enabled
- ✅ **Supabase Client** - `@supabase/supabase-js` installed in Next.js
- ✅ **Backend API Auth** - Simple bearer token API key
- ✅ **Article CRUD Operations** - Full database schema with vector search
- ✅ **Admin Page** - `/admin` for submitting articles to process
- ✅ **RLS Policies** - Currently permissive (allow all operations)

### What's Missing
- ❌ **User Authentication** - No login/signup system
- ❌ **User Ownership** - Articles table has no `user_id` column
- ❌ **Access Control** - Anyone can delete any article
- ❌ **Protected Routes** - Admin page accessible to everyone
- ❌ **Session Management** - No user sessions or JWT handling

### Current Database Schema
```sql
CREATE TABLE articles (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  url TEXT UNIQUE NOT NULL,
  summary_html TEXT,
  content_text TEXT,
  -- ... other fields
  created_at TIMESTAMP DEFAULT NOW()
  -- ⚠️ NO user_id column
);
```

### Current RLS Policies (Too Permissive)
```sql
CREATE POLICY "Users can view all articles" ON articles FOR SELECT USING (true);
CREATE POLICY "Users can insert articles" ON articles FOR INSERT WITH CHECK (true);
CREATE POLICY "Users can update articles" ON articles FOR UPDATE USING (true);
CREATE POLICY "Users can delete articles" ON articles FOR DELETE USING (true);
```

---

## Requirements

### Phase 1: Basic Authentication (MVP)

#### 1.1 User Sign Up / Sign In
- Users must create an account with email and password
- Existing users can log in with credentials
- Session persists across browser reloads
- Users can log out

#### 1.2 Protected Actions
Only authenticated users can:
- **Delete articles** - Delete buttons only visible when logged in
- **Access admin page** - `/admin` requires authentication
- **Submit articles** - Article processor requires login

#### 1.3 User-Owned Articles
- **Users only see their own articles** - ArticleList filtered by `user_id`
- **No cross-user access** - User A cannot see/edit/delete User B's articles
- **RLS enforcement** - Database policies enforce ownership at DB level

### Phase 2: Session & Enhanced Features (Future)

- Email verification
- Password reset flow
- Social authentication (Google, GitHub)
- Multi-factor authentication
- Admin roles (super user vs regular user)
- Shared articles / collaboration

---

## Recommendation: Supabase Auth

### Why Supabase Auth? ✅

**1. Already Integrated**
- You're using Supabase for database
- Auth client already installed: `@supabase/auth-js`
- Zero additional dependencies needed
- Seamless integration with existing setup

**2. Row Level Security (RLS) Native Support**
- Supabase Auth provides `auth.uid()` function in SQL
- RLS policies automatically access current user's ID
- Database enforces security - even if frontend bypassed
- No need to manually pass user IDs in queries

**3. Session Management Built-In**
- Automatic JWT token handling
- Refresh tokens managed automatically
- Secure httpOnly cookies option
- Session persistence across reloads
- No manual token storage needed

**4. Cost-Effective**
- **Free tier:** 50,000 Monthly Active Users (MAU)
- **Paid tier:** $0.00325 per MAU after that
- Far cheaper than Auth0, Clerk, or other providers
- Included in your existing Supabase subscription

**5. Feature-Rich**
- Email/password authentication
- Magic link authentication (passwordless)
- Social providers (Google, GitHub, etc.)
- Email verification
- Password reset flows
- Multi-factor authentication (MFA)
- Phone authentication

**6. Developer Experience**
- Simple API: `supabase.auth.signUp()`, `signIn()`, `signOut()`
- React hooks: `useUser()`, `useSession()`
- Pre-built UI components: `@supabase/auth-ui-react`
- Excellent documentation

### Alternatives Considered ❌

**Auth0**
- ❌ More expensive ($0.015/MAU vs $0.003/MAU)
- ❌ Requires separate integration with Supabase
- ❌ Need custom RLS policies to validate Auth0 JWTs
- ❌ More complex setup

**Clerk**
- ❌ Premium pricing ($25/month for 10K MAU)
- ❌ Overkill for your use case
- ❌ Separate service to manage

**NextAuth.js**
- ❌ Manual session management required
- ❌ Need to implement refresh tokens
- ❌ Requires additional database tables
- ❌ More code to maintain
- ⚠️ Doesn't integrate natively with Supabase RLS

**Custom Auth (JWT + bcrypt)**
- ❌ Security risks if not implemented correctly
- ❌ Must handle: password hashing, token refresh, email verification
- ❌ Significant development time
- ❌ Maintenance burden

### Decision: **Use Supabase Auth** ✅

---

## Implementation Plan - Phase 1

### Step 1: Enable Supabase Auth

#### 1.1 Supabase Dashboard Configuration
1. Go to https://supabase.com/dashboard
2. Select your project
3. Navigate to **Authentication** → **Providers**
4. Enable **Email** provider
5. Configure email settings:
   - **Enable email confirmations:** On (recommended) or Off (for faster testing)
   - **Secure email change:** On
   - **Email templates:** Customize as needed

#### 1.2 Configure Auth Settings
- **JWT expiry:** 3600 seconds (1 hour) - default is good
- **Refresh token expiry:** 2592000 seconds (30 days) - default is good
- **Site URL:** `http://localhost:3000` (local), `https://yourdomain.com` (production)
- **Redirect URLs:** Add `http://localhost:3000/auth/callback`

---

### Step 2: Database Schema Changes

**Migration File:** `migration/add-user-authentication.sql`

#### 2.1 Add `user_id` to Articles Table
```sql
-- Add user_id column (nullable initially for existing data)
ALTER TABLE articles
ADD COLUMN user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- Create index for performance
CREATE INDEX articles_user_id_idx ON articles(user_id);

-- Add comment
COMMENT ON COLUMN articles.user_id IS 'Owner of the article - references auth.users';
```

#### 2.2 Update RLS Policies

**Drop old permissive policies:**
```sql
DROP POLICY IF EXISTS "Users can view all articles" ON articles;
DROP POLICY IF EXISTS "Users can insert articles" ON articles;
DROP POLICY IF EXISTS "Users can update articles" ON articles;
DROP POLICY IF EXISTS "Users can delete articles" ON articles;
```

**Create new user-scoped policies:**
```sql
-- Users can only view their own articles
CREATE POLICY "Users can view own articles" ON articles
  FOR SELECT
  USING (auth.uid() = user_id);

-- Users can only insert articles with their own user_id
CREATE POLICY "Users can insert own articles" ON articles
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can only update their own articles
CREATE POLICY "Users can update own articles" ON articles
  FOR UPDATE
  USING (auth.uid() = user_id);

-- Users can only delete their own articles
CREATE POLICY "Users can delete own articles" ON articles
  FOR DELETE
  USING (auth.uid() = user_id);
```

#### 2.3 Update Conversations Table (Optional - for per-user chat)
```sql
-- Add user_id to conversations
ALTER TABLE conversations
ADD COLUMN user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- Create index
CREATE INDEX conversations_user_id_idx ON conversations(user_id);

-- Update RLS policies for conversations
DROP POLICY IF EXISTS "Users can view all conversations" ON conversations;
CREATE POLICY "Users can view own conversations" ON conversations
  FOR SELECT
  USING (auth.uid() = user_id);

-- Similar for INSERT, UPDATE, DELETE
```

#### 2.4 Handle Existing Data (if any)
```sql
-- Option A: Assign existing articles to a default user
-- First, create a system user or use your own user ID
-- UPDATE articles SET user_id = 'YOUR-USER-UUID' WHERE user_id IS NULL;

-- Option B: Delete unowned articles (if test data)
-- DELETE FROM articles WHERE user_id IS NULL;

-- Later: Make user_id required (after migration complete)
-- ALTER TABLE articles ALTER COLUMN user_id SET NOT NULL;
```

---

### Step 3: Frontend Implementation

#### 3.1 Create Auth Context Provider

**File:** `src/contexts/AuthContext.tsx`

```typescript
'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import { User, Session } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'
import { useRouter } from 'next/navigation'

interface AuthContextType {
  user: User | null
  session: Session | null
  loading: boolean
  signUp: (email: string, password: string) => Promise<{ error: any }>
  signIn: (email: string, password: string) => Promise<{ error: any }>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setUser(session?.user ?? null)
      setLoading(false)
    })

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      setUser(session?.user ?? null)
    })

    return () => subscription.unsubscribe()
  }, [])

  const signUp = async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    })
    return { error }
  }

  const signIn = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })
    if (!error) {
      router.push('/')
    }
    return { error }
  }

  const signOut = async () => {
    await supabase.auth.signOut()
    router.push('/login')
  }

  return (
    <AuthContext.Provider
      value={{ user, session, loading, signUp, signIn, signOut }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
```

#### 3.2 Update Root Layout

**File:** `src/app/layout.tsx`

```typescript
import { AuthProvider } from '@/contexts/AuthContext'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}
```

#### 3.3 Create Login Page

**File:** `src/app/login/page.tsx`

```typescript
'use client'

import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import Link from 'next/link'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const { signIn } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    const { error } = await signIn(email, password)

    if (error) {
      setError(error.message)
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-bold text-gray-900">
            Sign in to your account
          </h2>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-50 border border-red-300 text-red-800 px-4 py-3 rounded">
              {error}
            </div>
          )}
          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email address
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-[#077331] focus:border-[#077331]"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-[#077331] focus:border-[#077331]"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-[#077331] hover:bg-[#055a24] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#077331] disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>

          <div className="text-center text-sm">
            <span className="text-gray-600">Don't have an account? </span>
            <Link href="/signup" className="text-[#077331] hover:text-[#055a24] font-medium">
              Sign up
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}
```

#### 3.4 Create Signup Page

**File:** `src/app/signup/page.tsx`

```typescript
'use client'

import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import Link from 'next/link'

export default function SignupPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)
  const { signUp } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }

    setLoading(true)
    const { error } = await signUp(email, password)

    if (error) {
      setError(error.message)
      setLoading(false)
    } else {
      setSuccess(true)
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4">
        <div className="max-w-md w-full bg-white p-8 rounded-lg shadow">
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
              <svg className="h-6 w-6 text-[#077331]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Check your email</h3>
            <p className="text-sm text-gray-600 mb-4">
              We've sent you a confirmation link to <strong>{email}</strong>
            </p>
            <Link
              href="/login"
              className="text-[#077331] hover:text-[#055a24] font-medium"
            >
              Go to login
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-bold text-gray-900">
            Create your account
          </h2>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-50 border border-red-300 text-red-800 px-4 py-3 rounded">
              {error}
            </div>
          )}
          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email address
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-[#077331] focus:border-[#077331]"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-[#077331] focus:border-[#077331]"
              />
            </div>
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-[#077331] focus:border-[#077331]"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-[#077331] hover:bg-[#055a24] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#077331] disabled:opacity-50"
          >
            {loading ? 'Creating account...' : 'Sign up'}
          </button>

          <div className="text-center text-sm">
            <span className="text-gray-600">Already have an account? </span>
            <Link href="/login" className="text-[#077331] hover:text-[#055a24] font-medium">
              Sign in
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}
```

#### 3.5 Protect Admin Page

**File:** `src/app/admin/page.tsx` (add at top of component)

```typescript
'use client'

import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

export default function AdminPage() {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  if (loading) {
    return <div>Loading...</div>
  }

  if (!user) {
    return null // Will redirect
  }

  // Rest of your existing admin page code...
}
```

#### 3.6 Update ArticleList Component

**File:** `src/components/ArticleList.tsx`

```typescript
import { useAuth } from '@/contexts/AuthContext'

export default function ArticleList() {
  const { user } = useAuth()
  // ... existing state

  const fetchArticles = async () => {
    if (!user) return // Don't fetch if not logged in

    try {
      setLoading(true)
      const { data, error } = await supabase
        .from('articles')
        .select('*, key_insights, quotes, duration_minutes, word_count, topics')
        .eq('user_id', user.id) // Only fetch user's articles (RLS enforces this too)
        .order('created_at', { ascending: false })

      if (error) throw error
      setArticles(data || [])
    } catch (error) {
      console.error('Error fetching articles:', error)
    } finally {
      setLoading(false)
    }
  }

  // Only show delete button if user is logged in
  {user && (
    <button
      onClick={() => deleteArticle(article.id)}
      className="..."
    >
      <Trash2 className="h-4 w-4" />
    </button>
  )}
}
```

#### 3.7 Add Navigation with Auth State

**File:** `src/components/Nav.tsx` (new file)

```typescript
'use client'

import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'

export default function Nav() {
  const { user, signOut } = useAuth()

  return (
    <nav className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link href="/" className="text-xl font-bold text-[#077331]">
              Automate Life
            </Link>
          </div>
          <div className="flex items-center space-x-4">
            {user ? (
              <>
                <Link
                  href="/admin"
                  className="text-gray-700 hover:text-[#077331] px-3 py-2 rounded-md text-sm font-medium"
                >
                  Admin
                </Link>
                <span className="text-gray-600 text-sm">{user.email}</span>
                <button
                  onClick={() => signOut()}
                  className="bg-[#077331] text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-[#055a24]"
                >
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="text-gray-700 hover:text-[#077331] px-3 py-2 rounded-md text-sm font-medium"
                >
                  Login
                </Link>
                <Link
                  href="/signup"
                  className="bg-[#077331] text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-[#055a24]"
                >
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
```

---

### Step 4: Backend API Updates

#### 4.1 Update Article Processor

**File:** `programs/article_summarizer_backend/app/routes/article_processor.py`

Update the endpoint to accept and use `user_id`:

```python
from fastapi import Header, HTTPException

@router.post("/api/process-article")
async def process_article(
    request: ProcessArticleRequest,
    authorization: str = Header(None)
):
    # Extract user_id from Supabase JWT (optional - can also accept from request body)
    user_id = extract_user_from_jwt(authorization)

    # ... existing processing code ...

    # When inserting to Supabase, include user_id
    article_data = {
        "title": title,
        "url": url,
        "user_id": user_id,  # ← Add this
        # ... rest of fields
    }

    result = supabase.table("articles").insert(article_data).execute()
```

**Alternative:** Accept `user_id` in request body (simpler):

```python
class ProcessArticleRequest(BaseModel):
    url: str
    user_id: str  # ← Add this field

@router.post("/api/process-article")
async def process_article(request: ProcessArticleRequest):
    # Use request.user_id when inserting
    article_data = {
        "user_id": request.user_id,
        # ... rest
    }
```

#### 4.2 Keep Backend API Key for Scripts

- Backend API key stays for CLI/script access
- Web app sends Supabase JWT + user_id in requests
- RLS policies enforce security regardless of API key

---

## Implementation Plan - Phase 2

### Future Enhancements

#### Email Verification
- Require users to verify email before accessing articles
- Configure in Supabase Auth settings
- Customize email templates

#### Password Reset
- Supabase provides password reset flow out of the box
- Add "Forgot password?" link to login page
- Handle reset confirmation page

#### Social Authentication
- Add Google login: `supabase.auth.signInWithOAuth({ provider: 'google' })`
- Add GitHub login: `supabase.auth.signInWithOAuth({ provider: 'github' })`
- Configure OAuth apps in respective platforms

#### Role-Based Access Control (RBAC)
```sql
-- Add roles to users (Supabase)
CREATE TYPE user_role AS ENUM ('user', 'admin', 'superadmin');

ALTER TABLE auth.users ADD COLUMN role user_role DEFAULT 'user';

-- Admin-only policies
CREATE POLICY "Admins can view all articles" ON articles
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM auth.users
      WHERE auth.users.id = auth.uid()
      AND auth.users.role = 'admin'
    )
  );
```

#### Public Sharing
- Add `is_public` boolean to articles
- Create special RLS policy for public articles
- Generate shareable links

---

## Migration Strategy

### Safe Rollout Plan

#### Phase 1: Preparation (No Breaking Changes)
1. ✅ Add `user_id` column as **nullable** (allow NULL)
2. ✅ Keep existing permissive RLS policies
3. ✅ Deploy auth UI (login/signup available but optional)
4. ✅ Update admin page to capture user_id (if logged in)

**SQL:**
```sql
ALTER TABLE articles ADD COLUMN user_id UUID REFERENCES auth.users(id);
-- Don't add NOT NULL yet!
```

#### Phase 2: Testing (Parallel System)
1. ✅ Create test user accounts
2. ✅ Process new articles with user_id
3. ✅ Verify RLS policies work correctly
4. ✅ Test delete/edit permissions
5. ✅ Confirm query performance

#### Phase 3: Handle Existing Data
**Option A:** Assign to Default User
```sql
-- Create/use system user
INSERT INTO auth.users (id, email)
VALUES ('00000000-0000-0000-0000-000000000000', 'system@automatelife.com')
ON CONFLICT DO NOTHING;

-- Assign orphaned articles
UPDATE articles
SET user_id = '00000000-0000-0000-0000-000000000000'
WHERE user_id IS NULL;
```

**Option B:** Delete Test Data
```sql
DELETE FROM articles WHERE user_id IS NULL;
```

#### Phase 4: Enforce Authentication (Breaking Change)
1. ✅ Update RLS policies to user-scoped (as shown in Step 2.2)
2. ✅ Make `user_id` NOT NULL
3. ✅ Require login for all pages
4. ✅ Remove old permissive policies

**SQL:**
```sql
-- Make user_id required
ALTER TABLE articles ALTER COLUMN user_id SET NOT NULL;

-- Drop old policies
DROP POLICY "Users can view all articles" ON articles;

-- Create new user-scoped policies (as shown earlier)
```

#### Phase 5: Production Deployment
1. ✅ Run migrations on production Supabase
2. ✅ Deploy frontend with auth
3. ✅ Monitor error logs
4. ✅ Communicate changes to users (if any existing users)

---

## Code Examples

### How Users See Only Their Articles (RLS Magic)

**Frontend Code (Simple):**
```typescript
// User A queries articles
const { data } = await supabase
  .from('articles')
  .select('*')
// RLS automatically filters: WHERE user_id = 'user-a-uuid'

// User B queries articles (same code!)
const { data } = await supabase
  .from('articles')
  .select('*')
// RLS automatically filters: WHERE user_id = 'user-b-uuid'
```

**No need to manually add WHERE clause!** RLS enforces it at the database level.

### How to Get Current User

```typescript
import { useAuth } from '@/contexts/AuthContext'

function MyComponent() {
  const { user, session } = useAuth()

  if (!user) {
    return <div>Please log in</div>
  }

  return <div>Welcome, {user.email}!</div>
}
```

### How to Protect a Page

```typescript
'use client'

import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

export default function ProtectedPage() {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  if (loading) return <div>Loading...</div>
  if (!user) return null // Will redirect

  return <div>Protected content</div>
}
```

---

## Testing Checklist

### Before Deployment

- [ ] Create test user account via signup
- [ ] Verify email confirmation works (if enabled)
- [ ] Login with test account
- [ ] Process new article - verify user_id set correctly
- [ ] Verify article appears in ArticleList
- [ ] Create second test user
- [ ] Verify User A cannot see User B's articles
- [ ] Test delete article (should only work for own articles)
- [ ] Test admin page access (requires login)
- [ ] Test logout functionality
- [ ] Verify session persists after page reload
- [ ] Test password reset flow
- [ ] Check browser console for errors
- [ ] Test on mobile viewport

### Production Checklist

- [ ] Run migration SQL in Supabase (manually via SQL Editor)
- [ ] Verify Supabase Auth enabled
- [ ] Configure production Site URL
- [ ] Configure production Redirect URLs
- [ ] Update environment variables (.env.production)
- [ ] Deploy frontend to Vercel
- [ ] Test production login/signup
- [ ] Monitor error logs

---

## Security Considerations

### ✅ What's Secure

1. **RLS Enforcement** - Even if frontend is compromised, database enforces ownership
2. **JWT Tokens** - Supabase uses secure HTTP-only cookies (if configured)
3. **Password Hashing** - Supabase uses bcrypt automatically
4. **SQL Injection Protected** - Supabase client uses parameterized queries
5. **HTTPS Required** - Supabase enforces SSL connections

### ⚠️ Recommendations

1. **Enable email verification** - Prevent fake accounts
2. **Rate limiting** - Supabase provides built-in rate limiting
3. **CAPTCHA** - Add to signup form to prevent bots
4. **Password requirements** - Enforce strong passwords (8+ chars, numbers, symbols)
5. **Monitor auth logs** - Check Supabase Auth logs for suspicious activity

---

## Summary

### What You'll Have After Phase 1

✅ **User Accounts** - Email/password signup and login
✅ **Protected Pages** - Admin page requires authentication
✅ **User-Owned Articles** - Users only see/edit/delete their own articles
✅ **Row Level Security** - Database enforces ownership automatically
✅ **Session Management** - Persistent login across browser reloads
✅ **Secure by Default** - RLS prevents unauthorized access even if frontend bypassed

### Next Steps

1. **Review this plan** and confirm approach
2. **Enable Supabase Auth** in dashboard
3. **Run migration SQL** in Supabase SQL Editor (provided in `migration/add-user-authentication.sql`)
4. **Implement frontend code** (auth context, login/signup pages)
5. **Update backend** to accept user_id
6. **Test thoroughly** with test accounts
7. **Deploy to production** when ready

---

**Questions? Concerns?** Review this plan and let me know if you'd like any changes before we proceed with implementation!