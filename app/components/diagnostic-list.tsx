"use client"

import { useEffect, useState } from "react"
import DiagnosticCard from "./diagnostic-card"

type Diagnostic = { diagnosticId: number; shortDesc: string; fullDesc: string; severity: string }
const BACKEND_API_BASE = "/api/backend"

export default function DiagnosticList({ websiteEntryId, refreshKey, onDiagnosticChange, onFix }: { websiteEntryId: number; refreshKey: number; onDiagnosticChange: () => void; onFix: (shortDesc: string, fullDesc: string) => void }) {
  const [diagnostics, setDiagnostics] = useState<Diagnostic[]>([])

  useEffect(() => {
    fetch(`${BACKEND_API_BASE}/diagnostics?website_entry_id=${websiteEntryId}`, { credentials: "include" })
      .then(res => res.json())
      .then(setDiagnostics)
  }, [websiteEntryId, refreshKey])

  function handleDismiss(diagnosticId: number) {
    fetch(`${BACKEND_API_BASE}/diagnostics/${diagnosticId}`, {
      method: "DELETE",
      credentials: "include",
    })
    setDiagnostics(prev => prev.filter(i => i.diagnosticId !== diagnosticId))
    onDiagnosticChange()
  }

  function handleFix(diagnosticId: number) {
    const d = diagnostics.find(i => i.diagnosticId === diagnosticId)
    if (d) onFix(d.shortDesc, d.fullDesc)
  }

  return (
    <div className="h-full flex flex-col gap-2 overflow-y-auto">
      {diagnostics.length === 0 ? (
        <p className="text-xs text-slate-400">No diagnostics yet.</p>
      ) : (
        diagnostics.map(diagnostic => (
          <DiagnosticCard
            key={diagnostic.diagnosticId}
            shortDesc={diagnostic.shortDesc}
            fullDesc={diagnostic.fullDesc}
            severity={diagnostic.severity}
            onDismiss={() => handleDismiss(diagnostic.diagnosticId)}
            onFix={() => handleFix(diagnostic.diagnosticId)}
          />
        ))
      )}
    </div>
  )
}
