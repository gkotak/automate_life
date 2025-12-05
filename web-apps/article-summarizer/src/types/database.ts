// Database types for Organizations and Users
// These types match the Supabase database schema

export type UserRole = 'admin' | 'member'

export interface Organization {
  id: string
  name: string
  billing_id: string | null
  organizational_context?: string | null
  metadata: Record<string, any>
  created_at: string
  updated_at: string
}

export interface UserProfile {
  id: string
  organization_id: string
  role: UserRole
  display_name: string | null
  created_at: string
  updated_at: string
}

// Extended type that includes organization data
export interface UserWithOrganization extends UserProfile {
  organization: Organization
}

// Helper type for checking permissions
export interface UserPermissions {
  isAdmin: boolean
  canManageOrg: boolean
  canInviteUsers: boolean
  canManageBilling: boolean
}

// Helper function to check if user is admin
export function isAdmin(user: UserProfile | null): boolean {
  return user?.role === 'admin'
}

// Helper function to get user permissions
export function getUserPermissions(user: UserProfile | null): UserPermissions {
  const admin = isAdmin(user)

  return {
    isAdmin: admin,
    canManageOrg: admin,
    canInviteUsers: admin,
    canManageBilling: admin,
  }
}

// Helper function to check if organization has podcast history access
export function canAccessPodcastHistory(organization: Organization | null): boolean {
  return organization?.metadata?.features?.podcast_history === true
}

// Article types
export interface Article {
  id: number
  title: string
  url: string
  source?: string
  summary_text?: string
  transcript_text?: string
  content_source?: string
  video_id?: string
  audio_url?: string
  platform?: string
  key_insights?: any[]
  quotes?: any[]
  images?: any[]
  video_frames?: any[]
  duration_minutes?: number
  word_count?: number
  topics?: any[]
  created_at: string
  updated_at: string
}

export interface PrivateArticle extends Omit<Article, 'id'> {
  id: number
  organization_id: string
}

export type ArticleType = 'public' | 'private'

export interface ArticleWithType extends Article {
  type: 'public'
  saved_at?: string
}

export interface PrivateArticleWithType extends PrivateArticle {
  type: 'private'
  saved_at?: string
}

export type AnyArticle = ArticleWithType | PrivateArticleWithType

// Folder types
export interface Folder {
  id: number
  organization_id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface FolderWithCount extends Folder {
  article_count: number
  private_article_count: number
  total_count: number
}

export interface FolderArticle {
  id: number
  folder_id: number
  article_id: number
  added_at: string
}

export interface FolderPrivateArticle {
  id: number
  folder_id: number
  private_article_id: number
  added_at: string
}

// Theme types
export interface Theme {
  id: number
  organization_id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface ThemeWithCount extends Theme {
  article_count: number
}

export interface ThemedInsight {
  id: number
  private_article_id: number
  theme_id: number
  insight_text: string
  timestamp_seconds: number | null
  time_formatted: string | null
  created_at: string
}

export interface ThemedInsightWithArticle extends ThemedInsight {
  article_title: string
  article_url: string
  article_source?: string
  article_created_at: string
}

export interface ThemedInsightsByArticle {
  article_id: number
  article_title: string
  article_url: string
  article_source?: string
  article_created_at: string
  insights: Array<{
    id: number
    insight_text: string
    timestamp_seconds: number | null
    time_formatted: string | null
    created_at: string
  }>
}
