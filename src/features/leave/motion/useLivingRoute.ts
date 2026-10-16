import { useRef } from 'react'
import { gsap, useGSAP } from '@/lib/gsap'
import { motionTokens } from '@/styles/motion'

// Presentation memory only. No business state, browser persistence or API commands.
// Mark on timeline start so the StrictMode setup/cleanup rehearsal cannot consume it.
const presentedEvents = new Set<string>()
function remember(key: string) {
  presentedEvents.add(key)
  if (presentedEvents.size > 300) {
    const oldest = presentedEvents.values().next().value
    if (oldest) presentedEvents.delete(oldest)
  }
}

export function useLivingRoute(eventKey: string) {
  const root = useRef<HTMLElement>(null)
  useGSAP(() => {
    const element = root.current
    if (!element) return
    const media = gsap.matchMedia()
    media.add({ desktop: '(min-width: 768px)', mobile: '(max-width: 767px)', reduce: '(prefers-reduced-motion: reduce)' }, (context) => {
      element.dataset.motion = 'settled'
      if (context.conditions?.reduce) { remember(eventKey); return }
      if (presentedEvents.has(eventKey)) return
      const scene = element.querySelector<SVGSVGElement>(`svg[data-layout="${context.conditions?.desktop ? 'horizontal' : 'vertical'}"]`)
      const path = scene?.querySelector<SVGPathElement>('.js-route-segment[data-active="true"]')
      const signal = scene?.querySelector<SVGGElement>('.js-route-signal')
      if (!path || !signal) return
      const length = path.getTotalLength()
      const cursor = { distance: 0 }
      const start = path.getPointAtLength(0)
      gsap.set(signal, { x: start.x, y: start.y, opacity: 0 })
      const moveX = gsap.quickSetter(signal, 'x')
      const moveY = gsap.quickSetter(signal, 'y')
      const ring = element.querySelector('[data-arrival="true"] .route-arrival')
      const card = element.querySelector('.route-stage-card')
      element.dataset.motion = 'queued'
      const timeline = gsap.timeline({ paused: true, defaults: { ease: motionTokens.gsapEase },
        onStart: () => { remember(eventKey); element.dataset.motion = 'running' },
        onComplete: () => { element.dataset.motion = 'settled' },
      })
      timeline.fromTo(path, { strokeDasharray: length, strokeDashoffset: length }, { strokeDashoffset: 0, duration: motionTokens.route.draw }, 0)
        .to(signal, { opacity: 1, duration: 0.08 }, 0.18)
        .to(cursor, { distance: length, duration: motionTokens.route.signal, ease: 'power1.inOut', onUpdate: () => {
          const point = path.getPointAtLength(cursor.distance)
          moveX(point.x); moveY(point.y)
        } }, 0.2)
        .to(signal, { opacity: 0, duration: motionTokens.duration.fast }, 0.74)
      if (ring) timeline.fromTo(ring, { scale: 0.7, opacity: 0 }, { scale: 1, opacity: 1, duration: motionTokens.duration.fast }, motionTokens.route.arrival)
        .to(ring, { scale: 1.7, opacity: 0, duration: motionTokens.duration.standard }, 0.88)
      if (card) timeline.fromTo(card, { opacity: 0.55, y: 6 }, { opacity: 1, y: 0, duration: motionTokens.duration.standard }, motionTokens.route.card)
      // A below-the-fold mobile route waits for visibility, never blocking its controls.
      const observer = new IntersectionObserver((entries) => {
        if (entries.some((entry) => entry.isIntersecting)) { timeline.play(); observer.disconnect() }
      }, { threshold: 0.15 })
      observer.observe(element.querySelector('.route-graphic') ?? element)
      return () => { observer.disconnect(); element.dataset.motion = 'settled' }
    })
    return () => media.revert()
  }, { scope: root, dependencies: [eventKey], revertOnUpdate: true })
  return root
}
