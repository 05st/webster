import { ReactNode } from "react"

export default function Card(props: { children?: ReactNode; className?: string }): ReactNode {
  return (
    <div className={`bg-white border border-slate-200 p-4 rounded-lg shadow-sm ${props.className}`}>
      {props.children}
    </div>
  )
}
