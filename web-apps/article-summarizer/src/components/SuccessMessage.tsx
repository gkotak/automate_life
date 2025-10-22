interface SuccessMessageProps {
  title: string;
  message: string;
}

export default function SuccessMessage({ title, message }: SuccessMessageProps) {
  return (
    <div className="text-center py-8">
      <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#077331" strokeWidth="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
          <polyline points="22 4 12 14.01 9 11.01" />
        </svg>
      </div>
      <h3 className="text-xl font-semibold text-gray-950 mb-2">{title}</h3>
      <p className="text-sm text-gray-600">{message}</p>
    </div>
  );
}
