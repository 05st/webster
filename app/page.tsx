"use client"

import { useEffect, useState } from "react"
import Login from "./login"
import Dashboard from "./dashboard"

const BACKEND_API_BASE = "/api/backend"
type AuthState = "loading" | "authenticated" | "unauthenticated"

function LoadingScreen() {
  return (
    <main className="w-screen h-screen flex items-center justify-center p-6">
      <div
        className="flex items-center gap-3 text-sm text-gray-600"
        role="status"
        aria-live="polite"
        aria-busy="true"
      >
        {/* Simple spinner */}
        <div
          className="h-4 w-4 rounded-full border-2 border-gray-300 border-t-gray-700 animate-spin"
          aria-hidden="true"
        />
        <span>Checking session…</span>
      </div>
    </main>
  )
}

export default function Home() {
  const [authState, setAuthState] = useState<AuthState>("loading")

  useEffect(() => {
    fetch(`${BACKEND_API_BASE}/me`, { credentials: "include" })
      .then(res => setAuthState(res.ok ? "authenticated" : "unauthenticated"))
      .catch(() => setAuthState("unauthenticated"))
  }, [])

  if (authState === "loading") {
    return <LoadingScreen />
  }

  if (authState === "unauthenticated") {
    return <Login />
  }

  return <Dashboard />
}
