import Button from "./button"

export default function WebsiteEntry(props: { websiteEntryId: number; repoUrl: string; websiteUrl: string; diagnosticCount: number; onSelect: (websiteEntryId: number, websiteUrl: string) => void; selected: boolean }) {
  return (
    <Button
      onClick={() => props.onSelect(props.websiteEntryId, props.websiteUrl)}
      className={`w-full text-left flex items-center gap-2 ${props.selected ? "bg-slate-900 text-white hover:bg-slate-800" : "bg-white border border-slate-200 hover:bg-slate-50"}`}
    >
      <img
        src={`https://www.google.com/s2/favicons?domain_url=${props.websiteUrl}&sz=32`}
        className="w-4 h-4 rounded-sm shrink-0"
        alt=""
        onError={(e) => { (e.target as HTMLImageElement).style.display = "none" }}
      />
      <div className="flex flex-col gap-0.5 min-w-0 flex-1">
        <p className="text-sm truncate">{props.websiteUrl}</p>
        <p className={`text-xs truncate ${props.selected ? "text-slate-400" : "text-slate-500"}`}>{props.repoUrl}</p>
      </div>
      {props.diagnosticCount > 0 && (
        <span className={`shrink-0 text-xs font-medium px-1.5 py-0.5 rounded-full ${props.selected ? "bg-white/20 text-white" : "bg-slate-100 text-slate-600"}`}>
          {props.diagnosticCount}
        </span>
      )}
    </Button>
  )
}
