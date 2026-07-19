import { MCP_WIDGET_URI } from "../lib/contracts";

export { MCP_WIDGET_URI as WIDGET_URI };

export function dashboardWidgetHtml() {
  return `<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>
    :root { color-scheme: light dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; padding: 12px; background: transparent; color: light-dark(#2b241f,#f6f0e8); }
    .shell { overflow: hidden; border: 1px solid light-dark(#eadfd4,#4c433c); border-radius: 24px; background: light-dark(#fffdf9,#241f1b); box-shadow: 0 16px 42px rgba(62,38,18,.12); }
    .hero { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:22px; background:linear-gradient(125deg,#ffcf58 0%,#ff9f5d 55%,#f66a63 100%); color:#2b1b14; }
    .brand { display:flex; align-items:center; gap:12px; }
    .mark { display:grid; place-items:center; width:42px; height:42px; border-radius:15px; background:rgba(255,255,255,.72); font-size:25px; font-weight:900; color:#c4362d; }
    h1 { margin:0; font-size:19px; letter-spacing:-.02em; }
    .sub { margin:3px 0 0; font-size:12px; opacity:.72; }
    button { border:0; border-radius:999px; padding:9px 13px; background:#30231e; color:#fff; font-weight:700; cursor:pointer; }
    button:disabled { opacity:.55; cursor:wait; }
    .content { padding:18px; }
    .kpis { display:grid; grid-template-columns:repeat(4,1fr); gap:9px; }
    .kpi { min-width:0; padding:14px; border-radius:17px; background:light-dark(#f8f3ed,#302a25); }
    .label { font-size:10px; text-transform:uppercase; letter-spacing:.08em; color:light-dark(#77695f,#c9baaf); }
    .value { margin-top:7px; font-size:24px; font-weight:850; letter-spacing:-.04em; }
    .grid { display:grid; grid-template-columns:1.25fr .75fr; gap:10px; margin-top:10px; }
    .panel { padding:15px; border:1px solid light-dark(#eee3d8,#443b35); border-radius:18px; }
    .panel h2 { margin:0 0 10px; font-size:13px; }
    .event { display:flex; gap:10px; align-items:center; padding:9px 0; border-top:1px solid light-dark(#eee3d8,#443b35); }
    .event:first-of-type { border-top:0; }
    .date { min-width:42px; padding:7px 5px; border-radius:11px; text-align:center; background:light-dark(#fff1d1,#513f29); color:light-dark(#8b4e00,#ffd483); font-weight:800; font-size:11px; }
    .event strong { display:block; font-size:12px; }
    .event span { font-size:10px; color:light-dark(#77695f,#c9baaf); }
    .task { display:flex; align-items:center; gap:8px; margin:8px 0; font-size:11px; }
    .dot { width:8px; height:8px; border-radius:50%; background:#f66a63; }
    .empty { color:light-dark(#77695f,#c9baaf); font-size:11px; }
    .foot { display:flex; justify-content:space-between; align-items:center; margin-top:13px; font-size:10px; color:light-dark(#87786d,#b9aaa0); }
    @media(max-width:620px){ .kpis{grid-template-columns:repeat(2,1fr)} .grid{grid-template-columns:1fr} .hero{align-items:flex-start} }
  </style>
</head>
<body>
  <main class="shell">
    <header class="hero">
      <div class="brand"><div class="mark">9</div><div><h1>9 Freunde · Tagesblick</h1><p class="sub">Verwaltung, die mehr Zeit für Kinder lässt.</p></div></div>
      <button id="refresh" type="button">Aktualisieren</button>
    </header>
    <section class="content">
      <div class="kpis" id="kpis"></div>
      <div class="grid"><div class="panel"><h2>Nächste Termine</h2><div id="events"></div></div><div class="panel"><h2>Was Aufmerksamkeit braucht</h2><div id="tasks"></div></div></div>
      <div class="foot"><span id="mode">Sicherer Demo-Modus</span><span id="updated">—</span></div>
    </section>
  </main>
  <script type="module">
    const state = { data: null, requestId: 0, pending: new Map() };
    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[char]);
    const date = (value) => new Intl.DateTimeFormat(document.documentElement.lang || "de-DE", {day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit"}).format(new Date(value));
    function render(data) {
      state.data = data;
      const stats = data?.stats ?? {};
      const items = [["Aktive Kinder",stats.activeChildren??0],["Dokumente offen",stats.openDocuments??0],["Überfällige Rechnungen",stats.overdueInvoices??0],["Nächste Termine",stats.upcomingEvents??0]];
      document.querySelector("#kpis").innerHTML = items.map(([label,value]) => '<div class="kpi"><div class="label">'+esc(label)+'</div><div class="value">'+esc(value)+'</div></div>').join("");
      const events = Array.isArray(data?.events) ? data.events : [];
      document.querySelector("#events").innerHTML = events.length ? events.slice(0,3).map((event) => '<div class="event"><div class="date">'+esc(date(event.start))+'</div><div><strong>'+esc(event.title)+'</strong><span>'+esc(event.location||"9 Freunde")+'</span></div></div>').join("") : '<p class="empty">Keine anstehenden Termine.</p>';
      const tasks = Array.isArray(data?.tasks) ? data.tasks : [];
      document.querySelector("#tasks").innerHTML = tasks.length ? tasks.slice(0,4).map((task) => '<div class="task"><span class="dot"></span><span>'+esc(task)+'</span></div>').join("") : '<p class="empty">Alles im grünen Bereich.</p>';
      document.querySelector("#mode").textContent = data?.mode === "google" ? "Google Workspace verbunden" : "Sicherer Demo-Modus";
      document.querySelector("#updated").textContent = data?.generatedAt ? "Stand "+date(data.generatedAt) : "—";
    }
    function request(method, params) {
      const id = ++state.requestId;
      window.parent.postMessage({jsonrpc:"2.0",id,method,params},"*");
      return new Promise((resolve,reject) => state.pending.set(id,{resolve,reject}));
    }
    window.addEventListener("message", (event) => {
      if (event.source !== window.parent) return;
      const message = event.data;
      if (!message || message.jsonrpc !== "2.0") return;
      if (message.method === "ui/notifications/tool-result") render(message.params?.structuredContent);
      if (message.id && state.pending.has(message.id)) {
        const pending = state.pending.get(message.id); state.pending.delete(message.id);
        if (message.error) pending.reject(message.error); else pending.resolve(message.result);
      }
    }, { passive:true });
    const initial = window.openai?.toolOutput;
    if (initial) render(initial);
    document.querySelector("#refresh").addEventListener("click", async (event) => {
      const button = event.currentTarget; button.disabled = true;
      try {
        const result = window.openai?.callTool ? await window.openai.callTool("get_overview", {}) : await request("tools/call",{name:"get_overview",arguments:{}});
        if (result?.structuredContent) render(result.structuredContent);
      } finally { button.disabled = false; }
    });
  </script>
</body>
</html>`;
}
