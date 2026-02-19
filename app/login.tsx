import ButtonLink from "./components/button-link"

export default function Login() {
  const githubClientId = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID ?? process.env.GITHUB_CLIENT_ID

  return (
    <div className="w-screen h-screen flex items-center justify-center relative overflow-hidden bg-slate-50">
      <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-slate-200 opacity-60 blur-3xl" />
      <div className="absolute -bottom-32 -right-32 w-96 h-96 rounded-full bg-slate-300 opacity-40 blur-3xl" />
      <div className="absolute top-1/2 left-1/4 w-64 h-64 rounded-full bg-slate-100 opacity-80 blur-2xl" />

      <div className="relative z-10 bg-white border border-slate-200 rounded-2xl shadow-lg p-10 flex flex-col items-center gap-6 w-80">
        <div className="w-12 h-12 rounded-xl bg-slate-900 flex items-center justify-center shadow">
          <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6 text-white" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="1.5"/>
            <circle cx="9" cy="10" r="1.5" fill="currentColor"/>
            <circle cx="15" cy="10" r="1.5" fill="currentColor"/>
            <path d="M8.5 14.5q3.5 3 7 0" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </div>

        <div className="text-center">
          <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">Webster</h1>
          <p className="text-sm text-slate-500 mt-1">Your favourite website quality assurance engineer</p>
        </div>

        <div className="w-full border-t border-slate-100" />

        {githubClientId ? (
          <ButtonLink href="/auth/start" className="w-full text-center text-sm flex items-center justify-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 .5C5.73.5.5 5.73.5 12c0 5.08 3.29 9.38 7.86 10.9.57.1.78-.25.78-.55v-1.93c-3.19.69-3.86-1.54-3.86-1.54-.52-1.33-1.27-1.68-1.27-1.68-1.04-.71.08-.7.08-.7 1.15.08 1.75 1.18 1.75 1.18 1.02 1.75 2.68 1.24 3.33.95.1-.74.4-1.24.72-1.53-2.55-.29-5.23-1.27-5.23-5.67 0-1.25.45-2.27 1.18-3.07-.12-.29-.51-1.45.11-3.02 0 0 .96-.31 3.15 1.18a10.97 10.97 0 0 1 5.74 0c2.18-1.49 3.14-1.18 3.14-1.18.63 1.57.23 2.73.11 3.02.74.8 1.18 1.82 1.18 3.07 0 4.41-2.69 5.38-5.25 5.66.41.36.78 1.06.78 2.13v3.16c0 .31.21.66.79.55C20.22 21.37 23.5 17.07 23.5 12 23.5 5.73 18.27.5 12 .5z"/>
            </svg>
            Continue with GitHub
          </ButtonLink>
        ) : (
          <p className="text-xs text-red-500">Missing GitHub client ID</p>
        )}
      </div>
    </div>
  )
}
