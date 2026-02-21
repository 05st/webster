import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import "./globals.css"
import favicon16 from "./favicon-16.png"
import favicon32 from "./favicon-32.png"
import favicon96 from "./favicon-96.png"

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
})

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
})

export const metadata: Metadata = {
  title: "Webster",
  description: "The all-in-one website quality assurance engineer",
  alternates: {
    canonical: "https://webster.stimsina.com/",
  },
  icons: {
    icon: [
      { url: favicon16.src, sizes: "16x16", type: "image/png" },
      { url: favicon32.src, sizes: "32x32", type: "image/png" },
      { url: favicon96.src, sizes: "96x96", type: "image/png" },
    ],
    shortcut: [{ url: favicon32.src, type: "image/png" }],
    apple: [{ url: favicon96.src, sizes: "96x96", type: "image/png" }],
  },
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        {children}
      </body>
    </html>
  )
}
