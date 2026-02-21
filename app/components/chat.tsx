"use client"

import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react"
import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"
import Button from "./button"
import VerificationSettings from "./verification-settings"

type Message = { role: "human" | "ai"; content: string; isFixAction?: boolean; isAutomated?: boolean }
const BACKEND_API_BASE = "/api/backend"

const mdComponentsHuman = {
  p: ({ children }: any) => <p className="mb-1 last:mb-0">{children}</p>,
  h1: ({ children }: any) => <h1 className="text-base font-bold mb-1">{children}</h1>,
  h2: ({ children }: any) => <h2 className="text-sm font-bold mb-1">{children}</h2>,
  h3: ({ children }: any) => <h3 className="text-sm font-semibold mb-1">{children}</h3>,
  ul: ({ children }: any) => <ul className="list-disc list-outside pl-4 mb-1 space-y-0.5">{children}</ul>,
  ol: ({ children }: any) => <ol className="list-decimal list-outside pl-4 mb-1 space-y-0.5">{children}</ol>,
  li: ({ children }: any) => <li className="list-item">{children}</li>,
  a: ({ href, children }: any) => <a href={href} className="text-slate-300 underline" target="_blank" rel="noreferrer">{children}</a>,
  strong: ({ children }: any) => <strong className="font-semibold">{children}</strong>,
  em: ({ children }: any) => <em className="italic text-slate-300">{children}</em>,
  blockquote: ({ children }: any) => <blockquote className="border-l-2 border-slate-500 pl-2 text-slate-300 italic mb-1">{children}</blockquote>,
  code: ({ children }: any) => <code className="bg-black/20 px-1 rounded font-mono text-xs">{children}</code>,
  pre: ({ children }: any) => <pre className="bg-black/20 p-2 rounded font-mono text-xs overflow-x-auto mb-1 [&_code]:bg-transparent [&_code]:p-0">{children}</pre>,
  hr: () => <hr className="border-slate-600 my-2" />,
}

const mdComponentsAI = {
  p: ({ children }: any) => <p className="mb-1 last:mb-0">{children}</p>,
  h1: ({ children }: any) => <h1 className="text-base font-bold mb-1">{children}</h1>,
  h2: ({ children }: any) => <h2 className="text-sm font-bold mb-1">{children}</h2>,
  h3: ({ children }: any) => <h3 className="text-sm font-semibold mb-1">{children}</h3>,
  ul: ({ children }: any) => <ul className="list-disc list-outside pl-4 mb-1 space-y-0.5">{children}</ul>,
  ol: ({ children }: any) => <ol className="list-decimal list-outside pl-4 mb-1 space-y-0.5">{children}</ol>,
  li: ({ children }: any) => <li className="list-item">{children}</li>,
  a: ({ href, children }: any) => <a href={href} className="text-blue-600 underline" target="_blank" rel="noreferrer">{children}</a>,
  strong: ({ children }: any) => <strong className="font-semibold text-slate-900">{children}</strong>,
  em: ({ children }: any) => <em className="italic text-slate-600">{children}</em>,
  blockquote: ({ children }: any) => <blockquote className="border-l-2 border-slate-300 pl-2 text-slate-600 italic mb-1">{children}</blockquote>,
  code: ({ children }: any) => <code className="bg-slate-100 px-1 rounded font-mono text-xs text-slate-700">{children}</code>,
  pre: ({ children }: any) => <pre className="bg-slate-100 p-2 rounded font-mono text-xs text-slate-700 overflow-x-auto mb-1 [&_code]:bg-transparent [&_code]:p-0">{children}</pre>,
  hr: () => <hr className="border-slate-200 my-2" />,
}

const TOOL_LABELS: Record<string, string> = {
  open_page: "Opening browser...",
  click_element: "Clicking element...",
  type_into: "Typing into field...",
  press_key: "Pressing key...",
  wait_for_selector: "Waiting for element...",
  get_current_page_text: "Reading page content...",
  get_current_page_url: "Checking current URL...",
  fetch_page: "Fetching page...",
  get_page_metadata: "Reading page metadata...",
  get_page_speed: "Running performance audit...",
  submit_diagnostic: "Submitting diagnostic...",
}

function toolLabel(name: string): string {
  return TOOL_LABELS[name] ?? `Using ${name.replace(/_/g, " ")}...`
}

export type ChatHandle = { sendFix: (content: string) => void }

const Chat = forwardRef<ChatHandle, { websiteEntryId: number; websiteUrl: string; onAiMessage: () => void }>(
function Chat({ websiteEntryId, websiteUrl, onAiMessage }, ref) {
  const [tab, setTab] = useState<"chat" | "verification">("chat")
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [statusText, setStatusText] = useState("")
  const bottomRef = useRef<HTMLDivElement>(null)

  useImperativeHandle(ref, () => ({
    sendFix: (content: string) => sendMessage(content, true),
  }))

  useEffect(() => {
    fetch(`${BACKEND_API_BASE}/messages?website_entry_id=${websiteEntryId}`, { credentials: "include" })
      .then(res => res.json())
      .then((msgs: any[]) => msgs.map(m => ({ ...m, isFixAction: m.is_fix_action, isAutomated: m.is_automated })))
      .then(setMessages)
  }, [websiteEntryId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  async function sendMessage(content: string, isFixAction = false) {
    if (!content.trim() || loading) return
    setMessages(prev => [...prev, { role: "human", content, isFixAction }])
    setLoading(true)
    setStatusText("")

    const response = await fetch(`${BACKEND_API_BASE}/messages/send?website_entry_id=${websiteEntryId}&is_fix_action=${isFixAction}`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    })

    if (!response.body) { setLoading(false); return }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split("\n\n")
      buffer = parts.pop() ?? ""
      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith("data: ")) continue
        try {
          const event = JSON.parse(line.slice(6))
          if (event.type === "tool_start") {
            setStatusText(toolLabel(event.tool))
          } else if (event.type === "done") {
            setMessages(prev => [...prev, { role: "ai", content: event.content, isFixAction }])
            setLoading(false)
            setStatusText("")
            onAiMessage()
          }
        } catch { /* ignore malformed events */ }
      }
    }

    setLoading(false)
  }

  function handleSend() {
    sendMessage(input)
    setInput("")
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex-1 min-h-0 flex flex-col bg-white">
      <div className="px-3 py-2 bg-slate-50 text-xs border-b border-slate-200 flex items-center gap-2 min-w-0">
        <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 shrink-0 text-slate-400" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="1.5"/>
          <circle cx="9" cy="10" r="1.5" fill="currentColor"/>
          <circle cx="15" cy="10" r="1.5" fill="currentColor"/>
          <path d="M8.5 14.5q3.5 3 7 0" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
        <span className="truncate flex-1"><span className="text-slate-400">Chatting with Webster about </span><span className="text-slate-700">{websiteUrl}</span></span>
        {tab === "chat" && (
          <Button
            onClick={() => sendMessage("Analyze this website for issues.")}
            disabled={loading}
            className="shrink-0 text-xs px-2 py-1 bg-slate-800 text-white hover:bg-slate-700"
          >
            Analyze
          </Button>
        )}
      </div>
      <div className="flex bg-slate-50 border-b border-slate-200">
        {([["chat", "Chat"], ["verification", "Verification"]] as const).map(([t, label]) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-xs font-medium border-b-2 transition ${tab === t ? "border-slate-800 text-slate-800" : "border-transparent text-slate-400 hover:text-slate-600"}`}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "verification" ? (
        <VerificationSettings websiteEntryId={websiteEntryId} />
      ) : (
      <>
      <div className="flex-1 min-h-0 overflow-y-auto flex flex-col gap-2 pr-2">
        {messages.map((msg, i) => (
          <div key={i} className={`flex flex-col gap-0.5 ${msg.role === "human" ? "items-end ml-8 mt-2 mb-2" : "items-start ml-2 mr-8"}`}>
            {msg.isAutomated && !msg.isFixAction && (
              <div className={`flex items-center gap-1 text-xs text-blue-400 ${msg.role === "human" ? "mr-1" : "ml-2"}`}>
                <svg xmlns="http://www.w3.org/2000/svg" className="w-3 h-3" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2M9 11a2 2 0 0 0-2 2 2 2 0 0 0 2 2 2 2 0 0 0 2-2 2 2 0 0 0-2-2m6 0a2 2 0 0 0-2 2 2 2 0 0 0 2 2 2 2 0 0 0 2-2 2 2 0 0 0-2-2z"/>
                </svg>
                <span>Automated</span>
              </div>
            )}
            {msg.isFixAction && (
              <div className={`flex items-center gap-1 text-xs text-amber-500 ${msg.role === "human" ? "mr-1" : "ml-2"}`}>
                <svg xmlns="http://www.w3.org/2000/svg" className="w-3 h-3" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"/>
                </svg>
                <span>{msg.isAutomated ? "Automated fix" : "Fix action"}</span>
              </div>
            )}
            <div className={`p-3 text-sm ${msg.role === "human" ? "bg-slate-800 text-white rounded-lg" : "bg-slate-100 text-slate-800 rounded-lg"}`}>
              <Markdown remarkPlugins={[remarkGfm]} components={msg.role === "human" ? mdComponentsHuman : mdComponentsAI}>{msg.content}</Markdown>
            </div>
          </div>
        ))}
        {loading && (
          <div className="bg-slate-100 self-start mr-8 ml-2 px-4 py-3 rounded-lg flex flex-col gap-1.5">
            <div className="flex gap-1.5 items-center">
              <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
              <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
              <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" />
            </div>
            {statusText && <p className="text-xs text-slate-400">{statusText}</p>}
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="flex gap-2 p-2 mt-2 bg-slate-50 border-t border-slate-200">
        <textarea
          className="flex-1 bg-white p-2 text-sm text-slate-800 placeholder:text-slate-400 outline-none resize-none rounded-lg border border-slate-300 focus:border-slate-500 transition"
          rows={2}
          placeholder="Ask something about this website..."
          value={input}
          onChange={e => setInput(e.target.value)}
          disabled={loading}
          onKeyDown={handleKeyDown}
        />
        <button
          onClick={handleSend}
          disabled={loading}
          className="px-3 bg-slate-800 hover:bg-slate-700 hover:cursor-pointer transition rounded-lg self-stretch flex items-center justify-center"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </div>
      </>
      )}
    </div>
  )
})

export default Chat
