import { InputHTMLAttributes } from "react"
import { twMerge } from "tailwind-merge"

export default function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={twMerge(
        "bg-white border border-slate-300 rounded-lg p-2 text-sm w-full outline-none focus:border-slate-500 transition placeholder:text-slate-400",
        className
      )}
    />
  )
}
