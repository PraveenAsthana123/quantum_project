# Quantum Security Architecture — Shared Approach

## Layer Model (6 Layers)

| Layer | Page | Purpose |
|-------|------|---------|
| L0 | `/security/general-assessment` | AppSec, DevSecOps, CloudSec baseline — OWASP, CVE, SAST/DAST |
| L1 | `/security/opensource-tools` | Open-source tool install guide per component |
| L2 | `/security/pqc-assessment` | Crypto inventory — which algorithms are quantum-vulnerable |
| L3 | `/security/pqc-implementation` | Install liboqs, implement Kyber/Dilithium/Falcon/SPHINCS+ |
| L4 | `/security/ai-security-assessment` | AI/ML attack vectors — OWASP ML Top 10 |
| L5 | `/security/ai-security-tools` | AI-powered security per component (API, code, token, cert, model) |

## NIST PQC Standards (2024)
- FIPS 203 — ML-KEM (Kyber): key encapsulation
- FIPS 204 — ML-DSA (Dilithium): digital signatures  
- FIPS 205 — SLH-DSA (SPHINCS+): hash-based signatures
- FIPS 206 — FN-DSA (Falcon): lattice signatures

## Open Source Tools by Category

### AppSec
- Semgrep (SAST) — `pip install semgrep`
- OWASP ZAP (DAST) — `docker pull ghcr.io/zaproxy/zaproxy:stable`
- Bandit (Python SAST) — `pip install bandit`
- Trivy (container scan) — `curl -sfL .../install.sh | sh`
- Gitleaks (secret scan) — binary from GitHub releases
- OWASP Dependency-Check — Java-based

### DevSecOps
- SonarQube Community — Docker `sonarqube:community`
- Falco (runtime security) — Helm chart
- OPA Gatekeeper — Kubernetes admission
- Checkov (IaC scan) — `pip install checkov`
- Cosign (container signing) — binary

### CloudSec
- Prowler — `pip install prowler`
- ScoutSuite — `pip install scoutsuite`
- Steampipe — binary + plugins
- CloudSploit — Node.js CLI

### NetworkSec
- Nmap — `apt install nmap`
- Wireshark — `apt install wireshark`
- Suricata — `apt install suricata`
- Zeek — `apt install zeek`

### CryptoSec (PQC)
- liboqs — build from source (cmake)
- pyoqs — `pip install pyoqs`
- oqs-provider (OpenSSL) — build from source
- Hashicorp Vault — binary
- Certbot — `apt install certbot`

## AI Security Tools per Component

| Component | Tool | AI Layer |
|-----------|------|----------|
| API | OWASP ZAP + Ollama triage | LLM summarizes findings |
| Code | Semgrep + AI code review | LLM explains vuln patterns |
| Token | JWT decode + rule engine | Flags weak algos |
| Certificate | certlint + AI | Flags expiry/algo issues |
| Data Pipeline | Great Expectations + AI | Detects drift/poisoning |
| ML Model | ModelScan + AI | Checks weight integrity |
| Quantum Circuit | Custom + AI | Noise/gate fidelity |
| Infrastructure | Trivy + Falco | CVEs + runtime anomalies |

## Shared Security Principle
All findings are evidence-based. No assertion without grep/tool output.
AI tools are advisory — human review required for CRITICAL findings.
PQC migration is hybrid first (classical + PQC) — never pure PQC until interop verified.
