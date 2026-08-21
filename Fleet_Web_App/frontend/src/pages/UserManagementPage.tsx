import { Check, Plus, Search, Shield, UserCog } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import type { UserRole } from '../types'
import { userAdminService } from '../services/userAdminService'
import type { ManagedUser, PermissionCatalog } from '../services/userAdminService'

const roles: Array<Exclude<UserRole, 'driver'>> = ['admin', 'fleet_manager', 'maintenance_manager', 'route_planner']
const permissionLabel = (value: string) => value.split('.').map((part) => part.replace('_', ' ')).join(' / ')

export function UserManagementPage() {
  const [users, setUsers] = useState<ManagedUser[]>([])
  const [catalog, setCatalog] = useState<PermissionCatalog | null>(null)
  const [selected, setSelected] = useState<ManagedUser | null>(null)
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([])
  const [search, setSearch] = useState('')
  const [creating, setCreating] = useState(false)
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState<string | null>(null)

  const load = async () => {
    try {
      const [userData, permissionData] = await Promise.all([userAdminService.list(), userAdminService.catalog()])
      setUsers(userData.items.filter((user) => user.role !== 'driver'))
      setCatalog(permissionData)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to load users')
    } finally { setLoading(false) }
  }
  useEffect(() => {
    void Promise.all([userAdminService.list(), userAdminService.catalog()])
      .then(([userData, permissionData]) => {
        setUsers(userData.items.filter((user) => user.role !== 'driver'))
        setCatalog(permissionData)
      })
      .catch((error: unknown) => setMessage(error instanceof Error ? error.message : 'Unable to load users'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => users.filter((user) => `${user.full_name} ${user.email} ${user.role}`.toLowerCase().includes(search.toLowerCase())), [search, users])
  const choose = (user: ManagedUser) => { setSelected(user); setSelectedPermissions(user.permissions); setCreating(false); setMessage(null) }
  const allowed = selected && catalog ? catalog.role_permissions[selected.role] ?? [] : []

  const savePermissions = async () => {
    if (!selected || selected.role === 'admin') return
    try {
      const updated = await userAdminService.setPermissions(selected.id, selectedPermissions)
      setUsers((current) => current.map((user) => user.id === updated.id ? updated : user))
      setSelected(updated); setMessage('Access policy saved.')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Unable to save permissions') }
  }

  const create = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const data = new FormData(event.currentTarget)
    try {
      await userAdminService.create({ full_name: String(data.get('full_name')), email: String(data.get('email')), phone: String(data.get('phone') || ''), password: String(data.get('password')), role: String(data.get('role')) as Exclude<UserRole, 'driver'> })
      setCreating(false); setMessage('User account created.'); await load()
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Unable to create user') }
  }

  if (loading) return <div className="rounded-lg border border-fleet-line bg-white p-8 text-sm font-semibold text-fleet-muted">Loading access policies...</div>

  return <div className="space-y-5">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><div className="text-xs font-bold uppercase tracking-wider text-fleet-blue">Administration</div><h2 className="mt-1 text-3xl font-semibold">User access control</h2><p className="mt-1 text-sm text-fleet-muted">Roles define maximum authority. Individual permissions can be restricted within that boundary.</p></div><button className="flex items-center gap-2 rounded-md bg-fleet-blue px-4 py-2.5 text-sm font-semibold text-white" onClick={() => { setCreating(true); setSelected(null) }}><Plus className="h-4 w-4" />Create user</button></div>
    {message && <div className="rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-semibold text-blue-800">{message}</div>}
    <div className="grid gap-5 lg:grid-cols-[360px_1fr]">
      <section className="rounded-lg border border-fleet-line bg-white"><div className="border-b border-fleet-line p-4"><div className="flex items-center gap-2 rounded-md border border-fleet-line px-3"><Search className="h-4 w-4 text-fleet-muted" /><input className="min-h-10 w-full outline-none" onChange={(event) => setSearch(event.target.value)} placeholder="Search users" value={search} /></div></div><div className="max-h-[640px] overflow-auto">{filtered.map((user) => <button className={`flex w-full items-center gap-3 border-b border-fleet-line p-4 text-left ${selected?.id === user.id ? 'bg-blue-50' : 'hover:bg-slate-50'}`} key={user.id} onClick={() => choose(user)}><div className="grid h-9 w-9 place-items-center rounded-full bg-slate-100 text-xs font-bold">{user.full_name.slice(0, 2).toUpperCase()}</div><div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold">{user.full_name}</div><div className="truncate text-xs text-fleet-muted">{user.email}</div></div><span className={`h-2 w-2 rounded-full ${user.is_active ? 'bg-emerald-500' : 'bg-slate-300'}`} /></button>)}</div></section>
      <section className="min-h-[520px] rounded-lg border border-fleet-line bg-white p-5">
        {creating ? <CreateUserForm onSubmit={create} /> : selected ? <><div className="flex items-start justify-between border-b border-fleet-line pb-5"><div><div className="flex items-center gap-2"><UserCog className="h-5 w-5 text-fleet-blue" /><h3 className="text-xl font-semibold">{selected.full_name}</h3></div><div className="mt-1 text-sm text-fleet-muted">{selected.role.replace('_', ' ')} · {selected.email}</div></div><button className={`rounded-md px-3 py-2 text-xs font-semibold ${selected.is_active ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'}`} onClick={async () => { await userAdminService.setActive(selected.id, !selected.is_active); await load() }}>{selected.is_active ? 'Deactivate' : 'Activate'}</button></div><div className="py-5"><div className="mb-4 flex items-center gap-2 text-sm font-semibold"><Shield className="h-4 w-4" />Effective page and action permissions</div>{selected.role === 'admin' ? <div className="rounded-md bg-emerald-50 p-4 text-sm text-emerald-800">Administrators retain complete system authority and cannot be restricted here.</div> : <div className="grid gap-4 md:grid-cols-2">{Object.entries(catalog?.groups ?? {}).map(([group, permissions]) => <div className="rounded-md border border-fleet-line p-4" key={group}><div className="mb-3 text-xs font-bold uppercase tracking-wider text-fleet-muted">{group}</div>{permissions.filter((permission) => allowed.includes(permission)).map((permission) => { const enabled = selectedPermissions.includes(permission); return <label className="flex cursor-pointer items-center justify-between gap-3 py-2 text-sm" key={permission}><span>{permissionLabel(permission)}</span><input checked={enabled} onChange={() => setSelectedPermissions((current) => enabled ? current.filter((value) => value !== permission) : [...current, permission])} type="checkbox" /></label> })}</div>)}</div>}</div>{selected.role !== 'admin' && <button className="flex items-center gap-2 rounded-md bg-fleet-blue px-4 py-2.5 text-sm font-semibold text-white" onClick={savePermissions}><Check className="h-4 w-4" />Save access policy</button>}</> : <div className="grid h-full place-items-center text-center text-sm text-fleet-muted"><div><Shield className="mx-auto mb-3 h-9 w-9 text-slate-300" />Select a user to review access.</div></div>}
      </section>
    </div>
  </div>
}

function CreateUserForm({ onSubmit }: { onSubmit: (event: FormEvent<HTMLFormElement>) => void }) {
  return <form className="max-w-xl space-y-4" onSubmit={onSubmit}><div><h3 className="text-xl font-semibold">Create web portal user</h3><p className="mt-1 text-sm text-fleet-muted">Driver credentials are provisioned from Driver Management.</p></div>{[['full_name','Full name','Operations Manager'],['email','Email','manager@organization.lk'],['phone','Phone','+94 77 000 0000'],['password','Temporary password','Minimum 8 characters']].map(([name,label,placeholder]) => <label className="block text-sm font-semibold" key={name}>{label}<input className="mt-2 min-h-11 w-full rounded-md border border-fleet-line px-3 outline-none focus:ring-2 focus:ring-blue-100" name={name} placeholder={placeholder} required={name !== 'phone'} type={name === 'password' ? 'password' : name === 'email' ? 'email' : 'text'} /></label>)}<label className="block text-sm font-semibold">Role<select className="mt-2 min-h-11 w-full rounded-md border border-fleet-line px-3" name="role">{roles.map((role) => <option key={role} value={role}>{role.replace('_', ' ')}</option>)}</select></label><button className="flex items-center gap-2 rounded-md bg-fleet-blue px-4 py-2.5 text-sm font-semibold text-white"><Check className="h-4 w-4" />Create account</button></form>
}
