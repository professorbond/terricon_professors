/** Coordinates are shared by SVG paths and the native station buttons. */
export const routeGeometry = {
  horizontal: {
    width: 1000, height: 300,
    points: [[44, 58], [494, 58], [956, 58]] as const,
    rejected: [956, 208] as const,
    submitted: 'M44 58 H172 Q190 58 204 72 L258 126 Q272 140 292 140 H340 Q360 140 374 126 L428 72 Q442 58 462 58 H494',
    approved: 'M494 58 H956',
    rejection: 'M494 58 H630 Q650 58 664 72 L786 194 Q800 208 820 208 H956',
  },
  vertical: {
    width: 320, height: 430,
    points: [[24, 34], [24, 194], [24, 354]] as const,
    rejected: [64, 354] as const,
    submitted: 'M24 34 V194',
    approved: 'M24 194 V354',
    rejection: 'M24 194 V252 Q24 270 42 270 H46 Q64 270 64 288 V354',
  },
} as const
