/**
 * Tracker hanh vi phia trinh duyet.
 *
 * Moi thao tac tren UI duoc dong goi thanh document JSON va POST sang
 * /api/track -> ghi vao MongoDB. Cau truc giong het du lieu mock do
 * seed_mongo.py sinh ra, nho vay hai nguon nam chung khong gian phan tich.
 */
import { api, type TrackedEvent } from "./api"

const KEY = "ecom_session"

let sessionId = sessionStorage.getItem(KEY)
if (!sessionId) {
  sessionId = crypto.randomUUID()
  sessionStorage.setItem(KEY, sessionId)
}

let userId: number | null = null
const listeners = new Set<(e: TrackedEvent) => void>()

const device = {
  platform: /Mobi|Android/i.test(navigator.userAgent) ? "mobile_web" : "desktop_web",
  screen: `${screen.width}x${screen.height}`,
  user_agent: navigator.userAgent.slice(0, 120),
}

export const tracker = {
  sessionId: sessionId as string,
  setUser(id: number | null) { userId = id },
  getUser: () => userId,

  async track(eventType: string, payload: Record<string, unknown> = {}, province = "Ha Noi") {
    try {
      const res = await api.track({
        session_id: sessionId as string,
        user_id: userId,
        event_type: eventType,
        payload,
        device,
        geo: { country: "VN", province },
      })
      listeners.forEach((fn) => fn(res.event))
      return res.event
    } catch (err) {
      console.error("Tracker loi:", err)
    }
  },

  subscribe(fn: (e: TrackedEvent) => void) {
    listeners.add(fn)
    return () => listeners.delete(fn)
  },
}
