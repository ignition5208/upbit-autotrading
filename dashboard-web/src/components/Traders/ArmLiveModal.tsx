import { useState } from 'react'

export default function ArmLiveModal({
  show,
  traderId,
  onClose,
  onSubmit
}: {
  show: boolean
  traderId: number | null
  onClose: () => void
  onSubmit: (traderId: number, confirmToken?: string) => Promise<void>
}) {
  const [confirmToken, setConfirmToken] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  if (!show || traderId === null) return null

  async function submit() {
    if (traderId === null) return   // ✅ 추가
    setBusy(true)
    setErr(null)
    try {
      await onSubmit(traderId, confirmToken || undefined)
      onClose()
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setBusy(false)
    }
  }


  return (
    <div className="modal d-block" tabIndex={-1} style={{ background: 'rgba(0,0,0,.55)' }}>
      <div className="modal-dialog">
        <div className="modal-content">
          <div className="modal-header border-bottom border-soft">
            <h5 className="modal-title">Arm LIVE</h5>
            <button className="btn-close btn-close-white" onClick={onClose} />
          </div>

          <div className="modal-body">
            {err ? <div className="alert alert-danger">{err}</div> : null}
            <div className="text-muted-2 small">LIVE 모드에서 실제 주문이 가능해집니다.</div>
            <div className="mt-2">
              <label className="form-label text-muted-2">confirm_token (CRAZY only)</label>
              <input
                className="form-control bg-panel-2 border-soft text-white mono"
                value={confirmToken}
                onChange={(e) => setConfirmToken(e.target.value)}
                placeholder="optional"
              />
            </div>
            <div className="mt-2 p-2 rounded-3 border border-soft bg-panel-2 text-muted-2 small">
              정책: CRAZY + LIVE는 2단계 확인 + confirm_token 필요
            </div>
          </div>

          <div className="modal-footer border-top border-soft">
            <button className="btn badge-soft" onClick={onClose} disabled={busy}>Cancel</button>
            <button className="btn btn-accent" onClick={submit} disabled={busy}>Arm</button>
          </div>
        </div>
      </div>
    </div>
  )
}
