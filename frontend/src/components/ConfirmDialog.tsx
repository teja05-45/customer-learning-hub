import { useEffect, useState } from 'react'
import { Button, Modal } from 'react-bootstrap'
import { AlertTriangle } from 'lucide-react'

export function ConfirmDialog({
  show,
  title,
  children,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  destructive = false,
  busy = false,
  requirePhrase,
  onConfirm,
  onCancel,
}: {
  show: boolean
  title: string
  children?: React.ReactNode
  confirmLabel?: string
  cancelLabel?: string
  destructive?: boolean
  busy?: boolean
  requirePhrase?: string
  onConfirm: () => void
  onCancel: () => void
}) {
  const [phrase, setPhrase] = useState('')

  useEffect(() => {
    if (!show) setPhrase('')
  }, [show])

  const blocked = Boolean(requirePhrase) && phrase.trim().toUpperCase() !== (requirePhrase ?? '').toUpperCase()

  return (
    <Modal show={show} onHide={onCancel} centered backdrop="static" keyboard={!busy}>
      <Modal.Header closeButton={!busy}>
        <Modal.Title className="d-flex align-items-center gap-2">
          {destructive && <AlertTriangle size={16} color="var(--clh-danger)" />}
          {title}
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {children}
        {requirePhrase && (
          <div className="mt-3">
            <label className="form-label" htmlFor="confirm-phrase">
              Type <span className="mono">{requirePhrase}</span> to continue
            </label>
            <input
              id="confirm-phrase"
              className="form-control"
              value={phrase}
              onChange={(event) => setPhrase(event.target.value)}
              autoComplete="off"
            />
          </div>
        )}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="outline-secondary" onClick={onCancel} disabled={busy}>
          {cancelLabel}
        </Button>
        <Button
          variant={destructive ? 'danger' : 'primary'}
          onClick={onConfirm}
          disabled={busy || blocked}
        >
          {busy ? 'Working…' : confirmLabel}
        </Button>
      </Modal.Footer>
    </Modal>
  )
}
