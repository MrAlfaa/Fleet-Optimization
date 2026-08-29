import { Download, FileSpreadsheet, Upload, X } from 'lucide-react'
import { useState } from 'react'
import { fleetService } from '../services/fleetService'
import type { Vehicle } from '../types'
import { saveDownload } from '../utils/download'
import { showToast } from '../utils/toast'
import { ModalBody, ModalFooter, ModalHeader, ModalPanel, ModalViewport } from './ModalLayout'
import { PrimaryButton, SecondaryButton } from './UI'

const MAX_BYTES = 5 * 1024 * 1024

export function MaintenanceHistoryImportDialog({ vehicle, onClose, onImported }: {
  vehicle: Vehicle
  onClose: () => void
  onImported: () => void | Promise<void>
}) {
  const [file, setFile] = useState<File | null>(null)
  const [working, setWorking] = useState<'download' | 'import' | null>(null)
  const [error, setError] = useState('')

  const downloadTemplate = async () => {
    setWorking('download')
    setError('')
    try {
      const result = await fleetService.downloadMaintenanceHistoryTemplate(vehicle.id)
      saveDownload(result.blob, result.filename)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to download the template')
    } finally {
      setWorking(null)
    }
  }

  const chooseFile = (selected: File | null) => {
    setError('')
    if (!selected) return setFile(null)
    if (!selected.name.toLowerCase().endsWith('.xlsx')) {
      setFile(null)
      return setError('Select the completed FleetOpt .xlsx template.')
    }
    if (selected.size > MAX_BYTES) {
      setFile(null)
      return setError('The workbook must be 5 MB or smaller.')
    }
    setFile(selected)
  }

  const importHistory = async () => {
    if (!file) return
    setWorking('import')
    setError('')
    try {
      const result = await fleetService.importMaintenanceHistory(vehicle.id, file)
      await onImported()
      showToast({ tone: 'success', title: 'Service history imported', message: `${result.imported_count} completed record(s) were added.` })
      onClose()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The workbook could not be imported')
    } finally {
      setWorking(null)
    }
  }

  return <ModalViewport>
    <ModalPanel aria-modal="true" className="max-w-2xl" role="dialog">
      <ModalHeader className="flex items-start justify-between gap-4">
        <div><h2 className="text-xl font-extrabold text-slate-950">Import service history</h2><p className="mt-1 text-sm text-slate-500">Add verified completed records for {vehicle.registrationNumber}.</p></div>
        <button aria-label="Close history import" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100" onClick={onClose} type="button"><X className="h-5 w-5" /></button>
      </ModalHeader>
      <ModalBody className="space-y-5">
        <section className="rounded-lg border border-blue-200 bg-blue-50 p-4">
          <div className="flex items-start gap-3"><FileSpreadsheet className="mt-0.5 h-5 w-5 shrink-0 text-blue-700" /><div><h3 className="font-extrabold text-blue-950">Use the controlled template</h3><p className="mt-1 text-sm text-blue-800">Download the vehicle-specific workbook, keep its headers and dropdown values unchanged, then upload it here. The whole file is rejected if any row is invalid.</p></div></div>
          <div className="mt-4"><SecondaryButton disabled={working !== null} onClick={downloadTemplate}><Download className="h-4 w-4" />{working === 'download' ? 'Preparing...' : 'Download Excel Template'}</SecondaryButton></div>
        </section>
        <label className="block text-sm font-bold text-slate-700">Completed template
          <span className="mt-2 flex min-h-28 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 text-center transition hover:border-blue-400 hover:bg-blue-50">
            <Upload className="h-6 w-6 text-blue-600" />
            <span className="mt-2 font-semibold text-slate-800">{file?.name ?? 'Choose an .xlsx workbook'}</span>
            <span className="mt-1 text-xs font-medium text-slate-500">Maximum 5 MB and 1,000 history rows</span>
          </span>
          <input accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" className="sr-only" onChange={(event) => chooseFile(event.target.files?.[0] ?? null)} type="file" />
        </label>
        {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700" role="alert">{error}</div>}
      </ModalBody>
      <ModalFooter>
        <SecondaryButton disabled={working !== null} onClick={onClose}>Cancel</SecondaryButton>
        <PrimaryButton disabled={!file || working !== null} onClick={importHistory}><Upload className="h-4 w-4" />{working === 'import' ? 'Validating...' : 'Validate and Import'}</PrimaryButton>
      </ModalFooter>
    </ModalPanel>
  </ModalViewport>
}
