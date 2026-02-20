"use client"

import { useState } from "react"
import WebsiteList from "./components/website-list"
import Chat from "./components/chat"
import DiagnosticList from "./components/diagnostic-list"

export default function Dashboard() {
  const [selected, setSelected] = useState<{ websiteEntryId: number; websiteUrl: string } | null>(null)
  const [visitedEntries, setVisitedEntries] = useState<{ websiteEntryId: number; websiteUrl: string }[]>([])
  const [diagnosticRefreshKey, setDiagnosticRefreshKey] = useState(0)
  const [websiteListRefreshKey, setWebsiteListRefreshKey] = useState(0)

  function handleSelect(websiteEntryId: number, websiteUrl: string) {
    setSelected({ websiteEntryId, websiteUrl })
    setVisitedEntries(prev =>
      prev.some(e => e.websiteEntryId === websiteEntryId)
        ? prev
        : [...prev, { websiteEntryId, websiteUrl }]
    )
  }

  function handleDiagnosticChange() {
    setWebsiteListRefreshKey(k => k + 1)
  }

  function handleAiMessage() {
    setDiagnosticRefreshKey(k => k + 1)
    setWebsiteListRefreshKey(k => k + 1)
  }

  return (
    <div className="w-screen h-screen grid grid-cols-4">
      <div className="p-4 flex flex-col gap-2 overflow-y-auto border-r border-slate-200">
        <WebsiteList selectedWebsiteEntryId={selected?.websiteEntryId ?? null} onSelect={handleSelect} refreshKey={websiteListRefreshKey} />
      </div>
      <div className="mt-4 mb-4 col-span-2 min-h-0 flex flex-col">
        {selected === null ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 text-slate-400">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-12 h-12" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="1.5"/>
              <circle cx="9" cy="10" r="1.5" fill="currentColor"/>
              <circle cx="15" cy="10" r="1.5" fill="currentColor"/>
              <path d="M8.5 14.5q3.5 3 7 0" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            <p className="text-sm">Select a website to start chatting with Webster</p>
          </div>
        ) : (
          visitedEntries.map(entry => (
            <div key={entry.websiteEntryId} className={`flex-1 min-h-0 flex flex-col ${selected.websiteEntryId !== entry.websiteEntryId ? "hidden" : ""}`}>
              <Chat websiteEntryId={entry.websiteEntryId} websiteUrl={entry.websiteUrl} onAiMessage={handleAiMessage} />
            </div>
          ))
        )}
      </div>
      <div className="p-4 overflow-y-auto border-l border-slate-200">
        {selected !== null && <DiagnosticList websiteEntryId={selected.websiteEntryId} refreshKey={diagnosticRefreshKey} onDiagnosticChange={handleDiagnosticChange} />}
      </div>
    </div>
  )
}
