# 0008 — Area amministrativa: FastAPI, React e accesso a due livelli

- Stato: Accettata nell'impostazione, dettagli da confermare nel piano della fase 6
- Data: 2026-10-01

## Contesto

Serve un'interfaccia web da cui due amministratori consultano previsioni, valutazione, qualità dei dati e job, e decidono sulle proposte di variabili. Nico ha fornito il riferimento di design della pagina d'ingresso (`docs/frontend/riferimento-design.md`). Vincoli: risorse gratuite, progetto open source da rivendere, dati che non devono essere alterabili dall'interfaccia, esposizione su internet.

## Decisione

- **API**: FastAPI in `src/soccer_analyst/api/`, nello stesso pacchetto Python, così riusa i modelli Pydantic e le query esistenti. Quasi solo lettura: le uniche scritture sono sessioni, tentativi di accesso, audit e decisioni sulle proposte.
- **Frontend**: Vite, React 19, TypeScript, Tailwind v4, framer-motion, come da riferimento, in `frontend/`.
- **Autenticazione**: due admin creati da terminale; argon2id, TOTP obbligatorio, sessioni lato server con cookie `__Host-`. Niente JWT verso il browser: una sessione nel database si revoca subito.
- **Accesso a due livelli**: Cloudflare Access (solo le due email) davanti all'area `/app` e all'API, più l'autenticazione dell'applicazione. L'API verifica anche il token di Access.
- **Hosting**: frontend su Cloudflare Workers (static assets), API sulla VM Oracle dietro Cloudflare Tunnel, senza porte aperte.
- **Database**: schema `app` e due ruoli nuovi, `sap_api` (applicazione) e `sap_useradmin` (solo comandi `sap admin` da terminale).
- **Sicurezza come requisito di fase**: test di sicurezza continui in CI e pentest prima della messa online (`docs/security.md`).

## Alternative considerate

- **Streamlit o Dash**: rapidi per una dashboard interna, ma non permettono il design richiesto e mescolano interfaccia e accesso ai dati nello stesso processo.
- **Autenticazione esterna (Auth0, Clerk, Supabase Auth)**: meno codice, ma un servizio in più con limiti gratuiti che cambiano e dati degli utenti fuori dal nostro controllo. Per due utenti non serve.
- **JWT in localStorage**: esposti a qualunque XSS e non revocabili prima della scadenza.
- **Solo Cloudflare Access, senza autenticazione applicativa**: un errore di configurazione di Access lascerebbe l'API aperta. Due livelli indipendenti costano poco.
- **Vercel per il frontend**: valido, ma Cloudflare tiene insieme hosting, Tunnel, Access e R2 in un solo account.

## Conseguenze

- Il probabile unico costo del progetto è un dominio su Cloudflare (circa 10 € l'anno), necessario per Tunnel e Access con nomi stabili. Alternativa senza dominio: rete privata con il client WARP.
- Il repository diventa poliglotta (Python e TypeScript): la CI ha un job per il frontend e la revisione di sicurezza copre entrambi.
- L'area amministrativa non può modificare previsioni, quote o osservazioni: se in futuro servirà, sarà una nuova decisione.
