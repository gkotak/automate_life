'use client'

import { useState, useEffect, useCallback } from 'react'
import FoldersSidebar from './FoldersSidebar'
import ArticleList from './ArticleList'
import { FolderWithCount } from '@/types/database'

interface HomePageClientProps {
  initialFolderName?: string | null
}

export default function HomePageClient({ initialFolderName = null }: HomePageClientProps) {
  const [folders, setFolders] = useState<FolderWithCount[]>([])
  const [selectedFolderId, setSelectedFolderId] = useState<number | null>(null)
  const [isInitialized, setIsInitialized] = useState(false)

  // Fetch folders on mount
  useEffect(() => {
    const fetchFolders = async () => {
      try {
        const response = await fetch('/api/folders')
        if (response.ok) {
          const data = await response.json()
          const fetchedFolders = data.folders || []
          setFolders(fetchedFolders)

          // If we have an initial folder name, find and select it
          if (initialFolderName) {
            const matchingFolder = fetchedFolders.find(
              (f: FolderWithCount) => f.name.toLowerCase() === initialFolderName.toLowerCase()
            )
            if (matchingFolder) {
              setSelectedFolderId(matchingFolder.id)
            }
          }
          setIsInitialized(true)
        }
      } catch (error) {
        console.error('Failed to fetch folders:', error)
        setIsInitialized(true)
      }
    }
    fetchFolders()
  }, [initialFolderName])

  // Handle browser back/forward navigation
  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname
      if (path === '/') {
        setSelectedFolderId(null)
      } else if (path.startsWith('/folder/')) {
        const folderName = decodeURIComponent(path.replace('/folder/', ''))
        const folder = folders.find(
          (f) => f.name.toLowerCase() === folderName.toLowerCase()
        )
        if (folder) {
          setSelectedFolderId(folder.id)
        }
      }
    }

    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [folders])

  const handleSelectFolder = useCallback(
    (folderId: number | null) => {
      setSelectedFolderId(folderId)

      // Update URL without navigation
      if (folderId === null) {
        window.history.pushState({}, '', '/')
      } else {
        const folder = folders.find((f) => f.id === folderId)
        if (folder) {
          window.history.pushState({}, '', `/folder/${encodeURIComponent(folder.name)}`)
        }
      }
    },
    [folders]
  )

  // Show loading state while fetching folders (only if we need to resolve a folder name)
  if (initialFolderName && !isInitialized) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#077331]" />
      </div>
    )
  }

  return (
    <div className="flex h-full">
      {/* Folders Sidebar */}
      <FoldersSidebar
        selectedFolderId={selectedFolderId}
        onSelectFolder={handleSelectFolder}
        className="hidden md:flex flex-shrink-0"
      />

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <ArticleList folderId={selectedFolderId} />
      </div>
    </div>
  )
}
