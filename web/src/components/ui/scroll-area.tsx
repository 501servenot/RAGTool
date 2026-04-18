import * as React from 'react'

import { cn } from '../../lib/utils'

export const ScrollArea = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => {
  return <div ref={ref} className={cn('ui-scroll-area', className)} {...props} />
})

ScrollArea.displayName = 'ScrollArea'
