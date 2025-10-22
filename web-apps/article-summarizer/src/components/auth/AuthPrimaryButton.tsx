import React from 'react'

interface AuthPrimaryButtonProps {
  type?: 'button' | 'submit' | 'reset';
  disabled?: boolean;
  loading?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
}

export default function AuthPrimaryButton({
  type = 'button',
  disabled = false,
  loading = false,
  children,
  onClick,
}: AuthPrimaryButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md text-white font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      style={{ backgroundColor: '#077331' }}
      onMouseEnter={(e) => !disabled && !loading && (e.currentTarget.style.backgroundColor = '#065a27')}
      onMouseLeave={(e) => !disabled && !loading && (e.currentTarget.style.backgroundColor = '#077331')}
    >
      {children}
    </button>
  );
}
