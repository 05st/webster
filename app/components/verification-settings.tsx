"use client"

import { ReactNode, useEffect, useState } from "react"
import Button from "./button"
import Input from "./input"
import Toggle from "./toggle"

const BACKEND_API_BASE = "/api/backend"

type Settings = {
  enabled: boolean
  minSeverity: string
  autoFix: boolean
  pathsInScope: string
  webhookUrl: string
  webhookAuthHeaderKey: string
  webhookAuthHeaderValue: string
}

const defaultSettings: Settings = {
  enabled: false,
  minSeverity: "error",
  autoFix: false,
  pathsInScope: "",
  webhookUrl: "",
  webhookAuthHeaderKey: "",
  webhookAuthHeaderValue: "",
}

function SettingRow({ label, description, children }: { label: string; description: string; children: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-slate-800">{label}</p>
        <p className="text-xs text-slate-500 mt-0.5">{description}</p>
      </div>
      {children}
    </div>
  )
}

export default function VerificationSettings({ websiteEntryId }: { websiteEntryId: number }) {
  const [settings, setSettings] = useState<Settings>(defaultSettings)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    fetch(`${BACKEND_API_BASE}/verification-settings?website_entry_id=${websiteEntryId}`, { credentials: "include" })
      .then(res => res.json())
      .then(data => setSettings({ ...defaultSettings, ...data }))
  }, [websiteEntryId])

  async function save() {
    setSaving(true)
    await fetch(`${BACKEND_API_BASE}/verification-settings?website_entry_id=${websiteEntryId}`, {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    })
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="flex-1 min-h-0 overflow-y-auto flex flex-col gap-5 p-4">

      <SettingRow label="Enable continuous verification" description="Runs when a commit message contains a trigger keyword">
        <Toggle value={settings.enabled} onChange={v => setSettings(s => ({ ...s, enabled: v }))} />
      </SettingRow>

      <hr className="border-slate-100" />

      <SettingRow label="Minimum severity to alert" description="Diagnostics at or above this level will trigger an alert">
        <select
          value={settings.minSeverity}
          onChange={e => setSettings(s => ({ ...s, minSeverity: e.target.value }))}
          className="text-xs border border-slate-300 rounded px-2 py-1.5 bg-white text-slate-800 focus:outline-none focus:border-slate-500 shrink-0"
        >
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="error">Error</option>
        </select>
      </SettingRow>

      <hr className="border-slate-100" />

      <SettingRow label="Auto-fix & open PR" description="Automatically fix issues and open a pull request when the alert threshold is met">
        <Toggle value={settings.autoFix} onChange={v => setSettings(s => ({ ...s, autoFix: v }))} />
      </SettingRow>

      <hr className="border-slate-100" />

      <div className="flex flex-col gap-1.5">
        <p className="text-sm font-medium text-slate-800">Paths in scope</p>
        <p className="text-xs text-slate-500">Leave empty to check all pages. Comma-separated (e.g. /checkout, /login)</p>
        <Input
          className="text-xs px-2 py-1.5 rounded"
          value={settings.pathsInScope}
          onChange={e => setSettings(s => ({ ...s, pathsInScope: e.target.value }))}
          placeholder="/checkout, /login, /signup"
        />
      </div>

      <hr className="border-slate-100" />

      <div className="flex flex-col gap-2">
        <div>
          <p className="text-sm font-medium text-slate-800">Webhook URL</p>
          <p className="text-xs text-slate-500 mt-0.5">POSTed to when a diagnostic meets the alert threshold</p>
        </div>
        <Input
          type="url"
          className="text-xs px-2 py-1.5 rounded"
          value={settings.webhookUrl}
          onChange={e => setSettings(s => ({ ...s, webhookUrl: e.target.value }))}
          placeholder="https://hooks.slack.com/..."
        />
        {settings.webhookUrl && (
          <div className="flex gap-2">
            <Input
              className="text-xs px-2 py-1.5 rounded"
              value={settings.webhookAuthHeaderKey}
              onChange={e => setSettings(s => ({ ...s, webhookAuthHeaderKey: e.target.value }))}
              placeholder="Header name (e.g. Authorization)"
            />
            <Input
              className="text-xs px-2 py-1.5 rounded"
              value={settings.webhookAuthHeaderValue}
              onChange={e => setSettings(s => ({ ...s, webhookAuthHeaderValue: e.target.value }))}
              placeholder="Header value (e.g. Bearer ...)"
            />
          </div>
        )}
      </div>

      <div className="mt-auto flex items-center justify-end gap-3 pt-2">
        {saved && <span className="text-xs text-green-600">Saved</span>}
        <Button
          onClick={save}
          disabled={saving}
          className="text-xs px-3 py-1.5 bg-slate-800 text-white hover:bg-slate-700"
        >
          {saving ? "Saving..." : "Save settings"}
        </Button>
      </div>

    </div>
  )
}
