'use client'

import { useState, useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import { Folder } from '@/types/database'

interface CreateFolderModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (name: string, description: string) => Promise<void>
  folder?: Folder | null  // For edit mode
}

export default function CreateFolderModal({
  isOpen,
  onClose,
  onSave,
  folder,
}: CreateFolderModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const nameInputRef = useRef<HTMLInputElement>(null)

  const isEditMode = !!folder

  // Reset form when modal opens/closes or folder changes
  useEffect(() => {
    if (isOpen) {
      setName(folder?.name || '')
      setDescription(folder?.description || '')
      setError('')
      // Focus name input after a brief delay for animation
      setTimeout(() => nameInputRef.current?.focus(), 100)
    }
  }, [isOpen, folder])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!name.trim()) {
      setError('Folder name is required')
      return
    }

    setLoading(true)
    setError('')

    try {
      await onSave(name.trim(), description.trim())
      onClose()
    } catch (err: any) {
      setError(err.message || 'Failed to save folder')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
      onKeyDown={handleKeyDown}
    >
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            {isEditMode ? 'Edit Folder' : 'Create Folder'}
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4 space-y-4">
            {/* Name Input */}
            <div>
              <label
                htmlFor="folder-name"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Name <span className="text-red-500">*</span>
              </label>
              <input
                ref={nameInputRef}
                id="folder-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter folder name"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#077331] focus:border-transparent outline-none transition-shadow"
                disabled={loading}
              />
            </div>

            {/* Description Input */}
            <div>
              <label
                htmlFor="folder-description"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Description <span className="text-gray-400">(optional)</span>
              </label>
              <textarea
                id="folder-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Enter folder description"
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#077331] focus:border-transparent outline-none transition-shadow resize-none"
                disabled={loading}
              />
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-md px-3 py-2">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-lg">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-[#077331] rounded-md hover:bg-[#055a24] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {loading && (
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
              )}
              {isEditMode ? 'Save Changes' : 'Create Folder'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
