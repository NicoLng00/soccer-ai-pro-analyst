# Frontend

## Cosa è

Un'applicazione web in due parti:

- **Pagina d'ingresso** nello stile di `riferimento-design.md`: hero con video a tutto schermo, navbar a pillola smerigliata, titolo e due pulsanti. Uno dei due porta all'area riservata.
- **Area amministrativa** (`/app`) per **due utenti amministratori**. Nessuna registrazione: gli utenti si creano da terminale (`docs/security.md`, "Utenze amministrative").

L'area amministrativa è quasi solo lettura. L'unica scrittura sui dati è la decisione sulle proposte di variabili del `matchday-reviewer`. Nessun pulsante modifica una previsione, una quota o un'osservazione.

## Stack

Dal riferimento, invariato: Vite, React 19, TypeScript, Tailwind CSS v4 con `@tailwindcss/vite`, framer-motion per le animazioni, tipografia inline con la prop `style`.

Si aggiunge, con decisione registrata nella fase 6:

- routing e lettura dei dati dall'API: poche dipendenze, scelte nel piano della fase 6;
- grafici coerenti con il resto dell'interfaccia (stessa palette, stessi caratteri);
- test: Vitest con Testing Library per i componenti, Playwright per i percorsi completi.

Il codice sta in `frontend/` nello stesso repository. `package-lock.json` è committato; `npm ci` in CI.

## Adattamenti al riferimento

Questi punti prevalgono su `riferimento-design.md`.

| Nel riferimento | Da noi | Perché |
|---|---|---|
| Nome "Monsoon", testi su business continuity, link Product/Solutions/Pricing/... | Nome SoccerAnalystPro; testi sul sistema (bozza sotto); link alle sezioni della pagina | Altro prodotto |
| Video `hero.mp4` scaricato dall'URL del template | Video e immagini di contesto calcistico forniti da Nico. Il file del template non si scarica | Appartiene a un altro progetto |
| Striscia "Trusted by teams at" con nomi di aziende inventati | Da togliere, oppure da sostituire con fatti veri in solo testo: campionati coperti, partite analizzate, stagioni di storico | Su un prodotto in vendita, clienti inventati sono una referenza falsa |
| Google Fonts caricato con `<link>` | Inter servito dal nostro dominio (stesso carattere, stessa resa) | Nessuna richiesta a terzi: CSP più stretta e nessun indirizzo IP dei visitatori inviato a Google senza consenso (sentenza del Tribunale di Monaco, gennaio 2022) |
| Pulsanti "Get Started" e "See Plans" | "Accedi" (verso `/app`) e "Come funziona" (sezione metodo) | Due admin, nessun piano a pagamento per ora |
| Testi in inglese | Italiano come lingua predefinita, tutti i testi in un unico file per aggiungere l'inglese in seguito | Mercato iniziale italiano |

Restano come nel riferimento: navbar a pillola chiara, eyebrow smerigliato, titolo Inter antracite (`#1f1f1f`), pulsante pieno scuro e pulsante chiaro con bordo, animazioni di ingresso e di hover/tap, sovrapposizioni sul video.

### Video e immagini

- **Leggibilità.** Il design usa testo scuro su video chiaro in alto e testo chiaro in basso. Se il video scelto è scuro in alto, si invertono i colori come dice la nota del riferimento, e solo dopo averlo verificato.
- **Peso.** Massimo 25 MiB per file (limite di Cloudflare Workers per i file statici); obiettivo 3–8 MB: 1080p, H.264 in MP4 più una versione WebM, durata 10–20 secondi in loop, senza audio. Un'immagine `poster` mostrata mentre il video carica.
- **Accessibilità.** Con `prefers-reduced-motion` si mostra il poster al posto del video.
- **Diritti.** Niente loghi di club o di leghe, niente giocatori riconoscibili, niente maglie ufficiali. Ogni file ha la licenza d'uso commerciale annotata in `frontend/public/media/LICENSES.md` (fonte, autore, licenza, data).

### Bozza dei testi della pagina d'ingresso

Da confermare con Nico.

- Eyebrow: "Analisi pre-partita, calibrata"
- Titolo: "Il calcio, in probabilità"
- Sottotitolo: "Probabilità per 1X2, Goal/NoGoal e Over/Under 2.5, quota equa e confronto con il mercato. Ogni previsione è salvata prima del fischio e misurata dopo."
- Pulsanti: "Accedi", "Come funziona"

## Area amministrativa

Stesso linguaggio visivo della pagina d'ingresso (Inter, antracite, pillole smerigliate) su fondo chiaro neutro al posto del video.

| Pagina | Contenuto | Endpoint |
|---|---|---|
| Accesso | Utente e password, poi codice TOTP | `POST /api/auth/login`, `POST /api/auth/mfa` |
| Partite | Prossime partite: probabilità dei tre mercati, quota equa, quota di mercato, edge, orario della previsione | `GET /api/matches` |
| Partita | Dettaglio: previsioni a T-24h e T-1h, variabili principali, versione del modello, esito e contributo all'errore a partita finita | `GET /api/matches/{id}` |
| Valutazione | Calibrazione, log-loss, Brier, RPS, CLV nel tempo | `GET /api/evaluation/summary` |
| Qualità dei dati | Controlli recenti, slot saltati, coda di revisione delle entità | `GET /api/quality/checks` |
| Job | Esecuzioni, durate, errori | `GET /api/jobs/runs` |
| Variabili | Registro con stato, versione e report di valutazione | `GET /api/variables`, `GET /api/variables/{code}` |
| Proposte | Proposte del `matchday-reviewer` con evidenze; decisione "da valutare" (`accepted`) o "scartata" (`rejected`). Da valutare non vuol dire attiva: decide la valutazione | `GET /api/proposals`, `POST /api/proposals/{id}/decision` |
| Giornate | Report del `matchday-reviewer` | `GET /api/matchdays/{id}/review` |

Il testo che arriva da fonti esterne (nomi, titoli RSS, report degli agenti) si mostra sempre come testo: mai `dangerouslySetInnerHTML`, mai Markdown convertito in HTML senza sanitizzazione.

## Hosting

| Pezzo | Dove | Note |
|---|---|---|
| Pagina d'ingresso e area `/app` | Cloudflare Workers con static assets | Le richieste ai file statici sono gratuite e illimitate; limite di 25 MiB per file |
| API | FastAPI sulla VM Oracle | Raggiungibile solo tramite Cloudflare Tunnel: nessuna porta aperta in ingresso |
| Filtro d'accesso | Cloudflare Access davanti a `/app` e all'API | Solo le email dei due admin. Piano gratuito fino a 50 utenti; i log di Access restano 24 ore, quindi l'audit vero è in `app.audit_log` |

Tunnel e Access con nomi stabili richiedono un dominio gestito su Cloudflare: è il probabile unico costo del progetto (un `.com` costa circa 10 € l'anno). Alternativa senza dominio: rete privata raggiungibile solo con il client WARP sui dispositivi dei due admin.
