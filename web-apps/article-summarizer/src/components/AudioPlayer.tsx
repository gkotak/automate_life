'use client'

import { useEffect } from 'react'
import { Headphones } from 'lucide-react'

interface AudioPlayerProps {
  audioUrl: string
  onPlayerReady?: (jumpToTime: (seconds: number) => void) => void
  title?: string
  className?: string
}

export default function AudioPlayer({ audioUrl, onPlayerReady, title = 'Listen to Audio', className = '' }: AudioPlayerProps) {
  useEffect(() => {
    // Function to jump to specific time in audio
    const jumpToAudioTime = (seconds: number) => {
      const audioPlayer = document.getElementById('audio-player') as HTMLAudioElement
      if (audioPlayer) {
        audioPlayer.currentTime = seconds
        audioPlayer.play()
        // Ensure 2x speed after seeking
        setTimeout(() => {
          audioPlayer.playbackRate = 2.0
        }, 100)
        console.log(`Jumped to ${seconds}s at 2x speed in audio`)
      } else {
        console.warn('Audio player not found')
      }
    }

    // Add jumpToAudioTime to global scope
    ;(window as any).jumpToAudioTime = jumpToAudioTime

    // Notify parent component that player is ready
    if (onPlayerReady) {
      onPlayerReady(jumpToAudioTime)
    }

    // Store audio element reference for easy access
    const audioElement = document.getElementById('audio-player') as HTMLAudioElement
    if (audioElement) {
      ;(window as any).audioPlayer = audioElement
    }

    return () => {
      delete (window as any).audioPlayer
      delete (window as any).jumpToAudioTime
    }
  }, [audioUrl, onPlayerReady])

  return (
    <div className={`bg-white rounded-lg shadow-md p-4 sm:p-6 ${className}`}>
      <div className="space-y-2 sm:space-y-3">
        <h3 className="text-lg sm:text-xl font-semibold text-gray-900 flex items-center gap-2">
          <Headphones className="h-5 w-5" />
          {title}
        </h3>
        <p className="text-xs sm:text-sm text-gray-600">
          ⚡ Audio automatically plays at 2x speed for efficient listening. You can adjust speed in player controls.
        </p>
        <audio
          id="audio-player"
          controls
          controlsList="nodownload"
          className="w-full max-w-full sm:max-w-[600px]"
          onLoadedMetadata={(e) => {
            const audioEl = e.target as HTMLAudioElement
            audioEl.playbackRate = 2.0
          }}
        >
          <source src={audioUrl} type="audio/mpeg" />
          Your browser does not support the audio element.
        </audio>
        <p className="text-xs text-gray-500">
          <strong>Note:</strong> Audio content embedded from original source.
        </p>
      </div>
    </div>
  )
}
