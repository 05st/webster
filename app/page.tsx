"use client"

import { useEffect, useState } from "react"
import Login from "./login"
import Dashboard from "./dashboard"
import GithubAppModal from "./components/github-app-modal"

const BACKEND_API_BASE = "/api/backend"
type AuthState = "loading" | "authenticated" | "unauthenticated"

export default function Home() {
  const [authState, setAuthState] = useState<AuthState>("loading")
  const [showInstallModal, setShowInstallModal] = useState(false)

  useEffect(() => {
    fetch(`${BACKEND_API_BASE}/me`, { credentials: "include" })
      .then(res => {
        if (res.ok) {
          setAuthState("authenticated")
          fetch(`${BACKEND_API_BASE}/github/app-installed`, { credentials: "include" })
            .then(r => r.json())
            .then(data => { if (!data.installed) setShowInstallModal(true) })
            .catch(() => {})
        } else {
          setAuthState("unauthenticated")
        }
      })
      .catch(() => setAuthState("unauthenticated"))
  }, [])

  if (authState === "loading") {
    return <div className="w-screen h-screen" />
  }

  if (authState === "unauthenticated") {
    return <Login />
  }

  return (
    <>
      <Dashboard />
      {showInstallModal && <GithubAppModal onDismiss={() => setShowInstallModal(false)} />}
    </>
  )
}
