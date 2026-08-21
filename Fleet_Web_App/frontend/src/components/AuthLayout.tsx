import { Activity, ArrowRight, Eye, EyeOff, LockKeyhole, Mail, Route, ShieldCheck, Truck } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { authService } from '../services/authService'
import { FleetAccessShader } from './FleetAccessShader'

const startupSteps = ['Verifying access policy', 'Loading operational workspace', 'Synchronizing fleet intelligence']

export function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [startupStep, setStartupStep] = useState(-1)
  const navigate = useNavigate()

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    const data = new FormData(event.currentTarget)
    try {
      await authService.login({ email: String(data.get('email') || '').trim(), password: String(data.get('password') || '') })
      for (let index = 0; index < startupSteps.length; index += 1) {
        setStartupStep(index)
        await new Promise((resolve) => window.setTimeout(resolve, 300))
      }
      navigate('/dashboard')
    } catch (caught) {
      setStartupStep(-1)
      setError(caught instanceof Error ? caught.message : 'Unable to authenticate this account')
    } finally {
      setSubmitting(false)
    }
  }

  return <main className="relative min-h-screen overflow-hidden bg-[#07111f] text-white" data-auth-mode={mode}>
    <FleetAccessShader />
    <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(5,13,25,0.18)_0%,rgba(5,13,25,0.42)_52%,rgba(5,13,25,0.94)_76%)]" />
    <div className="relative z-10 grid min-h-screen lg:grid-cols-[minmax(0,1fr)_480px]">
      <section className="flex min-h-[42vh] flex-col justify-between px-6 py-7 sm:px-10 lg:min-h-screen lg:px-14 lg:py-10">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center border border-white/20 bg-white/10 text-cyan-200 backdrop-blur-sm"><Truck className="h-5 w-5" /></div>
          <div><div className="text-lg font-bold">FleetOpt AI</div><div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-300">Sri Lanka Operations</div></div>
        </div>
        <div className="max-w-2xl pb-6 lg:pb-14">
          <div className="mb-5 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300"><span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />Intelligence network online</div>
          <h1 className="max-w-xl text-4xl font-semibold leading-tight sm:text-5xl lg:text-6xl">One command surface for safer, smarter fleet operations.</h1>
          <p className="mt-5 max-w-xl text-sm leading-7 text-slate-300 sm:text-base">Vehicle readiness, parcel demand, dispatch decisions, and live route execution in one secured workspace.</p>
          <div className="mt-8 grid max-w-xl grid-cols-3 gap-px overflow-hidden border border-white/12 bg-white/10">
            <Signal icon={ShieldCheck} label="Fleet health" value="Protected" />
            <Signal icon={Activity} label="Demand signal" value="Synchronized" />
            <Signal icon={Route} label="Route engine" value="Operational" />
          </div>
        </div>
      </section>
      <section className="flex items-center border-t border-white/10 bg-[#07111f]/88 px-6 py-10 backdrop-blur-xl sm:px-10 lg:min-h-screen lg:border-l lg:border-t-0 lg:px-12">
        <div className="w-full">
          <div className="mb-9">
            <div className="mb-4 grid h-10 w-10 place-items-center border border-blue-400/30 bg-blue-500/10 text-blue-300"><LockKeyhole className="h-5 w-5" /></div>
            <h2 className="text-3xl font-semibold">Secure workspace access</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">Your account role and assigned permissions are verified by the FleetOpt backend.</p>
          </div>
          <form className="space-y-5" onSubmit={submit}>
            <AuthField icon={Mail} label="Work email" name="email" placeholder="name@organization.lk" type="email" />
            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-200" htmlFor="password">Password</label>
              <div className="flex min-h-[52px] items-center border border-slate-700 bg-slate-950/55 px-4 transition focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-500/20">
                <LockKeyhole className="h-4 w-4 text-slate-500" />
                <input autoComplete="current-password" className="auth-dark-input min-h-[52px] flex-1 bg-transparent px-3 text-sm text-white outline-none placeholder:text-slate-600" id="password" name="password" placeholder="Enter your password" required type={showPassword ? 'text' : 'password'} />
                <button aria-label={showPassword ? 'Hide password' : 'Show password'} className="p-2 text-slate-400 hover:text-white" onClick={() => setShowPassword((value) => !value)} type="button">{showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button>
              </div>
            </div>
            {error && <div className="border-l-2 border-red-400 bg-red-500/10 px-4 py-3 text-sm text-red-200" role="alert">{error}</div>}
            <button className="group flex min-h-[52px] w-full items-center justify-center gap-3 bg-blue-600 px-5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-wait disabled:opacity-70" disabled={submitting} type="submit">
              {submitting ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" /> : <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />}
              {submitting ? 'Authenticating securely' : 'Enter operations workspace'}
            </button>
          </form>
          <div className="mt-8 flex items-center justify-between border-t border-slate-800 pt-5 text-xs text-slate-500"><span>Accounts are provisioned by an administrator.</span><span className="font-semibold text-emerald-400">API secured</span></div>
        </div>
      </section>
    </div>
    {startupStep >= 0 && <StartupOverlay activeStep={startupStep} />}
  </main>
}

function AuthField({ icon: Icon, label, name, placeholder, type }: { icon: typeof Mail; label: string; name: string; placeholder: string; type: string }) {
  return <div><label className="mb-2 block text-sm font-semibold text-slate-200" htmlFor={name}>{label}</label><div className="flex min-h-[52px] items-center border border-slate-700 bg-slate-950/55 px-4 transition focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-500/20"><Icon className="h-4 w-4 text-slate-500" /><input autoComplete="username" className="auth-dark-input min-h-[52px] flex-1 bg-transparent px-3 text-sm text-white outline-none placeholder:text-slate-600" id={name} name={name} placeholder={placeholder} required type={type} /></div></div>
}

function Signal({ icon: Icon, label, value }: { icon: typeof ShieldCheck; label: string; value: string }) {
  return <div className="bg-[#081527]/88 p-4 backdrop-blur-sm"><Icon className="mb-5 h-4 w-4 text-blue-300" /><div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">{label}</div><div className="mt-1 text-xs font-semibold text-slate-200">{value}</div></div>
}

function StartupOverlay({ activeStep }: { activeStep: number }) {
  return <div aria-live="polite" className="fixed inset-0 z-50 grid place-items-center bg-[#06101d]/96 px-6 backdrop-blur-xl" role="status"><div className="w-full max-w-md"><div className="mb-8 h-px overflow-hidden bg-slate-800"><div className="h-full w-full origin-left animate-pulse bg-blue-400" /></div><div className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-300">FleetOpt secure startup</div><h2 className="mt-3 text-3xl font-semibold">Preparing your workspace</h2><div className="mt-8 space-y-3">{startupSteps.map((step, index) => <div className={`flex items-center gap-3 text-sm ${index <= activeStep ? 'text-white' : 'text-slate-600'}`} key={step}><span className={`h-2 w-2 rounded-full ${index < activeStep ? 'bg-emerald-400' : index === activeStep ? 'animate-pulse bg-blue-400' : 'bg-slate-700'}`} />{step}</div>)}</div></div></div>
}
