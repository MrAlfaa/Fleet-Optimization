import { Check, ChevronRight, LockKeyhole, Plus, RotateCcw, Search, Shield, UserCog } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import type { UserRole } from '../types'
import { userAdminService } from '../services/userAdminService'
import type { ManagedUser, PermissionCatalog } from '../services/userAdminService'
import { togglePermission } from '../utils/permissions'

const roles: Array<Exclude<UserRole, 'driver'>> = ['admin', 'fleet_manager', 'maintenance_manager', 'route_planner']
const accessViews = [
  { id: 'page', label: 'Pages & Forms' },
  { id: 'tab', label: 'Workspace Tabs' },
  { id: 'action', label: 'Actions' },
] as const
type AccessView = typeof accessViews[number]['id']

const samePermissions = (left: string[], right: string[]) => [...left].sort().join('|') === [...right].sort().join('|')
const roleLabel = (role: string) => role.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
const fetchAccessData = () => Promise.all([userAdminService.list(), userAdminService.catalog()])

export function UserManagementPage() {
  const [users, setUsers] = useState<ManagedUser[]>([])
  const [catalog, setCatalog] = useState<PermissionCatalog | null>(null)
  const [selected, setSelected] = useState<ManagedUser | null>(null)
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([])
  const [accessView, setAccessView] = useState<AccessView>('page')
  const [search, setSearch] = useState('')
  const [creating, setCreating] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const load = async () => {
    try {
      const [userData, permissionData] = await fetchAccessData()
      setUsers(userData.items.filter((user) => user.role !== 'driver'))
      setCatalog(permissionData)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to load users')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    fetchAccessData()
      .then(([userData, permissionData]) => {
        if (!active) return
        setUsers(userData.items.filter((user) => user.role !== 'driver'))
        setCatalog(permissionData)
      })
      .catch((error: unknown) => {
        if (active) setMessage(error instanceof Error ? error.message : 'Unable to load users')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [])

  const filtered = useMemo(
    () => users.filter((user) => `${user.full_name} ${user.email} ${user.role}`.toLowerCase().includes(search.toLowerCase())),
    [search, users],
  )
  const protectedAdmin = selected?.role === 'admin'
  const effectiveSelection = protectedAdmin && catalog ? Object.keys(catalog.items) : selectedPermissions
  const dirty = Boolean(selected && !protectedAdmin && !samePermissions(selected.permissions, selectedPermissions))

  const leaveCurrentPolicy = () => !dirty || window.confirm('Discard the unsaved access changes?')
  const choose = (user: ManagedUser) => {
    if (!leaveCurrentPolicy()) return
    setSelected(user)
    setSelectedPermissions(user.permissions)
    setCreating(false)
    setMessage(null)
  }

  const savePermissions = async () => {
    if (!selected || protectedAdmin || !dirty) return
    setSaving(true)
    try {
      const updated = await userAdminService.setPermissions(selected.id, selectedPermissions)
      setUsers((current) => current.map((user) => user.id === updated.id ? updated : user))
      setSelected(updated)
      setSelectedPermissions(updated.permissions)
      setMessage('Access policy saved. New requests now use this policy.')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to save permissions')
    } finally {
      setSaving(false)
    }
  }

  const create = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    try {
      await userAdminService.create({
        full_name: String(data.get('full_name')),
        email: String(data.get('email')),
        phone: String(data.get('phone') || ''),
        password: String(data.get('password')),
        role: String(data.get('role')) as Exclude<UserRole, 'driver'>,
      })
      setCreating(false)
      setMessage('User account created with the selected role template.')
      await load()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to create user')
    }
  }

  if (loading) return <div className="rounded-lg border border-fleet-line bg-white p-8 text-sm font-semibold text-fleet-muted">Loading access policies...</div>

  return <div className="min-w-0 space-y-5">
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <div className="text-xs font-bold uppercase text-fleet-blue">Administration</div>
        <h2 className="mt-1 text-3xl font-semibold">User access control</h2>
        <p className="mt-1 max-w-3xl text-sm text-fleet-muted">Roles provide an initial access template. Each non-admin user can then receive an individual page, tab, and action policy.</p>
      </div>
      <button className="flex min-h-11 items-center gap-2 rounded-md bg-fleet-blue px-4 text-sm font-semibold text-white transition hover:bg-blue-700" onClick={() => { if (leaveCurrentPolicy()) { setCreating(true); setSelected(null) } }} type="button"><Plus className="h-4 w-4" />Create user</button>
    </div>

    {message && <div className="rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-semibold text-blue-800" role="status">{message}</div>}

    <div className="grid min-w-0 gap-5 xl:grid-cols-[340px_minmax(0,1fr)]">
      <section className="min-w-0 overflow-hidden rounded-lg border border-fleet-line bg-white">
        <div className="border-b border-fleet-line p-4">
          <label className="flex items-center gap-2 rounded-md border border-fleet-line px-3">
            <Search className="h-4 w-4 text-fleet-muted" />
            <span className="sr-only">Search users</span>
            <input className="min-h-10 min-w-0 w-full outline-none" onChange={(event) => setSearch(event.target.value)} placeholder="Search users" value={search} />
          </label>
        </div>
        <div className="max-h-[680px] overflow-y-auto">
          {filtered.map((user) => <button aria-label={`${user.full_name} ${user.email}`} className={`flex w-full items-center gap-3 border-b border-fleet-line p-4 text-left transition ${selected?.id === user.id ? 'bg-blue-50' : 'hover:bg-slate-50'}`} key={user.id} onClick={() => choose(user)} type="button">
            <div className={`grid h-10 w-10 shrink-0 place-items-center rounded-full text-xs font-bold ${user.role === 'admin' ? 'bg-blue-100 text-blue-800' : 'bg-slate-100 text-slate-700'}`}>{user.full_name.slice(0, 2).toUpperCase()}</div>
            <div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold">{user.full_name}</div><div className="truncate text-xs text-fleet-muted">{user.email}</div><div className="mt-1 text-[11px] font-semibold text-slate-500">{roleLabel(user.role)}</div></div>
            {user.role === 'admin' ? <LockKeyhole className="h-4 w-4 text-blue-600" /> : <span aria-label={user.is_active ? 'Active' : 'Inactive'} className={`h-2.5 w-2.5 rounded-full ${user.is_active ? 'bg-emerald-500' : 'bg-slate-300'}`} />}
          </button>)}
        </div>
      </section>

      <section className="min-h-[560px] min-w-0 overflow-hidden rounded-lg border border-fleet-line bg-white">
        {creating ? <CreateUserForm onSubmit={create} /> : selected && catalog ? <>
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-fleet-line p-5">
            <div><div className="flex items-center gap-2"><UserCog className="h-5 w-5 text-fleet-blue" /><h3 className="text-xl font-semibold">{selected.full_name}</h3></div><div className="mt-1 text-sm text-fleet-muted">{roleLabel(selected.role)} · {selected.email}</div></div>
            {protectedAdmin ? <span className="inline-flex min-h-9 items-center gap-2 rounded-md bg-blue-50 px-3 text-xs font-bold text-blue-800"><LockKeyhole className="h-4 w-4" />Protected administrator</span> : <button className={`min-h-9 rounded-md px-3 text-xs font-semibold transition ${selected.is_active ? 'bg-red-50 text-red-700 hover:bg-red-100' : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'}`} onClick={async () => { await userAdminService.setActive(selected.id, !selected.is_active); await load() }} type="button">{selected.is_active ? 'Deactivate' : 'Activate'}</button>}
          </div>

          {protectedAdmin && <div className="m-5 flex gap-3 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900"><Shield className="mt-0.5 h-5 w-5 shrink-0" /><div><div className="font-bold">Administrator access is protected</div><p className="mt-1 text-blue-800">Every administrator always has complete access. Permissions and account status cannot be changed from this workspace.</p></div></div>}

          <div className="border-b border-fleet-line px-5 pt-1">
            <div className="flex max-w-full gap-1 overflow-x-auto" role="tablist" aria-label="Access policy sections">
              {accessViews.map((view) => <button aria-selected={accessView === view.id} className={`min-h-11 whitespace-nowrap border-b-2 px-4 text-sm font-semibold ${accessView === view.id ? 'border-blue-600 text-blue-700' : 'border-transparent text-slate-500 hover:text-slate-800'}`} key={view.id} onClick={() => setAccessView(view.id)} role="tab" type="button">{view.label}</button>)}
            </div>
          </div>

          <PermissionEditor catalog={catalog} disabled={protectedAdmin} permissions={effectiveSelection} type={accessView} onToggle={(permission, enabled) => setSelectedPermissions((current) => togglePermission(current, permission, enabled, catalog.items))} />

          {!protectedAdmin && <div className="sticky bottom-0 flex flex-wrap items-center justify-between gap-3 border-t border-fleet-line bg-white p-4 pb-[max(1rem,env(safe-area-inset-bottom))] shadow-[0_-8px_24px_rgba(15,23,42,0.06)]">
            <button className="flex min-h-10 items-center gap-2 rounded-md px-3 text-sm font-semibold text-slate-600 transition hover:bg-slate-100" onClick={() => setSelectedPermissions(catalog.role_permissions[selected.role] ?? [])} type="button"><RotateCcw className="h-4 w-4" />Reset to role template</button>
            <div className="flex items-center gap-3"><span className="text-xs font-semibold text-slate-500">{dirty ? 'Unsaved changes' : 'Policy is up to date'}</span><button className="flex min-h-10 items-center gap-2 rounded-md bg-fleet-blue px-4 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50" disabled={!dirty || saving} onClick={savePermissions} type="button"><Check className="h-4 w-4" />{saving ? 'Saving...' : 'Save access policy'}</button></div>
          </div>}
        </> : <div className="grid min-h-[560px] place-items-center p-8 text-center text-sm text-fleet-muted"><div><Shield className="mx-auto mb-3 h-9 w-9 text-slate-300" /><div className="font-semibold text-slate-700">Select a user</div><p className="mt-1">Review or update the user's individual access policy.</p></div></div>}
      </section>
    </div>
  </div>
}

function PermissionEditor({ catalog, permissions, type, disabled, onToggle }: { catalog: PermissionCatalog; permissions: string[]; type: AccessView; disabled: boolean; onToggle: (permission: string, enabled: boolean) => void }) {
  const groups = Object.entries(catalog.groups).map(([name, keys]) => ({ name, items: keys.map((key) => catalog.items[key]).filter((item) => item?.type === type) })).filter((group) => group.items.length)
  return <div className="min-h-[380px] p-5" role="tabpanel">
    <div className="mb-4"><h4 className="font-semibold text-slate-900">{accessViews.find((view) => view.id === type)?.label}</h4><p className="mt-1 text-sm text-slate-500">{type === 'page' ? 'Controls which primary workspaces and forms appear for this user.' : type === 'tab' ? 'Controls sections inside an authorized workspace.' : 'Controls commands that create or change operational data.'}</p></div>
    <div className="grid gap-4 lg:grid-cols-2">
      {groups.map((group) => <fieldset className="min-w-0 rounded-lg border border-fleet-line p-4" key={group.name}><legend className="px-1 text-xs font-bold uppercase text-slate-500">{group.name}</legend><div className="divide-y divide-slate-100">{group.items.map((item) => { const enabled = permissions.includes(item.key); return <label className={`flex min-w-0 items-start gap-3 py-3 ${disabled ? 'cursor-not-allowed' : 'cursor-pointer'}`} key={item.key}><input aria-label={item.label} checked={enabled} className="mt-1 h-4 w-4 accent-blue-600" disabled={disabled} onChange={(event) => onToggle(item.key, event.target.checked)} type="checkbox" /><span className="min-w-0 flex-1"><span className="block text-sm font-semibold text-slate-800">{item.label}</span><span className="mt-0.5 block text-xs leading-5 text-slate-500">{item.description}</span>{item.parent && <span className="mt-1 inline-flex items-center text-[11px] font-semibold text-blue-700"><ChevronRight className="h-3 w-3" />Requires {catalog.items[item.parent]?.label ?? item.parent}</span>}</span></label> })}</div></fieldset>)}
    </div>
  </div>
}

function CreateUserForm({ onSubmit }: { onSubmit: (event: FormEvent<HTMLFormElement>) => void }) {
  return <form className="max-w-2xl space-y-5 p-5" onSubmit={onSubmit}>
    <div><h3 className="text-xl font-semibold">Create web portal user</h3><p className="mt-1 text-sm text-fleet-muted">The selected role supplies the initial access template. Individual access can be adjusted after creation.</p></div>
    <div className="grid gap-4 sm:grid-cols-2">{[['full_name','Full name','Operations Manager'],['email','Email','manager@organization.lk'],['phone','Phone','+94 77 000 0000'],['password','Temporary password','Minimum 8 characters']].map(([name,label,placeholder]) => <label className="block text-sm font-semibold" key={name}>{label}<input className="mt-2 min-h-11 w-full rounded-md border border-fleet-line px-3 outline-none focus:ring-2 focus:ring-blue-100" name={name} placeholder={placeholder} required={name !== 'phone'} type={name === 'password' ? 'password' : name === 'email' ? 'email' : 'text'} /></label>)}</div>
    <label className="block text-sm font-semibold">Role<select className="mt-2 min-h-11 w-full rounded-md border border-fleet-line bg-white px-3" name="role">{roles.map((role) => <option key={role} value={role}>{roleLabel(role)}</option>)}</select></label>
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><strong>Administrator accounts are permanent full-access accounts.</strong> Their access policy and account status cannot be changed after creation.</div>
    <button className="flex min-h-11 items-center gap-2 rounded-md bg-fleet-blue px-4 text-sm font-semibold text-white transition hover:bg-blue-700"><Check className="h-4 w-4" />Create account</button>
  </form>
}
