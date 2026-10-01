# Fase 7 — Pentest e messa online

## Prima di iniziare

Leggi `docs/security.md`, ADR 0008, la sezione Fase 7 di `docs/roadmap.md` e l'ultimo report del `security-reviewer`. Proponi il piano in plan mode. Il pentest lo conduce Nico: il tuo ruolo è preparare, assistere, correggere e ritestare.

## Obiettivo

Mettere online l'area amministrativa solo dopo un pentest senza vulnerabilità critiche o alte aperte, su una VM irrobustita e sorvegliata.

## Blocchi di lavoro

1. **Preparazione.** Perimetro scritto (host, URL, versioni), utenze di staging dedicate, finestra temporale, elenco degli strumenti. La skill `/pentest` guida la campagna.
2. **Ricognizione e test.** Secondo `docs/security.md`: WSTG per la parte web, API Security Top 10 per gli endpoint, ASVS 5.0 livello 2 come elenco di verifica. Ogni strumento offensivo si esegue con conferma esplicita e solo contro lo staging.
3. **Report.** Risultati con severità CVSS 4.0, evidenza, correzione proposta. Il report si salva fuori dal repository (`reports/security/` è ignorata da git).
4. **Correzioni.** Una correzione per branch, con un test che riproduce il problema prima della correzione. Revisione del `security-reviewer` su ogni correzione.
5. **Ritest.** Ogni risultato chiuso ha l'esito del ritest nel report.
6. **Hardening della VM.** SSH solo con chiave e senza root, nessuna porta in ingresso, aggiornamenti automatici, socket di Docker non esposto, utenti dei container non root dove possibile. Verifica con una scansione delle porte dall'esterno.
7. **Messa online.** Tunnel e Access in produzione, backup verificato con un ripristino, avvisi su accessi falliti ripetuti, errori 5xx e slot saltati.

## Vincoli

- Mai test contro sistemi di terzi, Cloudflare compreso oltre alla nostra configurazione.
- Nessun dato reale delle utenze di produzione nello staging.
- Nessuna messa online con vulnerabilità critiche o alte aperte.

## Fatto quando

Criteri della Fase 7 in `docs/roadmap.md` spuntati. Aggiorna `Fase corrente` solo dopo l'approvazione di Nico.
