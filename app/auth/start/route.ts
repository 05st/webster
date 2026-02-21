import { NextRequest, NextResponse } from "next/server"

export const runtime = "nodejs"
export const dynamic = "force-dynamic"

export async function GET(request: NextRequest) {
  const githubClientId = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID ?? process.env.GITHUB_CLIENT_ID
  if (!githubClientId) {
    return NextResponse.json({ error: "GitHub client ID is not configured" }, { status: 500 })
  }

  const redirectUri = `${request.nextUrl.origin}/api/backend/integrations/github/oauth2/callback`
  const githubUrl = new URL("https://github.com/login/oauth/authorize")
  githubUrl.searchParams.set("client_id", githubClientId)
  githubUrl.searchParams.set("redirect_uri", redirectUri)
  githubUrl.searchParams.set("scope", "repo admin:repo_hook")

  return NextResponse.redirect(githubUrl)
}
