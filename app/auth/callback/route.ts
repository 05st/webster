import { NextRequest, NextResponse } from "next/server"

export function GET(request: NextRequest) {
  const userId = request.nextUrl.searchParams.get("user_id")
  const redirectUrl = new URL("/", request.url)

  if (!userId) {
    return NextResponse.redirect(redirectUrl)
  }

  const response = NextResponse.redirect(redirectUrl)
  response.cookies.set("user_id", userId, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  })
  return response
}
