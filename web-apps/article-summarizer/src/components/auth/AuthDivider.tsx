import React from 'react'

interface AuthDividerProps {
  text: string;
}

export default function AuthDivider({ text }: AuthDividerProps) {
  return (
    <div className="relative">
      <div className="absolute inset-0 flex items-center">
        <div className="w-full border-t border-slate-200"></div>
      </div>
      <div className="relative flex justify-center text-sm">
        <span className="px-2 bg-white text-slate-500">{text}</span>
      </div>
    </div>
  );
}
