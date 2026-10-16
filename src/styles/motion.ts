/** Seconds for Motion/GSAP; keep CSS millisecond tokens in tokens.css aligned. */
export const motionTokens = {
  duration: { instant: 0, fast: 0.16, standard: 0.26, expressive: 0.6, deliberate: 0.6 },
  ease: [0.22, 1, 0.36, 1] as const,
  gsapEase: 'power3.out',
  transition: { duration: 0.26, ease: [0.22, 1, 0.36, 1] as const },
  spring: { type: 'spring', stiffness: 430, damping: 38, mass: 0.8 } as const,
  route: { draw: 0.6, signal: 0.54, arrival: 0.72, card: 0.9, history: 0.96 },
} as const
