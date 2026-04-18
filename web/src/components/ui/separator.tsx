import * as React from 'react'

import { cn } from '../../lib/utils'

interface SeparatorProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: 'horizontal' | 'vertical'
}

export function Separator({
  className,
  orientation = 'horizontal',
  ...props
}: SeparatorProps) {
  return (
    <div
      aria-hidden="true"
      className={cn('ui-separator', `ui-separator--${orientation}`, className)}
      {...props}
    />
  )
}
