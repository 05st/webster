import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"
import Button from "./button"

const mdComponents = {
  p: ({ children }: any) => <p className="mb-1 last:mb-0">{children}</p>,
  ul: ({ children }: any) => <ul className="list-disc pl-4 mb-1 space-y-0.5">{children}</ul>,
  ol: ({ children }: any) => <ol className="list-decimal pl-4 mb-1 space-y-0.5">{children}</ol>,
  li: ({ children }: any) => <li>{children}</li>,
  strong: ({ children }: any) => <strong className="font-semibold text-slate-800">{children}</strong>,
  em: ({ children }: any) => <em className="italic">{children}</em>,
  a: ({ href, children }: any) => <a href={href} className="text-blue-600 underline" target="_blank" rel="noreferrer">{children}</a>,
  code: ({ children }: any) => <code className="bg-slate-100 px-1 rounded font-mono text-slate-700">{children}</code>,
  pre: ({ children }: any) => <pre className="bg-slate-100 p-2 rounded font-mono text-slate-700 overflow-x-auto mb-1 [&_code]:bg-transparent [&_code]:p-0">{children}</pre>,
}

const severityStyles: Record<string, { border: string; dot: string }> = {
  error:   { border: "border-l-red-400",   dot: "bg-red-400" },
  warning: { border: "border-l-amber-400", dot: "bg-amber-400" },
  info:    { border: "border-l-blue-400",  dot: "bg-blue-400" },
}

export default function DiagnosticCard({ shortDesc, fullDesc, severity, onDismiss, onFix }: { shortDesc: string; fullDesc: string; severity: string; onDismiss: () => void; onFix: () => void }) {
  const { border, dot } = severityStyles[severity] ?? severityStyles.warning

  return (
    <div className={`bg-white border border-slate-200 border-l-4 ${border} p-4 rounded-lg shadow-sm flex flex-col gap-2`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dot}`} />
          <p className="text-sm text-slate-800 leading-snug font-medium">{shortDesc}</p>
        </div>
        <button
          onClick={onDismiss}
          className="text-slate-400 hover:text-slate-700 hover:cursor-pointer transition shrink-0 mt-0.5"
          aria-label="Dismiss"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
          </svg>
        </button>
      </div>
      <div className="text-xs text-slate-500 leading-relaxed">
        <Markdown remarkPlugins={[remarkGfm]} components={mdComponents}>{fullDesc}</Markdown>
      </div>
      <Button onClick={onFix} className="self-start text-xs px-2 py-1">Fix</Button>
    </div>
  )
}
