import { ReactNode } from "react"
import { twMerge } from "tailwind-merge"

export default function Button(props: { children?: ReactNode; className?: string; type?: "submit" | "reset" | "button"; onClick?: () => void }) {
  return (
    <button type={props.type} onClick={props.onClick} className={twMerge("bg-slate-100 text-slate-800 p-2 hover:bg-slate-200 hover:cursor-pointer transition rounded-lg", props.className)}>
      {props.children}
    </button>
  )
}
