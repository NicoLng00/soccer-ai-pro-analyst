# Fase 6 — API e area amministrativa

## Prima di iniziare

Leggi, in quest'ordine: `CLAUDE.md`, ADR 0008, `docs/security.md`, `docs/frontend/README.md`, `docs/frontend/riferimento-design.md`, la sezione `app` e i ruoli di `docs/data-model.md`, la sezione Fase 6 di `docs/roadmap.md`. Poi entra in plan mode e proponi un piano a blocchi. Nel piano indica le dipendenze nuove (Python e npm) con il motivo di ciascuna: poche e mantenute.

## Obiettivo

Due amministratori entrano nello staging con le proprie credenziali e TOTP, vedono previsioni, valutazione, qualità dei dati e job, e decidono sulle proposte di variabili. Ogni endpoint è coperto dai test di sicurezza continui.

## Blocchi di lavoro

1. **Schema `app` e ruoli.** Migrazione con `app.admin_user`, `app.session`, `app.login_attempt`, `app.audit_log` (sola aggiunta, trigger che blocca `UPDATE` e `DELETE`), ruoli `sap_api` e `sap_useradmin` con i grant di `docs/data-model.md`. Revisione dello `schema-guardian`.
2. **Comandi `sap admin`.** `create`, `set-password`, `reset-mfa`, `disable`, `list`, con il ruolo `sap_useradmin`. Password con `getpass`, mai come argomento; controllo contro un elenco di password compromesse incluso nel pacchetto; QR del TOTP nel terminale.
3. **Nucleo dell'API.** `src/soccer_analyst/api/`: applicazione FastAPI, configurazione, header di sicurezza, CORS, gestione degli errori senza dettagli interni, verifica del token di Cloudflare Access (disattivabile solo con `SAP_ENV=dev`), dipendenza `require_admin`, limite di tentativi.
4. **Autenticazione.** `login`, `mfa`, `logout`, `me` secondo `docs/security.md`. Test: risposte indistinguibili, blocco progressivo, scadenze, revoca, flag dei cookie.
5. **Endpoint di lettura.** Quelli della tabella di `docs/frontend/README.md`, uno alla volta con la skill `nuovo-endpoint`. Paginazione e limiti su ogni parametro. Le letture rispettano il point-in-time dove ha senso (una previsione mostra le variabili note al suo istante).
6. **Test trasversali.** Test che enumera tutte le route e verifica la lista pubblica; Schemathesis sullo schema OpenAPI con una sessione di test; test degli header.
7. **Frontend.** `frontend/` dal riferimento con gli adattamenti. Pagina d'ingresso, accesso con TOTP, pagine dell'area `/app`. Inter servito localmente. Vitest e Playwright.
8. **CI.** Job per il frontend (`npm ci`, lint, `tsc`, build, Vitest, Playwright), Semgrep, CodeQL, gitleaks, pip-audit, `npm audit` o osv-scanner, ZAP baseline e API scan su stack effimero (notturno e sulle PR verso `main`).
9. **Staging.** Worker con static assets per il frontend; API sulla VM dietro Tunnel; applicazioni Access per `/app` e per l'API con le sole email dei due admin. Procedura scritta in `docs/runbook/staging.md`.

## Vincoli

- L'API non scrive mai in `ref`, `obs`, `mkt` e nelle previsioni di `ml`. Non avvia job e non ricalcola previsioni.
- Ogni endpoint nuovo passa dalla skill `nuovo-endpoint`. Un endpoint senza test di autorizzazione non si committa.
- Credenziali reali mai nel codice, nei test, nei log o in chat: i test usano utenti generati al volo.
- Il testo esterno (nomi, titoli, report degli agenti) si mostra solo come testo.
- Video e immagini: solo file con licenza annotata in `frontend/public/media/LICENSES.md`. Finché Nico non li fornisce, un segnaposto neutro (gradiente) al posto del video.

## Revisioni obbligatorie

- `schema-guardian` dopo il blocco 1.
- `security-reviewer` dopo i blocchi 2, 3, 4, dopo ogni gruppo di endpoint del blocco 5 e prima del deploy in staging.
- `leakage-auditor` sugli endpoint che mostrano variabili di una previsione.

## Fatto quando

Criteri della Fase 6 in `docs/roadmap.md` spuntati, ciascuno con il comando o il link all'esecuzione della CI che lo verifica.
