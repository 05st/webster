"use client"

import { useEffect, useState } from "react"
import DiagnosticCard from "./diagnostic-card"

type Diagnostic = { diagnosticId: number; shortDesc: string; fullDesc: string; severity: string }
const BACKEND_URL = process.env.BACKEND_URL

export default function DiagnosticList({ websiteEntryId, refreshKey, onDiagnosticChange }: { websiteEntryId: number; refreshKey: number; onDiagnosticChange: () => void }) {
  const [diagnostics, setDiagnostics] = useState<Diagnostic[]>([])

  useEffect(() => {
    fetch(`${BACKEND_URL}/diagnostics?website_entry_id=${websiteEntryId}`, { credentials: "include" })
      .then(res => res.json())
      .then(setDiagnostics)
  }, [websiteEntryId, refreshKey])

  function handleDismiss(diagnosticId: number) {
    fetch(`${BACKEND_URL}/diagnostics/${diagnosticId}`, {
      method: "DELETE",
      credentials: "include",
    })
    setDiagnostics(prev => prev.filter(i => i.diagnosticId !== diagnosticId))
    onDiagnosticChange()
  }

  function handleFix(_diagnosticId: number) {
    // todo
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
