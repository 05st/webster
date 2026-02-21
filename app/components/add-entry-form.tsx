"use client";

import { useEffect, useState } from "react"
import Button from "./button"
import Card from "./card"
import Input from "./input"

const BACKEND_API_BASE = "/api/backend"

export default function AddEntryForm({ onAdd }: { onAdd: (websiteEntryId: number, websiteUrl: string, repoName: string) => void }) {
  const [repos, setRepos] = useState<string[]>([])
  const [url, setUrl] = useState("")
  const [repo, setRepo] = useState("")
  const [error, setError] = useState("")

  useEffect(() => {
    fetch(`${BACKEND_API_BASE}/github/repos`, { credentials: "include" })
      .then(res => res.json())
      .then(setRepos)
  }, [])

  function handleSubmit(e: React.SubmitEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!repos.includes(repo)) {
      setError("Please select a valid repository from the list.")
      return
    }
    if (!url) {
      setError("Please input a URL for the website.")
      return
    }
    setError("")

    fetch(`${BACKEND_API_BASE}/website-entries/add?website_url=${url}&repo_name=${repo}`, {
      method: "POST",
      credentials: "include",
    })
      .then(res => res.json())
      .then((websiteEntryId: number) => onAdd(websiteEntryId, url, repo))
    
    setUrl("")
    setRepo("")
  }

  return (
    <Card>
      <form className="flex flex-col gap-2" onSubmit={handleSubmit}>
        <Input type="url" placeholder="Website URL" value={url} onChange={e => setUrl(e.target.value)} />
        <Input list="repos" placeholder="GitHub Repository (user/repo)" value={repo} onChange={e => setRepo(e.target.value)} />
        <datalist id="repos">
          {repos.map(repo => (
            <option key={repo} value={repo} />
          ))}
        </datalist>
        {error && <p className="text-red-400 text-xs">{error}</p>}
        <Button type="submit" className="w-full text-sm">Add</Button>
      </form>
    </Card>
  )
}
