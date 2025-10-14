'use client'

import { useState } from 'react'
import { X, ZoomIn, ChevronLeft, ChevronRight } from 'lucide-react'

interface ImageGalleryProps {
  images: string[]  // Array of image URLs
}

export default function ImageGallery({ images }: ImageGalleryProps) {
  const [selectedImage, setSelectedImage] = useState<number | null>(null)

  // Clean image URLs to get full resolution (remove query parameters)
  const cleanImageUrl = (url: string): string => {
    try {
      // Skip relative URLs - they're likely broken and shouldn't be in the database
      if (url.startsWith('/') || url.startsWith('./')) {
        console.warn('Skipping relative image URL:', url)
        return ''
      }

      const urlObj = new URL(url)
      // Remove query parameters for full-size images
      return `${urlObj.protocol}//${urlObj.host}${urlObj.pathname}`
    } catch (e) {
      console.error('Failed to parse image URL:', url, e)
      return url
    }
  }

  // Clean all image URLs and filter out invalid ones
  const cleanedImages = images.map(cleanImageUrl).filter(url => url !== '')

  if (!cleanedImages || cleanedImages.length === 0) {
    return null
  }

  const openLightbox = (index: number) => {
    setSelectedImage(index)
    // Prevent body scroll when lightbox is open
    document.body.style.overflow = 'hidden'
  }

  const closeLightbox = () => {
    setSelectedImage(null)
    document.body.style.overflow = 'auto'
  }

  const goToPrevious = () => {
    if (selectedImage !== null && selectedImage > 0) {
      setSelectedImage(selectedImage - 1)
    }
  }

  const goToNext = () => {
    if (selectedImage !== null && selectedImage < images.length - 1) {
      setSelectedImage(selectedImage + 1)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') closeLightbox()
    if (e.key === 'ArrowLeft') goToPrevious()
    if (e.key === 'ArrowRight') goToNext()
  }

  return (
    <>
      <div className="mt-8 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <ZoomIn className="w-5 h-5" />
          Article Images ({cleanedImages.length})
        </h3>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {cleanedImages.map((imageUrl, index) => (
            <button
              key={index}
              onClick={() => openLightbox(index)}
              className="relative group overflow-hidden rounded-lg border border-gray-200 hover:border-blue-500 transition-all duration-200 bg-gray-50 h-48"
              aria-label={`View image ${index + 1}`}
            >
              <img
                src={imageUrl}
                alt={`Article image ${index + 1}`}
                className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-200"
                loading="lazy"
                onError={(e) => {
                  // If image fails to load, show a placeholder or retry with original URL
                  const img = e.target as HTMLImageElement
                  if (img.src !== images[index]) {
                    img.src = images[index] // Try original URL with params
                  }
                }}
              />
              <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-opacity duration-200 flex items-center justify-center">
                <ZoomIn className="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Lightbox */}
      {selectedImage !== null && (
        <div
          className="fixed inset-0 z-50 bg-black bg-opacity-95 flex items-center justify-center p-4"
          onClick={closeLightbox}
          onKeyDown={handleKeyDown}
          tabIndex={0}
        >
          {/* Close button */}
          <button
            onClick={closeLightbox}
            className="absolute top-4 right-4 text-white hover:text-gray-300 transition-colors z-10"
            aria-label="Close lightbox"
          >
            <X className="w-8 h-8" />
          </button>

          {/* Navigation buttons */}
          {selectedImage > 0 && (
            <button
              onClick={(e) => { e.stopPropagation(); goToPrevious(); }}
              className="absolute left-4 text-white hover:text-gray-300 transition-colors z-10"
              aria-label="Previous image"
            >
              <ChevronLeft className="w-12 h-12" />
            </button>
          )}

          {selectedImage < images.length - 1 && (
            <button
              onClick={(e) => { e.stopPropagation(); goToNext(); }}
              className="absolute right-4 text-white hover:text-gray-300 transition-colors z-10"
              aria-label="Next image"
            >
              <ChevronRight className="w-12 h-12" />
            </button>
          )}

          {/* Image counter */}
          <div className="absolute top-4 left-4 text-white text-sm bg-black bg-opacity-50 px-3 py-1 rounded">
            {selectedImage + 1} / {images.length}
          </div>

          {/* Main image */}
          <div
            className="w-full h-full flex items-center justify-center p-16"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={cleanedImages[selectedImage]}
              alt={`Article image ${selectedImage + 1}`}
              className="max-w-full max-h-full object-contain"
            />
          </div>
        </div>
      )}
    </>
  )
}
