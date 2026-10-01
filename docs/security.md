# Sicurezza

Riferimenti: OWASP ASVS 5.0 livello 2 (in particolare i capitoli su API e web service, autenticazione, sessioni, autorizzazione), OWASP API Security Top 10 (2023), OWASP Web Security Testing Guide.

## Cosa proteggiamo e da cosa

| Bene | Perché conta |
|---|---|
| Integrità dei dati | Chi altera quote, risultati o osservazioni falsa le previsioni senza che nessuno se ne accorga |
| Previsioni e modello | Sono il valore commerciale del progetto |
| Credenziali dei due admin | Danno accesso all'area riservata e alle decisioni sulle proposte |
| Database e chiavi API | Accesso diretto ai dati e ai piani gratuiti delle fonti |

Minacce principali: tentativi ripetuti di accesso e credenziali rubate altrove; un endpoint dimenticato senza autenticazione; injection; testo malevolo che arriva dalle fonti (nomi, titoli RSS) e viene mostrato nell'interfaccia; testo che cerca di manipolare gli agenti LLM; dipendenze compromesse; segreti finiti nel repository.

## Superficie esposta

Da internet si raggiungono solo la pagina d'ingresso statica e, dietro Cloudflare Access, l'area `/app` e l'API. Postgres, Dagster, SSH e SeaweedFS non sono raggiungibili da internet. La UI di Dagster, se serve da remoto, passa da Tunnel e Access come applicazione separata.

## Difesa a livelli

1. **Rete.** Cloudflare Tunnel: la VM non ha porte aperte in ingresso. Firewall della VM e security list di Oracle chiusi in ingresso. SSH solo con chiave. Postgres ascolta solo sulla rete Docker interna.
2. **Cloudflare Access.** Solo le email dei due admin, con codice monouso via email. È un filtro prima ancora che la richiesta arrivi all'applicazione.
3. **Verifica di Access nell'API.** L'API controlla l'header `Cf-Access-Jwt-Assertion` (firma, team domain, audience). Una richiesta che arriva aggirando Cloudflare viene rifiutata.
4. **Autenticazione applicativa.**
   - Password con hash argon2id; mai salvate o registrate in chiaro.
   - TOTP obbligatorio: senza secondo fattore la sessione non dà accesso a nessun endpoint.
   - Sessioni lato server con token opaco casuale (256 bit); nel database c'è solo l'hash del token.
   - Cookie `__Host-sap_session`: `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/`.
   - Scadenza per inattività 30 minuti, scadenza assoluta 12 ore, nuovo token a ogni accesso, logout che revoca la sessione.
   - Limite di tentativi per IP e per utente con blocco progressivo; stessa risposta e tempi simili per utente inesistente e password errata.
5. **Autorizzazione negata per default.** Ogni route richiede la dipendenza `require_admin`, salvo una lista pubblica esplicita (`GET /api/health`, `POST /api/auth/login`, `POST /api/auth/mfa`). Un test enumera tutte le route dell'applicazione e fallisce se ne compare una nuova fuori dalla lista e senza protezione.
6. **Database con privilegi minimi.** L'API usa il ruolo `sap_api` (`docs/data-model.md`): lettura dei dati, scrittura solo su sessioni, tentativi di accesso, audit e decisioni sulle proposte. Non può creare utenti. Gli utenti si gestiscono da terminale con il ruolo `sap_useradmin`, che il container dell'API non conosce.
7. **Ingresso e uscita.** Modelli Pydantic stretti per ogni parametro; limiti su tutto (intervallo di date al massimo una stagione, pagine al massimo 200 righe, lunghezza delle stringhe); solo SQL parametrizzato; errori senza stack trace né dettagli interni. Nel frontend il testo esterno si mostra solo come testo.
8. **Header.** Content-Security-Policy stretta (`default-src 'self'`, niente `unsafe-inline` né `unsafe-eval`, `frame-ancestors 'none'`, `base-uri 'none'`, `connect-src` limitato all'API), `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` restrittiva, `Cross-Origin-Opener-Policy: same-origin`.
9. **CORS.** Solo l'origine del frontend, con credenziali; nessun carattere jolly.
10. **Richieste che cambiano stato.** `SameSite=Strict` più controllo dell'header `Origin` su ogni `POST`.
11. **Audit.** `app.audit_log` in sola aggiunta: accessi riusciti e falliti, secondo fattore, logout, decisioni sulle proposte, gestione degli utenti. Mai password, codici TOTP, cookie o token nei log.
12. **Segreti.** Solo variabili d'ambiente. In sviluppo `.env` non si esporta nella sessione di Claude Code: `scripts/claude.sh` le passa solo `SAP_ENV` e `SAP_DB_URL_READONLY`, e i processi Python leggono `.env` da soli solo con `SAP_ENV=dev`. I segreti TOTP sono cifrati nel database con una chiave che arriva dall'ambiente (`SAP_TOTP_ENCRYPTION_KEY`), con procedura di rotazione documentata.
13. **Agenti LLM.** Il testo delle notizie è dato, mai istruzioni: gli agenti non hanno strumenti che scrivono, e il loro output passa da un modello Pydantic e dalla valutazione (ADR 0006).
14. **Catena di fornitura.** `uv.lock` e `package-lock.json` committati; Dependabot; audit delle dipendenze; scansione dei segreti.

## Utenze amministrative

- Due utenti. Nessuna registrazione, nessun recupero password via email.
- Creazione da terminale sulla VM: `sap admin create <utente>`. La password si digita due volte senza eco (mai come argomento, mai nei log), almeno 15 caratteri, controllata contro un elenco di password compromesse. Poi si registra il TOTP: QR nel terminale e conferma con un codice.
- Gestione: `sap admin set-password`, `sap admin reset-mfa`, `sap admin disable`, `sap admin list`. Ogni comando scrive in `app.audit_log`.
- Le credenziali non passano mai da chat, email, repository o issue. Per configurare il sistema servono solo i nomi utente e le email per Access.

## Test di sicurezza continui

| Controllo | Strumento | Quando | Blocca il merge |
|---|---|---|---|
| Autorizzazione di ogni endpoint: 401 senza sessione, con sessione scaduta o revocata, senza secondo fattore | pytest, test che enumera le route | Ogni PR | Sì |
| Lista degli endpoint pubblici invariata | pytest | Ogni PR | Sì |
| Fuzzing dallo schema OpenAPI: nessun errore 5xx, risposte conformi allo schema | Schemathesis | Ogni PR | Sì |
| Accesso: limite di tentativi, blocco, risposte indistinguibili | pytest | Ogni PR | Sì |
| Flag dei cookie e header di sicurezza | pytest e Playwright | Ogni PR | Sì |
| Analisi statica | ruff (regole `S`), Semgrep, CodeQL | Ogni PR | Sì, per severità alta |
| Segreti nel codice | gitleaks | pre-commit e ogni PR | Sì |
| Dipendenze vulnerabili | pip-audit, `npm audit` o osv-scanner, Dependabot | Ogni PR e ogni settimana | Sì, per alta o critica con correzione disponibile |
| Scansione dinamica | OWASP ZAP: baseline sul frontend, API scan con lo schema OpenAPI, su uno stack effimero | Ogni notte e sulle PR verso `main` | Sì, per avvisi alti |
| Percorsi completi | Playwright: accesso con TOTP, logout, scadenza, accesso negato, nessun segreto nel bundle | Ogni PR | Sì |

## Pentest

- **Quando.** Prima della messa online (cancello della fase 7), poi a ogni rilascio importante e almeno ogni tre mesi.
- **Chi.** Nico conduce il test manuale con la skill `/pentest`; il subagent `security-reviewer` rilegge codice e configurazione in modo indipendente.
- **Dove.** Ambiente di staging identico alla produzione, con utenze di staging. Mai contro sistemi di terzi. Le prove che passano da Cloudflare restano leggere; le prove intensive si fanno direttamente sullo staging.
- **Perimetro.** Pagina d'ingresso, area `/app`, API, configurazione di Access e Tunnel, VM (porte, SSH, aggiornamenti, utenti e socket di Docker), Postgres (raggiungibilità, ruoli, RLS), gestione dei segreti, UI di Dagster.
- **Metodo.** WSTG per la parte web, API Security Top 10 per gli endpoint, ASVS 5.0 livello 2 come elenco di verifica.
- **Strumenti.** ZAP o Burp Suite Community, ffuf, nuclei, sqlmap, testssl.sh, nmap. In Claude Code ogni esecuzione chiede conferma (permessi `ask`).
- **Report.** Perimetro, metodo, risultati con severità CVSS 4.0, evidenza, correzione, esito del ritest. **Il report non entra nel repository pubblico**: si conserva in privato (bucket R2 privato o archivio locale di Nico).
- **Cancello per la messa online.** Nessuna vulnerabilità critica o alta aperta; le medie hanno un piano e una data.
