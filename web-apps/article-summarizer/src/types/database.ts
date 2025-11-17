// Database types for Organizations and Users
// These types match the Supabase database schema

export type UserRole = 'admin' | 'member'

export interface Organization {
  id: string
  name: string
  billing_id: string | null
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
