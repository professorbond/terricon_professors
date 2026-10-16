import type { ComponentPropsWithoutRef } from 'react'

type ButtonProps = ComponentPropsWithoutRef<'button'> & {
  variant?: 'primary' | 'secondary' | 'quiet'
}

/** Native button semantics; navigation uses a Link, never an onClick redirect. */
export function Button({ variant = 'primary', className = '', type = 'button', children, ...props }: ButtonProps) {
  return <button {...props} type={type} className={`button button--${variant} ${className}`}><span className="button-content">{children}</span></button>
}
