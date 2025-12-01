'use client'

import { useState, useEffect, useCallback } from 'react'
import { Folder, ChevronLeft, ChevronRight, Plus, MoreVertical, Pencil, Trash2 } from 'lucide-react'
import { FolderWithCount } from '@/types/database'
import CreateFolderModal from './CreateFolderModal'
import { useAuth } from '@/contexts/AuthContext'

interface FoldersSidebarProps {
  selectedFolderId?: number | null
  onSelectFolder?: (folderId: number | null) => void
  className?: string
}

export default function FoldersSidebar({
  selectedFolderId = null,
  onSelectFolder,
  className = '',
}: FoldersSidebarProps) {
  const { user } = useAuth()
  const [folders, setFolders] = useState<FolderWithCount[]>([])
  const [loading, setLoading] = useState(true)
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('foldersSidebarCollapsed') === 'true'
    }
    return false
  })
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingFolder, setEditingFolder] = useState<FolderWithCount | null>(null)
  const [menuOpenId, setMenuOpenId] = useState<number | null>(null)

  // Fetch folders
  const fetchFolders = useCallback(async () => {
    if (!user) {
      setFolders([])
      setLoading(false)
      return
    }

    try {
      const response = await fetch('/api/folders')
      if (response.ok) {
        const data = await response.json()
        setFolders(data.folders || [])
      }
    } catch (error) {
      console.error('Failed to fetch folders:', error)
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => {
    fetchFolders()
  }, [fetchFolders])

  // Persist collapse state
  useEffect(() => {
    localStorage.setItem('foldersSidebarCollapsed', String(collapsed))
  }, [collapsed])

  // Handle create folder
  const handleCreateFolder = async (name: string, description: string) => {
    const response = await fetch('/api/folders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Failed to create folder')
    }

    const data = await response.json()
    setFolders((prev) => [...prev, data.folder].sort((a, b) => a.name.localeCompare(b.name)))
  }

  // Handle edit folder
  const handleEditFolder = async (name: string, description: string) => {
    if (!editingFolder) return

    const response = await fetch(`/api/folders/${editingFolder.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Failed to update folder')
    }

    const data = await response.json()
    setFolders((prev) =>
      prev
        .map((f) => (f.id === editingFolder.id ? { ...f, ...data.folder } : f))
        .sort((a, b) => a.name.localeCompare(b.name))
    )
    setEditingFolder(null)
  }

  // Handle delete folder
  const handleDeleteFolder = async (folderId: number) => {
    if (!confirm('Are you sure you want to delete this folder? Articles will not be deleted.')) {
      return
    }

    try {
      const response = await fetch(`/api/folders/${folderId}`, {
        method: 'DELETE',
      })

      if (response.ok) {
        setFolders((prev) => prev.filter((f) => f.id !== folderId))
        // If deleted folder was selected, clear selection
        if (selectedFolderId === folderId) {
          onSelectFolder?.(null)
        }
      }
    } catch (error) {
      console.error('Failed to delete folder:', error)
    }

    setMenuOpenId(null)
  }

  // Don't show sidebar if user is not logged in
  if (!user) {
    return null
  }

  return (
    <>
      <div
        className={`bg-white border-r border-gray-200 flex flex-col transition-all duration-300 ${
          collapsed ? 'w-12' : 'w-60'
        } ${className}`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-gray-100">
          {!collapsed && (
            <h2 className="text-sm font-semibold text-gray-700">Folders</h2>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </button>
        </div>

        {/* Folder List */}
        <div className="flex-1 overflow-y-auto py-2">
          {/* All Articles Option */}
          <button
            onClick={() => onSelectFolder?.(null)}
            className={`w-full flex items-center gap-2 px-3 py-2 transition-colors ${
              selectedFolderId === null
                ? 'bg-green-50 text-[#077331]'
                : 'text-gray-700 hover:bg-gray-50'
            }`}
            title="All Articles"
          >
            <Folder className="h-4 w-4 flex-shrink-0" />
            {!collapsed && <span className="text-sm truncate">All Articles</span>}
          </button>

          {/* Loading State */}
          {loading && !collapsed && (
            <div className="px-3 py-4 text-center">
              <div className="animate-spin rounded-full h-5 w-5 border-2 border-[#077331] border-t-transparent mx-auto" />
            </div>
          )}

          {/* Folders */}
          {!loading &&
            folders.map((folder) => (
              <div key={folder.id} className="relative group">
                <button
                  onClick={() => onSelectFolder?.(folder.id)}
                  className={`w-full flex items-center gap-2 px-3 py-2 transition-colors ${
                    selectedFolderId === folder.id
                      ? 'bg-green-50 text-[#077331]'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                  title={collapsed ? `${folder.name} (${folder.total_count})` : undefined}
                >
                  <Folder className="h-4 w-4 flex-shrink-0" />
                  {!collapsed && (
                    <>
                      <span className="text-sm truncate flex-1 text-left">{folder.name}</span>
                      <span className="text-xs text-gray-400">{folder.total_count}</span>
                    </>
                  )}
                </button>

                {/* Menu Button (shown on hover) */}
                {!collapsed && (
                  <div className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setMenuOpenId(menuOpenId === folder.id ? null : folder.id)
                      }}
                      className="p-1 text-gray-400 hover:text-gray-600 rounded"
                    >
                      <MoreVertical className="h-4 w-4" />
                    </button>

                    {/* Dropdown Menu */}
                    {menuOpenId === folder.id && (
                      <div className="absolute right-0 top-full mt-1 w-32 bg-white rounded-md shadow-lg border border-gray-200 z-50 py-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setEditingFolder(folder)
                            setMenuOpenId(null)
                          }}
                          className="w-full px-3 py-1.5 flex items-center gap-2 text-sm text-gray-700 hover:bg-gray-50"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                          Edit
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDeleteFolder(folder.id)
                          }}
                          className="w-full px-3 py-1.5 flex items-center gap-2 text-sm text-red-600 hover:bg-red-50"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
        </div>

        {/* Create Folder Button */}
        <div className="p-3 border-t border-gray-100">
          <button
            onClick={() => setShowCreateModal(true)}
            className={`flex items-center gap-2 text-[#077331] hover:text-[#055a24] transition-colors ${
              collapsed ? 'justify-center w-full' : ''
            }`}
            title="Create folder"
          >
            <Plus className="h-4 w-4" />
            {!collapsed && <span className="text-sm font-medium">Create folder</span>}
          </button>
        </div>
      </div>

      {/* Create/Edit Modal */}
      <CreateFolderModal
        isOpen={showCreateModal || !!editingFolder}
        onClose={() => {
          setShowCreateModal(false)
          setEditingFolder(null)
        }}
        onSave={editingFolder ? handleEditFolder : handleCreateFolder}
        folder={editingFolder}
      />
    </>
  )
}
