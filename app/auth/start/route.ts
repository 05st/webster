import { NextRequest, NextResponse } from "next/server"

export const runtime = "nodejs"
export const dynamic = "force-dynamic"

export async function GET(request: NextRequest) {
  const appSlug = process.env.NEXT_PUBLIC_GITHUB_APP_SLUG
  if (!appSlug) {
    return NextResponse.json({ error: "GitHub app slug is not configured" }, { status: 500 })
  }

  const redirectUri = `${request.nextUrl.origin}/api/backend/integrations/github/oauth2/callback`
  const installUrl = new URL(`https://github.com/apps/${appSlug}/installations/new`)
  installUrl.searchParams.set("redirect_uri", redirectUri)

  return NextResponse.redirect(installUrl)
}
