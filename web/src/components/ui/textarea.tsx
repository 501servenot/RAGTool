import * as React from 'react'

import { cn } from '../../lib/utils'

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => {
  return (
    <textarea
      ref={ref}
      data-slot="textarea"
      className={cn('ui-textarea ui-textarea--shadcn', className)}
      {...props}
    />
  )
})

Textarea.displayName = 'Textarea'
