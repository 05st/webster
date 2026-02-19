import { cookies } from "next/headers"
import Login from "./login"
import Dashboard from "./dashboard"

export default async function Home() {
  const user_id = (await cookies()).get("user_id")

  if (!user_id) {
    return <Login />
  } else {
    return <Dashboard user_id={user_id.value} />
  }
}
