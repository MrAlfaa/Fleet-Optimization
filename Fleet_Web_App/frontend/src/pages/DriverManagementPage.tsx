import { KeyRound, Pencil, Plus, RotateCcw, UserRoundCheck, X } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { Card, DataTable, EmptyState, ErrorState, LoadingState, PageHeader, PrimaryButton, SecondaryButton, StatusBadge } from '../components/UI'
import { useAsyncData } from '../hooks/useAsyncData'
import { driverAdminService } from '../services/driverAdminService'
import type { ManagedDriver } from '../services/driverAdminService'
import { ModalBody, ModalHeader, ModalPanel, ModalViewport } from '../components/ModalLayout'

const initialForm = { full_name: '', username: '', email: '', phone: '', temporary_password: '', confirm: '' }

export function DriverManagementPage() {
  const { data = [], error, loading, reload } = useAsyncData(driverAdminService.list, [])
  const [form, setForm] = useState(initialForm)
  const [showForm, setShowForm] = useState(false)
  const [actionError, setActionError] = useState('')
  const [busy, setBusy] = useState(false)
  const [editTarget, setEditTarget] = useState<ManagedDriver | null>(null)
  const [resetTarget, setResetTarget] = useState<ManagedDriver | null>(null)
  const [resetPassword, setResetPassword] = useState('')

  const createDriver = async (event: FormEvent) => {
    event.preventDefault()
    if (form.temporary_password !== form.confirm) return setActionError('Temporary passwords do not match.')
    setBusy(true); setActionError('')
    try {
      await driverAdminService.create({ full_name: form.full_name, username: form.username, email: form.email, phone: form.phone, temporary_password: form.temporary_password, is_active: true })
      setForm(initialForm); setShowForm(false); await reload()
    } catch (cause) { setActionError(cause instanceof Error ? cause.message : 'Unable to create driver') }
    finally { setBusy(false) }
  }

  const saveDriver = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); if (!editTarget) return; setBusy(true); setActionError(''); const values = new FormData(event.currentTarget); try { await driverAdminService.update(editTarget.id, { full_name: String(values.get('full_name') || ''), username: String(values.get('username') || ''), email: String(values.get('email') || ''), phone: String(values.get('phone') || '') }); setEditTarget(null); await reload() } catch (cause) { setActionError(cause instanceof Error ? cause.message : 'Unable to update driver') } finally { setBusy(false) } }
  const resetDevice = async () => { if (!resetTarget || resetPassword.length < 10) return; setBusy(true); setActionError(''); try { await driverAdminService.resetDevice(resetTarget.id, resetPassword); setResetTarget(null); setResetPassword(''); await reload() } catch (cause) { setActionError(cause instanceof Error ? cause.message : 'Unable to reset device') } finally { setBusy(false) } }

  if (loading) return <LoadingState label="Loading driver accounts" />
  if (error) return <ErrorState message={error} onRetry={reload} />

  const drivers = data ?? []
  return <div>
    <PageHeader title="Driver Management" description="Provision driver credentials, review enrolled devices, and revoke lost or replaced phones." action={<PrimaryButton onClick={() => setShowForm((value) => !value)}><Plus className="h-4 w-4" /> Create Driver</PrimaryButton>} />
    {actionError && <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{actionError}</div>}
    {showForm && <Card className="mb-5" title="New Driver Account"><form className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" onSubmit={createDriver}>
      {[
        ['full_name', 'Full name', 'Nimal Perera'], ['username', 'Username', 'driver.nimal'], ['email', 'Email', 'nimal@gmail.com'], ['phone', 'Phone number', '+94 77 123 4567'], ['temporary_password', 'Temporary password', 'Minimum 10 characters'], ['confirm', 'Confirm password', 'Repeat temporary password'],
      ].map(([key, label, placeholder]) => <label className="text-sm font-semibold text-fleet-muted" key={key}>{label}<input className="mt-2 min-h-11 w-full rounded-lg border border-fleet-line px-3 text-fleet-ink" minLength={key.includes('password') || key === 'confirm' ? 10 : undefined} onChange={(event) => setForm({ ...form, [key]: event.target.value })} placeholder={placeholder} required={key !== 'phone'} type={key.includes('password') || key === 'confirm' ? 'password' : key === 'email' ? 'email' : 'text'} value={form[key as keyof typeof form]} /></label>)}
      <div className="flex items-end"><PrimaryButton disabled={busy} type="submit"><UserRoundCheck className="h-4 w-4" /> {busy ? 'Creating...' : 'Create Driver'}</PrimaryButton></div>
    </form></Card>}
    {drivers.length === 0 ? <EmptyState description="Create the first driver account, then the driver can enroll one Android device using the temporary credentials." title="No driver accounts" /> : <DataTable headers={['Driver / Username', 'Contact', 'Device', 'Assignment', 'Status', 'Actions']}>
      {drivers.map((driver) => <tr key={driver.id}>
        <td className="px-5 py-4"><div className="font-bold">{driver.full_name}</div><div className="text-xs font-semibold text-fleet-blue">@{driver.username}</div></td>
        <td className="px-5 py-4"><div>{driver.email}</div><div className="text-xs text-fleet-muted">{driver.phone || 'No phone'}</div></td>
        <td className="px-5 py-4"><StatusBadge tone={driver.device_enrollment_status === 'enrolled' ? 'green' : 'amber'}>{driver.device_enrollment_status}</StatusBadge><div className="mt-1 text-xs text-fleet-muted">{driver.device?.device_model || 'No device registered'}</div></td>
        <td className="px-5 py-4"><div>{driver.active_route?.route_code || 'No active route'}</div><div className="text-xs text-fleet-muted">{driver.assigned_vehicle?.registration_number || 'No vehicle'}</div></td>
        <td className="px-5 py-4"><StatusBadge tone={driver.is_active ? 'green' : 'red'}>{driver.is_active ? 'Active' : 'Inactive'}</StatusBadge></td>
        <td className="px-5 py-4"><div className="flex flex-wrap gap-2"><SecondaryButton onClick={() => setEditTarget(driver)}><Pencil className="h-4 w-4" /> Edit</SecondaryButton><SecondaryButton onClick={() => setResetTarget(driver)}><RotateCcw className="h-4 w-4" /> Reset Device</SecondaryButton><SecondaryButton onClick={async () => { await driverAdminService.setActive(driver.id, !driver.is_active); await reload() }}><KeyRound className="h-4 w-4" /> {driver.is_active ? 'Deactivate' : 'Activate'}</SecondaryButton></div></td>
      </tr>)}
    </DataTable>}
    {editTarget && <Dialog title="Edit driver" onClose={() => setEditTarget(null)}><form className="space-y-4" onSubmit={saveDriver}><DialogField defaultValue={editTarget.full_name} label="Full name" name="full_name" /><DialogField defaultValue={editTarget.username} label="Username" name="username" /><DialogField defaultValue={editTarget.email} label="Email" name="email" type="email" /><DialogField defaultValue={editTarget.phone} label="Phone" name="phone" /><div className="flex justify-end gap-2"><SecondaryButton onClick={() => setEditTarget(null)}>Cancel</SecondaryButton><PrimaryButton disabled={busy} type="submit">Save driver</PrimaryButton></div></form></Dialog>}
    {resetTarget && <Dialog title={`Reset ${resetTarget.username}'s device`} onClose={() => setResetTarget(null)}><p className="mb-4 text-sm text-slate-600">This revokes the enrolled phone and all mobile sessions immediately. The driver must enroll again with the new temporary password.</p><label className="text-sm font-bold text-slate-600">New temporary password<input className="mt-2 min-h-11 w-full rounded-lg border px-3" minLength={10} onChange={(event) => setResetPassword(event.target.value)} type="password" value={resetPassword} /></label><div className="mt-5 flex justify-end gap-2"><SecondaryButton onClick={() => setResetTarget(null)}>Cancel</SecondaryButton><PrimaryButton disabled={busy || resetPassword.length < 10} onClick={resetDevice}>Reset device</PrimaryButton></div></Dialog>}
  </div>
}

function Dialog({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) { return <ModalViewport><ModalPanel aria-modal="true" className="max-w-lg" role="dialog"><ModalHeader className="flex items-center justify-between"><h2 className="text-xl font-extrabold">{title}</h2><button aria-label="Close dialog" onClick={onClose} type="button"><X className="h-5 w-5" /></button></ModalHeader><ModalBody>{children}</ModalBody></ModalPanel></ModalViewport> }
function DialogField({ label, name, defaultValue, type='text' }: { label: string; name: string; defaultValue?: string; type?: string }) { return <label className="block text-sm font-bold text-slate-600">{label}<input className="mt-2 min-h-11 w-full rounded-lg border px-3" defaultValue={defaultValue} name={name} required type={type} /></label> }
