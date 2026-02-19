"use client"

import { useEffect, useState } from "react"
import WebsiteEntry from "./website-entry"
import AddEntryForm from "./add-entry-form"

type Entry = { websiteEntryId: number; websiteUrl: string; repoName: string; diagnosticCount: number }
const BACKEND_API_BASE = "/api/backend"

export default function WebsiteList({ selectedWebsiteEntryId, onSelect, refreshKey }: { selectedWebsiteEntryId: number | null; onSelect: (websiteEntryId: number, websiteUrl: string) => void; refreshKey: number }) {
  const [entries, setEntries] = useState<Entry[]>([])

  useEffect(() => {
    fetch(`${BACKEND_API_BASE}/website-entries`, { credentials: "include" })
      .then(res => res.json())
      .then(setEntries)
  }, [refreshKey])

  function handleAdd(websiteEntryId: number, websiteUrl: string, repoName: string) {
    setEntries(prev => [...prev, { websiteEntryId, websiteUrl, repoName, diagnosticCount: 0 }])
  }

  return (
    <>
      {entries.map(entry => (
        <WebsiteEntry
          key={entry.websiteEntryId}
          websiteEntryId={entry.websiteEntryId}
          websiteUrl={entry.websiteUrl}
          repoUrl={entry.repoName}
          diagnosticCount={entry.diagnosticCount}
          onSelect={onSelect}
          selected={entry.websiteEntryId === selectedWebsiteEntryId}
        />
      ))}
      <AddEntryForm onAdd={handleAdd} />
    </>
  )
}
