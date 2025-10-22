interface ErrorMessageProps {
  message: string;
}

export default function ErrorMessage({ message }: ErrorMessageProps) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3">
      <p className="text-sm text-red-800">{message}</p>
    </div>
  );
}
