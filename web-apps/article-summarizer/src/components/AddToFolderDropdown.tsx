'use client'

import { useState, useRef, useEffect } from 'react'
import { FolderPlus, Check, Plus, Folder } from 'lucide-react'
import { FolderWithCount } from '@/types/database'

interface AddToFolderDropdownProps {
  articleId: number
  isPrivate: boolean
  folders: FolderWithCount[]
  articleFolderIds: number[]
  onToggleFolder: (folderId: number, isInFolder: boolean) => Promise<void>
  onCreateFolder: () => void
}

export default function AddToFolderDropdown({
  articleId,
  isPrivate,
  folders,
  articleFolderIds,
  onToggleFolder,
  onCreateFolder,
}: AddToFolderDropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [loadingFolderId, setLoadingFolderId] = useState<number | null>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  // Close on escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen])

  const handleToggleFolder = async (folderId: number) => {
    const isInFolder = articleFolderIds.includes(folderId)
    setLoadingFolderId(folderId)

    try {
      await onToggleFolder(folderId, isInFolder)
    } finally {
      setLoadingFolderId(null)
    }
  }

  const handleCreateFolder = () => {
    setIsOpen(false)
    onCreateFolder()
  }

  return (
    <div className="relative">
      {/* Trigger Button */}
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(!isOpen)}
        className="p-1.5 sm:p-2 text-gray-500 hover:text-[#077331] transition-colors"
        title="Add to folder"
      >
        <FolderPlus className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          ref={dropdownRef}
          className="absolute right-0 mt-1 w-56 bg-white rounded-lg shadow-lg border border-gray-200 z-50 py-1"
        >
          {/* Header */}
          <div className="px-3 py-2 border-b border-gray-100">
            <p className="text-sm font-medium text-gray-700">Add to folder</p>
          </div>

          {/* Folder List */}
          <div className="max-h-64 overflow-y-auto">
            {folders.length === 0 ? (
              <div className="px-3 py-4 text-center text-sm text-gray-500">
                No folders yet
              </div>
            ) : (
              folders.map((folder) => {
                const isInFolder = articleFolderIds.includes(folder.id)
                const isLoading = loadingFolderId === folder.id

                return (
                  <button
                    key={folder.id}
                    onClick={() => handleToggleFolder(folder.id)}
                    disabled={isLoading}
                    className="w-full px-3 py-2 flex items-center gap-2 hover:bg-gray-50 transition-colors disabled:opacity-50"
                  >
                    {/* Checkbox/Check indicator */}
                    <div className={`w-4 h-4 flex items-center justify-center rounded border ${
                      isInFolder
                        ? 'bg-[#077331] border-[#077331]'
                        : 'border-gray-300'
                    }`}>
                      {isLoading ? (
                        <div className="animate-spin rounded-full h-2.5 w-2.5 border border-white border-t-transparent" />
                      ) : isInFolder ? (
                        <Check className="h-3 w-3 text-white" />
                      ) : null}
                    </div>

                    {/* Folder icon and name */}
                    <Folder className="h-4 w-4 text-gray-400 flex-shrink-0" />
                    <span className="text-sm text-gray-700 truncate flex-1 text-left">
                      {folder.name}
                    </span>

                    {/* Article count */}
                    <span className="text-xs text-gray-400">
                      {folder.total_count}
                    </span>
                  </button>
                )
              })
            )}
          </div>

          {/* Divider */}
          <div className="border-t border-gray-100 my-1" />

          {/* Create New Folder */}
          <button
            onClick={handleCreateFolder}
            className="w-full px-3 py-2 flex items-center gap-2 hover:bg-gray-50 transition-colors text-[#077331]"
          >
            <Plus className="h-4 w-4" />
            <span className="text-sm font-medium">Create new folder</span>
          </button>
        </div>
      )}
    </div>
  )
}
