# Anchoring the audit head outside the log's trust domain

`verify_recovery(trusted_audit_head=...)` is only meaningful if the head was stored **earlier and somewhere the
log's writer cannot rewrite**. The code provides the mechanism; whether storage is *independent* depends on how you
deploy it. This page is the checklist. Nothing here has been tested against a real second host or OS account by the
authors of this repository; the unit tests run the service on localhost in one account.

## Options (same `load()` / `advance(log)` contract)

| Option | Independent? | Use for |
|---|---|---|
| `HeadAnchor(path)` | No: same account can rewrite it | tests, demos |
| `SignedHeadAnchor(path, authority_public_key, signer=...)` | Partly: a process without the authority **private key** cannot forge a head. It can still delete the file or restore an older signed one (use `load(min_sequence=N)` with N from a separate record) | single host, key held by another account/HSM |
| `AnchorServer` + `RemoteHeadAnchor` | Yes, if deployed as below | production-style separation |

## Deploying `AnchorServer`

1. **Generate the authority key on the anchor host** and keep it there. The controller and verifier get only the
   **public** key (`trustsr.checkpoint.public_key_bytes`) and a bearer token (>= 16 random characters).
2. **Own account.** Run the service as a dedicated account that the agent/controller cannot become.
   * Linux: `useradd --system trustsr-anchor`; key and store directory `chmod 700`, owner `trustsr-anchor`; run via systemd with `User=trustsr-anchor`.
   * Windows: a dedicated local/service account; `icacls <dir> /inheritance:r /grant:r "<ACCOUNT>:(OI)(CI)F"` so only that account (and Administrators, if you accept that) can read/write; run it as a Windows service (e.g. NSSM or `sc.exe`) under that account.
3. **TLS.** The reference server speaks plain HTTP. Bind to `127.0.0.1` and put a TLS reverse proxy in front, or use a private network. Never expose the plain port.
4. **Keep the token out of the agent's reach** as far as possible (a compromised agent holding the token can still *advance* the head with a log that extends it; it cannot rewrite history).
5. **Record the last sequence number** somewhere other than the anchor (ticketing system, separate log) and pass `min_sequence` to `load()` so a restored old store is noticed.
6. **Back up** the store and key separately; losing the key means re-anchoring from scratch (a new trust root).

## What this does not solve

* A fully compromised anchor host, or anyone holding the authority private key.
* Availability: `load()` fails closed (raises `AnchorError`) if the service is down; promotion then cannot happen.
* The service checks only that a submitted log is internally consistent and **extends** the stored head. It does not judge whether the events are honest.
* No trusted timestamps, no multi-party consensus, no key rotation/revocation protocol.
