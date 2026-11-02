/* Budjettikortti Home Assistantiin (Budjetti-integraatio lataa tämän automaattisesti).
 * Näyttää kuukauden tilanteen ja budjetit, sallii tapahtumien lisäyksen, muokkauksen ja poiston
 * sekä kuitin lukemisen puhelimen kameralla (Claude budjetin kautta).
 * Kaikki tieto kulkee Home Assistantin websocketin kautta (budjetti/*-komennot). */

const MONTHS = ["tammikuu", "helmikuu", "maaliskuu", "huhtikuu", "toukokuu", "kesäkuu",
  "heinäkuu", "elokuu", "syyskuu", "lokakuu", "marraskuu", "joulukuu"];
const TOTAL = "Yhteensä";

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const mdi = (name) => `<ha-icon icon="mdi:${name}"></ha-icon>`;
const eur = (cents) => (cents < 0 ? "−" : "") + (Math.abs(cents) / 100).toFixed(2).replace(".", ",") + " €";
const toCents = (v) => Math.round(parseFloat(String(v).replace(/\s/g, "").replace(",", ".")) * 100);
const today = () => new Date().toISOString().slice(0, 10);
const monthKey = (d) => d.toISOString().slice(0, 7);
const monthLabel = (m) => { const [y, mm] = m.split("-"); const n = MONTHS[+mm - 1]; return n[0].toUpperCase() + n.slice(1) + " " + y; };
const shiftMonth = (m, by) => { const [y, mm] = m.split("-").map(Number); return monthKey(new Date(Date.UTC(y, mm - 1 + by, 1))); };
const dayLabel = (d) => { const [, m, dd] = d.split("-"); return `${+dd}.${+m}.`; };

/* Puhelimen kuva pienennetään ennen lähetystä (pitkä sivu max 1600 px, JPEG). */
async function shrinkImage(file, maxSide = 1600) {
  const bmp = await createImageBitmap(file);
  const scale = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
  const c = document.createElement("canvas");
  c.width = Math.round(bmp.width * scale); c.height = Math.round(bmp.height * scale);
  c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
  const blob = await new Promise((res) => c.toBlob(res, "image/jpeg", 0.85));
  const b64 = await new Promise((res) => { const r = new FileReader(); r.onload = () => res(String(r.result).split(",")[1]); r.readAsDataURL(blob); });
  return { b64, url: URL.createObjectURL(blob) };
}

const STYLE = `
  :host { display: block; }
  ha-card { padding: 16px; }
  .head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
  .head .m { font-size: 18px; font-weight: 500; }
  ha-icon { --mdc-icon-size: 18px; vertical-align: -3px; pointer-events: none; }
  .nav ha-icon { --mdc-icon-size: 24px; }
  .nav { background: none; border: none; color: var(--primary-text-color); font-size: 22px; cursor: pointer; padding: 0 10px; line-height: 1; }
  .sum { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 14px; }
  .sum div { background: var(--secondary-background-color); border-radius: 10px; padding: 8px 10px; }
  .sum .k { font-size: 12px; color: var(--secondary-text-color); }
  .sum .v { font-size: 16px; font-weight: 500; font-variant-numeric: tabular-nums; }
  .neg { color: var(--error-color); } .pos { color: var(--success-color, #43a047); }
  .sec { font-size: 13px; color: var(--secondary-text-color); margin: 14px 0 6px; }
  .bud { padding: 6px 0; cursor: pointer; }
  .bud .r { display: flex; justify-content: space-between; gap: 8px; font-size: 14px; }
  .bud .r .f { font-variant-numeric: tabular-nums; white-space: nowrap; }
  .track { height: 6px; border-radius: 3px; background: var(--secondary-background-color); overflow: hidden; margin-top: 4px; }
  .fill { height: 100%; border-radius: 3px; background: var(--primary-color); }
  .fill.warn { background: var(--warning-color, #ffa000); } .fill.over { background: var(--error-color); }
  .actions { display: flex; gap: 8px; margin: 14px 0 4px; }
  button.btn { display: flex; align-items: center; justify-content: center; gap: 4px; flex: 1; border: none; border-radius: 10px; padding: 11px; font: inherit; font-weight: 500; cursor: pointer;
    background: var(--primary-color); color: var(--text-primary-color, #fff); }
  button.btn.sec2 { background: var(--secondary-background-color); color: var(--primary-text-color); }
  button.btn.danger { background: none; color: var(--error-color); }
  button.btn:disabled { opacity: .6; }
  .tx { display: flex; align-items: center; gap: 10px; padding: 9px 0; border-top: 1px solid var(--divider-color); cursor: pointer; }
  .tx .tag { font-size: 11px; color: var(--secondary-text-color); border: 1px solid var(--divider-color); border-radius: 99px; padding: 1px 8px; white-space: nowrap; }
  .tx .d { flex: 1; min-width: 0; } .tx .n { font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tx .dt { font-size: 12px; color: var(--secondary-text-color); }
  .tx .a { font-variant-numeric: tabular-nums; white-space: nowrap; }
  .tx .rc { font-size: 14px; }
  .empty { color: var(--secondary-text-color); font-size: 14px; padding: 6px 0; }
  .form label { display: block; font-size: 12px; color: var(--secondary-text-color); margin: 10px 0 4px; }
  .form input, .form select { width: 100%; box-sizing: border-box; font: inherit; font-size: 16px; padding: 10px; border-radius: 8px;
    border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); }
  .seg { display: flex; gap: 4px; background: var(--secondary-background-color); border-radius: 10px; padding: 3px; }
  .seg button { flex: 1; border: none; background: none; padding: 8px; border-radius: 8px; font: inherit; cursor: pointer; color: var(--secondary-text-color); }
  .seg button.on { background: var(--card-background-color); color: var(--primary-text-color); font-weight: 500; }
  .row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .chk { display: flex; align-items: center; gap: 8px; font-size: 14px; margin-top: 10px; } .chk input { width: auto; }
  .note { font-size: 13px; color: var(--secondary-text-color); margin-top: 10px; }
  .thumb { max-width: 100%; border-radius: 8px; margin-top: 10px; border: 1px solid var(--divider-color); }
  .item { display: flex; justify-content: space-between; gap: 10px; padding: 6px 0; border-top: 1px solid var(--divider-color); font-size: 14px; }
  .item .c { font-size: 11px; color: var(--secondary-text-color); }
  .err { color: var(--error-color); font-size: 14px; margin-top: 10px; }
  .busy { color: var(--secondary-text-color); font-size: 14px; margin-top: 10px; }
`;

class BudjettiCard extends HTMLElement {
  static getStubConfig() { return { transactions: 8 }; }

  setConfig(config) {
    this._config = { transactions: 8, ...config };
    this._month = monthKey(new Date());
    this._view = "main";
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", (e) => this._onClick(e));
      this.shadowRoot.addEventListener("change", (e) => this._onChange(e));
    }
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._load();
  }

  getCardSize() { return 9; }

  connectedCallback() { this._timer = setInterval(() => { if (this._view === "main") this._load(true); }, 60000); }
  disconnectedCallback() { clearInterval(this._timer); }

  _ws(type, payload = {}) {
    const msg = { type: "budjetti/" + type, ...payload };
    if (this._config.entry_id) msg.entry_id = this._config.entry_id;
    return this._hass.callWS(msg);
  }

  async _load(quiet = false) {
    if (!quiet) { this._error = ""; this._render(); }
    try { this._data = await this._ws("month", { month: this._month }); this._error = ""; }
    catch (e) { this._error = e.message || String(e); }
    this._render();
  }

  /* ---------- tapahtumat ---------- */
  _onClick(e) {
    const el = e.target.closest("[data-a]"); if (!el) return;
    const a = el.dataset.a, d = this._data;
    if (a === "prev" || a === "next") { this._month = shiftMonth(this._month, a === "prev" ? -1 : 1); this._load(); }
    else if (a === "add") this._openForm();
    else if (a === "scan") this.shadowRoot.getElementById("file").click();
    else if (a === "tx") this._openForm(d.transactions.find((t) => String(t.id) === el.dataset.id));
    else if (a === "rcpt") { e.stopPropagation(); this._openReceipt(d.transactions.find((t) => String(t.id) === el.dataset.id)); }
    else if (a === "bud") this._openBudget(el.dataset.cat);
    else if (a === "type") {
      this._readForm();  // kirjoitetut arvot talteen ennen uudelleenpiirtoa
      const ctype = (k) => (k === "income" ? "income" : "expense");
      if (ctype(el.dataset.t) !== ctype(this._form.kind)) this._form.category = "";  // tulo- ja menokategoriat eri
      this._form.kind = el.dataset.t; this._render();
    }
    else if (a === "cancel") { this._view = "main"; this._form = null; this._render(); }
    else if (a === "save") this._save();
    else if (a === "del") this._delete();
    else if (a === "savebud") this._saveBudget();
  }

  _onChange(e) {
    if (e.target.id === "file" && e.target.files[0]) { this._scan(e.target.files[0]); e.target.value = ""; }
  }

  _openForm(tx) {
    const kind = !tx ? "expense" : tx.type === "income" ? "income" : tx.amount_cents < 0 ? "refund" : "expense";
    this._form = tx
      ? { id: tx.id, kind, amount: (Math.abs(tx.amount_cents) / 100).toFixed(2).replace(".", ","), category: tx.category, date: tx.date, note: tx.note }
      : { kind, amount: "", category: "", date: today(), note: "" };
    this._view = "form"; this._error = ""; this._render();
  }

  _readForm() {
    const r = this.shadowRoot;
    Object.assign(this._form, {
      amount: r.getElementById("amount").value, category: r.getElementById("category").value,
      date: r.getElementById("date").value || today(), note: r.getElementById("note").value.trim(),
    });
  }

  async _save() {
    this._readForm();
    const f = this._form, cents = toCents(f.amount);
    if (!isFinite(cents) || cents <= 0) { this._error = "Anna summa, esim. 12,50"; this._render(); return; }
    const payload = {
      date: f.date, amount_cents: f.kind === "refund" ? -cents : cents,
      tx_type: f.kind === "income" ? "income" : "expense", category: f.category, note: f.note,
    };
    if (f.id) payload.tx_id = f.id;
    if (f.items && f.items.length) payload.items = f.items;
    if (f.image) { payload.image = f.image.b64; payload.media_type = "image/jpeg"; }
    this._busy = "Tallennetaan…"; this._render();
    try {
      await this._ws("save", payload);
      this._view = "main"; this._form = null; this._busy = "";
      if (f.date.slice(0, 7) !== this._month) this._month = f.date.slice(0, 7);
      await this._load();
    } catch (e) { this._busy = ""; this._error = e.message || String(e); this._render(); }
  }

  async _delete() {
    if (!confirm("Poistetaanko tapahtuma?")) return;
    try { await this._ws("delete", { tx_id: this._form.id }); this._view = "main"; this._form = null; await this._load(); }
    catch (e) { this._error = e.message || String(e); this._render(); }
  }

  async _scan(file) {
    this._view = "form";
    this._form = { kind: "expense", amount: "", category: "", date: today(), note: "" };
    this._busy = "Kuvaa käsitellään…"; this._error = ""; this._render();
    try {
      const image = await shrinkImage(file);
      this._form.image = image;
      this._busy = "Claude lukee kuittia… (noin 10–20 s)"; this._render();
      const s = await this._ws("scan", { image: image.b64, media_type: "image/jpeg" });
      Object.assign(this._form, {
        amount: s.amount_cents != null ? (s.amount_cents / 100).toFixed(2).replace(".", ",") : "",
        category: s.category || "", date: s.date || today(), note: s.note || "", items: s.items || [],
      });
      this._busy = "";
      if (s.amount_cents == null) this._error = "Summaa ei tunnistettu, täytä se käsin.";
    } catch (e) { this._busy = ""; this._error = e.message || String(e); }
    this._render();
  }

  async _openReceipt(tx) {
    this._view = "receipt"; this._rc = { tx, loading: true }; this._render();
    try { Object.assign(this._rc, await this._ws("receipt", { tx_id: tx.id }), { loading: false }); }
    catch (e) { this._rc.loading = false; this._error = e.message || String(e); }
    this._render();
  }

  _openBudget(cat) {
    const b = cat && (this._data.budgets || []).find((x) => x.category === cat);
    this._bud = { category: cat || "", amount: b ? String(b.amount_cents / 100).replace(".", ",") : "" };
    this._view = "budget"; this._error = ""; this._render();
  }

  async _saveBudget() {
    const r = this.shadowRoot, v = r.getElementById("budamount").value.trim();
    if (!this._bud.category) this._bud.category = r.getElementById("budcat").value;
    const cents = v === "" ? 0 : toCents(v);
    if (!isFinite(cents) || cents < 0) { this._error = "Anna summa, esim. 250"; this._render(); return; }
    try {
      await this._ws("set_budget", { category: this._bud.category, amount_cents: cents, month: this._month, only: r.getElementById("only").checked });
      this._view = "main"; await this._load();
    } catch (e) { this._error = e.message || String(e); this._render(); }
  }

  /* ---------- näkymät ---------- */
  _render() {
    if (!this.shadowRoot || !this._config) return;
    const body = { form: () => this._formView(), receipt: () => this._receiptView(), budget: () => this._budgetView() }[this._view];
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card>${body ? body() : this._mainView()}
      ${this._busy ? `<div class="busy">${esc(this._busy)}</div>` : ""}
      ${this._error ? `<div class="err">${esc(this._error)}</div>` : ""}</ha-card>`;
  }

  _mainView() {
    const d = this._data;
    const head = `<div class="head"><button class="nav" data-a="prev" aria-label="Edellinen">${mdi("chevron-left")}</button>
      <span class="m">${monthLabel(this._month)}</span><button class="nav" data-a="next" aria-label="Seuraava">${mdi("chevron-right")}</button></div>`;
    const buttons = `<div class="actions"><button class="btn" data-a="add">${mdi("plus")} Lisää</button>
      <button class="btn sec2" data-a="scan">${mdi("camera")} Kuitti</button></div>
      <input type="file" id="file" accept="image/*" capture="environment" hidden>`;
    if (!d) return head + `<div class="empty">${this._error ? "" : "Ladataan…"}</div>` + buttons;
    const s = d.summary;
    const sum = `<div class="sum"><div><div class="k">Menot</div><div class="v">${eur(s.expense_cents)}</div></div>
      <div><div class="k">Tulot</div><div class="v">${eur(s.income_cents)}</div></div>
      <div><div class="k">Saldo</div><div class="v ${s.net_cents < 0 ? "neg" : "pos"}">${eur(s.net_cents)}</div></div></div>`;
    const rows = s.categories.filter((c) => c.budget_cents || c.spent_cents)
      .sort((a, b) => (!!b.budget_cents - !!a.budget_cents) || b.spent_cents - a.spent_cents);
    if (s.total_budget_cents) rows.unshift({ category: TOTAL, spent_cents: s.expense_cents, budget_cents: s.total_budget_cents });
    const buds = rows.map((c) => {
      if (!c.budget_cents) return `<div class="bud" data-a="bud" data-cat="${esc(c.category)}"><div class="r"><span>${esc(c.category)}</span>
        <span class="f">${eur(c.spent_cents)}</span></div></div>`;
      const pct = c.spent_cents / c.budget_cents, cls = pct > 1 ? "over" : pct >= 0.8 ? "warn" : "";
      return `<div class="bud" data-a="bud" data-cat="${esc(c.category)}"><div class="r"><span>${esc(c.category)}</span>
        <span class="f">${eur(c.spent_cents)} / ${eur(c.budget_cents)}</span></div>
        <div class="track"><div class="fill ${cls}" style="width:${Math.min(100, Math.max(0, pct * 100))}%"></div></div></div>`;
    }).join("") || `<div class="empty">Ei menoja eikä budjetteja tässä kuussa.</div>`;
    const addBud = `<div class="bud" data-a="bud" data-cat=""><div class="r"><span style="color:var(--primary-color);display:inline-flex;align-items:center;gap:4px">${mdi("plus")} Aseta budjetti</span></div></div>`;
    const txs = d.transactions.slice(0, this._config.transactions).map((t) => {
      const plus = t.type === "income" || t.amount_cents < 0;
      const rc = (t.has_receipt || t.item_count) ? `<span class="rc" data-a="rcpt" data-id="${t.id}" title="Kuitti">${mdi("receipt-text-outline")}</span>` : "";
      return `<div class="tx" data-a="tx" data-id="${t.id}"><span class="tag">${esc(t.category)}</span>
        <div class="d"><div class="n">${esc(t.note || (t.type === "income" ? "Tulo" : "Meno"))}</div><div class="dt">${dayLabel(t.date)}</div></div>
        ${rc}<span class="a ${plus ? "pos" : ""}">${plus ? "+" : "−"}${eur(Math.abs(t.amount_cents))}</span></div>`;
    }).join("") || `<div class="empty">Ei tapahtumia.</div>`;
    return head + sum + `<div class="sec">Budjetit (napauta muuttaaksesi)</div>${buds}${addBud}` + buttons +
      `<div class="sec">Tapahtumat</div>${txs}`;
  }

  _formView() {
    const f = this._form, d = this._data || { categories: [] };
    const ctype = f.kind === "income" ? "income" : "expense";
    const cats = d.categories.filter((c) => c.type === ctype).map((c) => c.name);
    if (f.category && !cats.includes(f.category)) cats.unshift(f.category);
    const seg = [["expense", "Meno"], ["income", "Tulo"], ["refund", "Hyvitys"]]
      .map(([k, l]) => `<button data-a="type" data-t="${k}" class="${f.kind === k ? "on" : ""}">${l}</button>`).join("");
    const extra = [
      f.items && f.items.length ? `${f.items.length} tuoteriviä` : "",
      f.image ? "kuitin kuva" : "",
    ].filter(Boolean).join(" ja ");
    return `<div class="form"><div class="head"><span class="m">${f.id ? "Muokkaa tapahtumaa" : "Uusi tapahtuma"}</span></div>
      <div class="seg">${seg}</div>
      <div class="row2"><div><label for="amount">Summa (€)</label><input id="amount" inputmode="decimal" value="${esc(f.amount)}"></div>
      <div><label for="date">Päivä</label><input id="date" type="date" value="${esc(f.date)}"></div></div>
      <label for="category">Kategoria</label><select id="category">${cats.map((c) => `<option ${c === f.category ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>
      <label for="note">Kuvaus</label><input id="note" value="${esc(f.note)}" placeholder="esim. Lidl">
      ${extra ? `<div class="note">Tallentuu myös: ${extra}.</div>` : ""}
      ${f.image ? `<img class="thumb" src="${f.image.url}" alt="Kuitti">` : ""}
      <div class="actions"><button class="btn" data-a="save" ${this._busy ? "disabled" : ""}>Tallenna</button>
      <button class="btn sec2" data-a="cancel">Peruuta</button></div>
      ${f.id ? `<div class="actions"><button class="btn danger" data-a="del">Poista tapahtuma</button></div>` : ""}</div>`;
  }

  _receiptView() {
    const rc = this._rc, t = rc.tx;
    const items = (rc.items || []).map((i) => `<div class="item"><div>${esc(i.name)}<div class="c">${esc(i.item_category || "luokittelematon")}</div></div>
      <span>${i.price_cents == null ? "?" : eur(i.price_cents)}</span></div>`).join("");
    return `<div class="head"><span class="m">${esc(t.note || t.category)}</span></div>
      <div class="note">${dayLabel(t.date)} · ${esc(t.category)} · ${eur(Math.abs(t.amount_cents))}</div>
      ${rc.loading ? `<div class="busy">Ladataan…</div>` : items || `<div class="empty">Ei tuoterivejä.</div>`}
      ${rc.image ? `<img class="thumb" src="data:image/jpeg;base64,${rc.image}" alt="Kuitti">` : ""}
      <div class="actions"><button class="btn sec2" data-a="cancel">Takaisin</button></div>`;
  }

  _budgetView() {
    const b = this._bud;
    const opts = [TOTAL, ...(this._data.categories || []).filter((c) => c.type === "expense").map((c) => c.name)];
    const pick = b.category ? "" : `<label for="budcat">Kategoria</label><select id="budcat">${opts.map((c) => `<option>${esc(c)}</option>`).join("")}</select>`;
    return `<div class="form"><div class="head"><span class="m">Budjetti${b.category ? ": " + esc(b.category) : ""}</span></div>${pick}
      <label for="budamount">Euroa kuukaudessa (tyhjä = ei budjettia)</label>
      <input id="budamount" inputmode="decimal" value="${esc(b.amount)}">
      <label class="chk"><input type="checkbox" id="only"> Vain ${esc(monthLabel(this._month).toLowerCase())}</label>
      <div class="note">Muuten budjetti on voimassa tästä kuukaudesta eteenpäin, kunnes muutat sitä.</div>
      <div class="actions"><button class="btn" data-a="savebud">Tallenna</button><button class="btn sec2" data-a="cancel">Peruuta</button></div></div>`;
  }
}

// Integraatio lataa tämän heti sivun alussa, ennen kuin Home Assistant ottaa käyttöön oman
// komponenttirekisterinsä. Määritellään kortti vasta, kun sovellus on latautunut, muuten
// kortti päätyisi väärään rekisteriin ("Custom element doesn't exist").
(async () => {
  for (let i = 0; i < 600 && !customElements.get("home-assistant-main"); i++) {
    await new Promise((r) => setTimeout(r, 100));
  }
  if (!customElements.get("budjetti-card")) customElements.define("budjetti-card", BudjettiCard);
})();
window.customCards = window.customCards || [];
window.customCards.push({ type: "budjetti-card", name: "Budjetti", description: "Kuukauden budjetti, tapahtumat ja kuitin luku kameralla." });
