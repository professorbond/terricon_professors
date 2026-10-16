import { useRef } from 'react'
import { gsap, useGSAP } from '@/lib/gsap'
import { motionTokens } from '@/styles/motion'

// Once per app lifetime, including return from logout. No persistent user tracking.
let introHasPlayed = false

export function useLoginIntro() {
  const root = useRef<HTMLDivElement>(null)
  const animateThisMount = useRef(!introHasPlayed)

  useGSAP(() => {
    const element = root.current
    if (!element) return
    element.dataset.intro = 'complete'
    if (!animateThisMount.current) return
    introHasPlayed = true
    const media = gsap.matchMedia()
    media.add('(prefers-reduced-motion: no-preference)', () => {
      element.dataset.intro = 'running'
      const timeline = gsap.timeline({ defaults: { ease: motionTokens.gsapEase }, onComplete: () => { element.dataset.intro = 'complete' } })
      timeline.fromTo('.js-route', { strokeDasharray: 1, strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.4, stagger: 0.07 }, 0)
        .from('.js-title-line', { yPercent: 108, duration: 0.4, stagger: 0.045 }, 0.12)
        .from('.js-form-reveal', { opacity: 0.45, y: 6, duration: motionTokens.duration.standard, stagger: 0.05 }, 0.32)
        .fromTo('.cta-sweep', { xPercent: -110, opacity: 1 }, { xPercent: 110, opacity: 0, duration: 0.32 }, 0.49)
      return () => { element.dataset.intro = 'complete' }
    })
    return () => media.revert()
  }, { scope: root })

  return root
}
