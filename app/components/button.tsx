import { ReactNode } from "react"
import { twMerge } from "tailwind-merge"

export default function Button(props: { children?: ReactNode; className?: string; type?: "submit" | "reset" | "button"; onClick?: () => void; disabled?: boolean }) {
  return (
    <button type={props.type} onClick={props.onClick} disabled={props.disabled} className={twMerge("bg-slate-100 text-slate-800 p-2 hover:bg-slate-200 hover:cursor-pointer transition rounded-lg disabled:opacity-40 disabled:cursor-not-allowed", props.className)}>
      {props.children}
    </button>
  )
}
