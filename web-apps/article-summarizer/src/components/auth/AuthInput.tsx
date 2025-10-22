import React from 'react'

interface AuthInputProps {
  id: string;
  name: string;
  type: string;
  label: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  required?: boolean;
  autoComplete?: string;
  placeholder?: string;
  helperText?: string;
}

export default function AuthInput({
  id,
  name,
  type,
  label,
  value,
  onChange,
  required = false,
  autoComplete,
  placeholder,
  helperText,
}: AuthInputProps) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-gray-950 mb-2">
        {label}
      </label>
      <input
        id={id}
        name={name}
        type={type}
        autoComplete={autoComplete}
        required={required}
        value={value}
        onChange={onChange}
        className="w-full px-3 py-2 bg-white border border-slate-200 rounded text-gray-950 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-green focus:border-transparent text-sm"
        placeholder={placeholder}
      />
      {helperText && (
        <p className="mt-1 text-xs text-slate-600">{helperText}</p>
      )}
    </div>
  );
}
