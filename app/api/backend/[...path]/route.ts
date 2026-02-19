import { NextRequest } from "next/server"

export const runtime = "nodejs"
export const dynamic = "force-dynamic"

const BACKEND_URL = process.env.BACKEND_URL

async function proxy(request: NextRequest, path: string[]) {
  if (!BACKEND_URL) {
    return Response.json({ error: "BACKEND_URL is not configured" }, { status: 500 })
  }

  let backendBase: URL
  try {
    backendBase = new URL(BACKEND_URL)
  } catch {
    return Response.json({ error: "BACKEND_URL is invalid" }, { status: 500 })
  }

  if (backendBase.pathname !== "/" && backendBase.pathname !== "") {
    return Response.json(
      { error: "BACKEND_URL must be domain root only (no path), e.g. https://st-xxxx--api.modal.run" },
      { status: 500 }
    )
  }

  const targetUrl = new URL(`${path.join("/")}${request.nextUrl.search}`, backendBase)

  const headers = new Headers(request.headers)
  headers.delete("host")
  headers.delete("connection")

  const method = request.method
  const hasBody = method !== "GET" && method !== "HEAD"

  const backendResponse = await fetch(targetUrl, {
    method,
    headers,
    body: hasBody ? await request.arrayBuffer() : undefined,
    redirect: "manual",
  })

  const responseHeaders = new Headers(backendResponse.headers)
  // Node fetch may transparently decode upstream compressed responses.
  // Remove encoding/length headers so the browser does not try to decode again.
  responseHeaders.delete("content-encoding")
  responseHeaders.delete("content-length")
  responseHeaders.delete("transfer-encoding")
  responseHeaders.set("x-webster-proxy-target", targetUrl.toString())

  return new Response(backendResponse.body, {
    status: backendResponse.status,
    statusText: backendResponse.statusText,
    headers: responseHeaders,
  })
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params
  return proxy(request, path)
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params
  return proxy(request, path)
}

export async function PUT(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params
  return proxy(request, path)
}

export async function PATCH(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params
  return proxy(request, path)
}

export async function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params
  return proxy(request, path)
}

export async function OPTIONS(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params
  return proxy(request, path)
}
