import { useId, type ReactNode } from 'react'
import { LayoutGroup, motion, useReducedMotion } from 'motion/react'
import { motionTokens } from '@/styles/motion'

interface Option<T extends string> { value: T; label: string; icon?: ReactNode; tone?: 'warm' }

/** Native radio keyboard behavior; only the selection surface shares layout. */
export function SegmentedControl<T extends string>({ label, options, value, onChange, disabled = false }: {
  label: string; options: readonly Option<T>[]; value: T; onChange: (value: T) => void; disabled?: boolean
}) {
  const id = useId()
  const reduce = useReducedMotion()
  return <LayoutGroup id={id}><fieldset className="signal-segments" disabled={disabled}>
    <legend className="sr-only">{label}</legend>
    {options.map((option) => <label key={option.value} data-selected={option.value === value} data-tone={option.tone}>
      <input type="radio" name={id} checked={option.value === value} onChange={() => onChange(option.value)} />
      {option.value === value && <motion.span className="segment-indicator" {...(!reduce ? { layoutId: 'selection' } : {})} aria-hidden="true" transition={reduce ? { duration: 0 } : motionTokens.spring} />}
      <span className="segment-label">{option.icon}{option.label}</span>
    </label>)}
  </fieldset></LayoutGroup>
}
