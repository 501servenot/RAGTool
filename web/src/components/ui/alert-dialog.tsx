import * as React from 'react'
import { createPortal } from 'react-dom'

import { cn } from '../../lib/utils'

interface AlertDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: React.ReactNode
}

export function AlertDialog({ open, onOpenChange, children }: AlertDialogProps) {
  React.useEffect(() => {
    if (!open) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onOpenChange(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [open, onOpenChange])

  if (!open || typeof document === 'undefined') {
    return null
  }

  return createPortal(
    <div className="ui-alert-dialog" role="presentation">
      {children}
    </div>,
    document.body,
  )
}

export function AlertDialogContent({
  className,
  children,
  onPointerDownOutside,
}: React.HTMLAttributes<HTMLDivElement> & {
  onPointerDownOutside?: () => void
}) {
  return (
    <div className="ui-alert-dialog__overlay" onClick={onPointerDownOutside}>
      <div
        role="alertdialog"
        aria-modal="true"
        className={cn('ui-alert-dialog__content', className)}
        onClick={(event) => event.stopPropagation()}
      >
        {children}
      </div>
    </div>
  )
}

export function AlertDialogHeader({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('ui-alert-dialog__header', className)} {...props} />
}

export function AlertDialogTitle({
  className,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn('ui-alert-dialog__title', className)} {...props} />
}

export function AlertDialogDescription({
  className,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('ui-alert-dialog__description', className)} {...props} />
}

export function AlertDialogFooter({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('ui-alert-dialog__footer', className)} {...props} />
}
