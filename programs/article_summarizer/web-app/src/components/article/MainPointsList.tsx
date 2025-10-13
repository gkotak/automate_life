import { MainPoint } from '@/lib/supabase'
import { CheckCircle } from 'lucide-react'

interface MainPointsListProps {
  points: MainPoint[]
}

export default function MainPointsList({ points }: MainPointsListProps) {
  if (!points || points.length === 0) {
    return null
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
        📋 Main Points
        <span className="text-sm font-normal text-gray-500">({points.length})</span>
      </h3>

      <div className="space-y-3">
        {points.map((point, index) => (
          <div
            key={index}
            className="flex items-start gap-3 p-3 bg-green-50 rounded-lg border border-green-100"
          >
            <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-gray-800 leading-relaxed">{point.point}</p>
              {point.details && (
                <p className="text-gray-600 text-sm mt-2">{point.details}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}