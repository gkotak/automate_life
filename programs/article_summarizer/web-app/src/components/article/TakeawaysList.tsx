import { Star } from 'lucide-react'

interface TakeawaysListProps {
  takeaways: string[]
}

export default function TakeawaysList({ takeaways }: TakeawaysListProps) {
  if (!takeaways || takeaways.length === 0) {
    return null
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
        ⭐ Key Takeaways
        <span className="text-sm font-normal text-gray-500">({takeaways.length})</span>
      </h3>

      <div className="space-y-2">
        {takeaways.map((takeaway, index) => (
          <div
            key={index}
            className="flex items-start gap-3 p-3 bg-yellow-50 rounded-lg border border-yellow-100"
          >
            <Star className="h-4 w-4 text-yellow-600 shrink-0 mt-1" />
            <p className="text-gray-800 leading-relaxed">{takeaway}</p>
          </div>
        ))}
      </div>
    </div>
  )
}