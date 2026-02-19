import { ReactNode } from "react"

export default function ButtonLink(props: { children?: ReactNode; className?: string; href: string }) {
  return (
    <a href={props.href} className={`bg-slate-800 text-white p-2 rounded-lg hover:bg-slate-700 hover:cursor-pointer transition ${props.className}`}>
      {props.children}
    </a>
  )
}
