"use client"

import { useEffect, useState } from "react"
import Login from "./login"
import Dashboard from "./dashboard"

const BACKEND_API_BASE = "/api/backend"
type AuthState = "loading" | "authenticated" | "unauthenticated"

export default function Home() {
  const [authState, setAuthState] = useState<AuthState>("loading")

  useEffect(() => {
    fetch(`${BACKEND_API_BASE}/me`, { credentials: "include" })
      .then(res => setAuthState(res.ok ? "authenticated" : "unauthenticated"))
      .catch(() => setAuthState("unauthenticated"))
  }, [])

  if (authState === "loading") {
    return <div className="w-screen h-screen" />
  }

  if (authState === "unauthenticated") {
    return <Login />
  }

  return <Dashboard />
}
