/**
 * Tracker phia trinh duyet.
 *
 * Moi thao tac cua nguoi dung duoc dong goi thanh mot document JSON va
 * POST sang /api/track -> ghi thang vao MongoDB collection clickstream_events.
 * Cau truc document giong het du lieu mock do seed_mongo.py sinh ra, nho vay
 * hai nguon nam chung mot khong gian phan tich o Chuong 4.
 */
const Tracker = (() => {
  // Mot phien duyet web = mot session_id, giu trong sessionStorage.
  let sessionId = sessionStorage.getItem("ecom_session");
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem("ecom_session", sessionId);
  }

  let userId = null;
  const listeners = [];

  const device = {
    platform: /Mobi|Android/i.test(navigator.userAgent) ? "mobile_web" : "desktop_web",
    user_agent: navigator.userAgent.slice(0, 120),
    screen: `${screen.width}x${screen.height}`,
  };

  async function send(eventType, payload = {}) {
    const body = {
      session_id: sessionId,
      user_id: userId,
      event_type: eventType,
      payload,
      device,
      geo: { country: "VN", province: document.getElementById("province")?.value || "Ha Noi" },
      traffic_source: { channel: "direct", campaign: "live_demo" },
    };
    try {
      const res = await fetch("/api/track", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      listeners.forEach((fn) => fn(data.event));
      return data.event;
    } catch (err) {
      console.error("Tracker loi:", err);
    }
  }

  return {
    sessionId,
    setUser: (id) => { userId = id ? Number(id) : null; },
    getUser: () => userId,
    track: send,
    onEvent: (fn) => listeners.push(fn),
  };
})();
