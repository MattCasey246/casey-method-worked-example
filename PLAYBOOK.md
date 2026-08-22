# The Casey Method
## A Safety-Gated Governance Framework for AI Adoption in Social and Assisted Housing and Other Essential Services

**Version 1.1.0 — 22 August 2026**
**Author: Matt Casey, Director, Casey IT Limited** *(ORCID: to be added at deposit)*
**Status: Versioned methodology publication. The method is published for adoption and independent implementation (§7). Casey IT Limited applies it commercially; in any Casey IT engagement the signed Statement of Work governs and prevails over this document. Consolidates instruments developed and applied 30 May – 25 July 2026 (source register and provenance note in §10).**
**Canonical version: this document is deposited at Zenodo under a concept DOI *(to be minted at deposit)*; cite the concept DOI, which always resolves to the latest version.**

### Abstract

Small and medium-sized organisations operating essential services — social housing, property management, and care — face a distinctive AI adoption problem: their data carries statutory duty (habitability and hazard-response obligations such as the UK's Awaab's Law and the Housing Health and Safety Rating System, or NSPIRE inspection standards in US federally assisted housing), their estates include an operational technology layer that office-centric AI programmes ignore, and their internal IT capacity is too thin to independently assure vendor claims. This playbook codifies the Casey Method, a six-stage operational method that sequences governance and safety assurance ahead of AI enablement. Its central commitment is an ordering constraint: a safety metric derived from the organisation's statutory duty — worst-failure recall — is ranked above headline accuracy and enforced as a contractual precondition of enablement. A reference implementation on a synthetic social-housing estate illustrates that this ordering can reverse the decision an accuracy-led process reaches: a prompt variant with the higher headline accuracy was rejected for missing seeded serious hazards, while the selected variant caught all of them, at a quantified cost and latency premium (methodological limitations, including a disclosed exemplar–test overlap, are stated inline in §3). The method further specifies bounded, least-capability integration patterns and assigns explicit ownership of solution cost and service-level accountability — two pillars the licence-reseller channel structurally leaves unowned. The evaluation harness, reference implementation, and architecture decision records are published alongside this document.

**Keywords:** AI governance · safety-critical AI · LLM evaluation · social housing · affordable housing · Awaab's Law · NSPIRE · hazard recall · AI readiness assessment · responsible AI adoption · SMB · operational technology

**How to cite:** Casey, M. (2026). *The Casey Method: A Safety-Gated Governance Framework for AI Adoption in Social and Assisted Housing and Other Essential Services.* Version 1.1.0. Zenodo. DOI: *to be minted at deposit.*

---

## 1. What this playbook is

This document codifies the method for taking a small or medium-sized organisation that operates essential services — housing, property, care, and comparable settings where technology failure lands on residents and service users, not just on a P&L — from an unknown AI exposure position to governed, safety-gated, ROI-accountable AI adoption on its real operational estate.

It exists so that the process is inspectable, repeatable, and independent of any one engagement. Each stage names its purpose, inputs, instruments, exit gate, and failure handling. The instruments referenced in §8 are real artefacts, not aspirations: a tenant scan script, a scored report template, a working evaluation harness with reproducible results in the accompanying repository, integration reference patterns, and an operational dashboard. The evaluation harness, reference implementation, and architecture decision records are published; the remaining instruments are specified here and held in the private delivery kit (§8 states which is which).

## 2. The problem class

Essential-service SMBs share a technology profile that generic AI enablement does not fit:

- **An operational technology layer.** Building management systems, environmental sensors, door entry, CCTV, repairs and maintenance queues. AI initiatives that only consider the office estate (documents, email, chat) miss the layer where the organisation's statutory duties actually live.
- **Statutory duty attached to data.** In UK social housing, Awaab's Law and the Housing Health and Safety Rating System make damp, mould, and habitability data legally load-bearing; comparable inspection and habitability regimes exist in other jurisdictions, including NSPIRE in US federally assisted housing (§2.1). A missed hazard is not a bad customer experience. It is a regulatory and human failure.
- **Thin internal IT.** One to five technology staff, no data science function, and no internal assurance capacity to independently verify vendor claims. Enterprise-scale advisory is priced out of reach.
- **A vendor channel whose incentives concentrate on one pillar.** The reseller commercial model concentrates incentive on the productivity pillar, leaving solution cost and service-level accountability structurally unowned: no party in that model owns what an AI capability costs to run at scale, what reliability commitments it can honour, or what happens when it is wrong about a resident.

The method exists because the standard failure sequence in this class is predictable: licences bought → assistant enabled on an ungoverned estate → oversharing surfaces or a safety-relevant error occurs → adoption freezes. The method inverts the order: governance and safety gates come before enablement, and cost and reliability ownership are assigned before scale.

The method is anchored in essential services because that is where statutory duty gives the safety metric its objective derivation (§2.1). The same architecture extends to any organisation whose data carries a comparable legal duty of care — regulated care settings, water and environmental compliance, education safeguarding — by substituting the applicable duty into the Stage 3 derivation. Where no statutory duty exists, the gate can still be applied against a contractually agreed worst-failure definition, but the method's distinctive claim (§6) is made only for the duty-anchored case.

### 2.1 The statutory anchor, UK and US

The safety metric is not chosen by the consultant or the vendor; it is derived from the duty the law already imposes on the organisation. Two worked derivations:

| | Statutory duty | Data it makes load-bearing | Derived worst-failure event | Derived Stage 3 metric |
|---|---|---|---|---|
| **UK social housing** | Awaab's Law (Social Housing (Regulation) Act 2023; Phase 1 in force 27 Oct 2025 for damp and mould; Phase 2 extends to further HHSRS hazard categories from 30 Nov 2026) — fixed timescales for investigating and remedying hazards, 24-hour response for emergency hazards | Damp, mould, and habitability reports; repairs and maintenance records; environmental sensor telemetry | A resident-reported serious hazard (e.g. a damp/mould report phrased casually) triaged as non-hazardous, so the statutory clock never starts | Recall on seeded serious-hazard cases in the labelled set, ranked above headline accuracy |
| **US federally assisted housing** | NSPIRE (HUD final rule, 2023) — inspection standards classifying deficiencies as life-threatening, severe, moderate, or low, with 24-hour correction required for life-threatening and severe deficiencies | Unit and property condition records, inspection findings, resident-reported deficiencies | A resident report describing what NSPIRE would class as a life-threatening or severe deficiency triaged as routine, so the 24-hour duty is never triggered | Recall on seeded life-threatening/severe-deficiency cases, ranked above headline accuracy |

The derivation is mechanical once the duty is named: identify the statutory clock, identify the data that starts it, define the worst failure as *the clock not starting when it should*, and make recall on that failure class the gate. This is what makes the metric auditable rather than aspirational — an assessor, a regulator, or a second consultant can re-derive it from the statute and check the gate against it.

## 3. Process overview

Six stages. No stage may be skipped; each has an exit gate, and enablement (Stage 4) is unreachable without passing the governance gate (Stage 2) and the safety-evaluation gate (Stage 3).

| Stage | Name | Exit gate |
|---|---|---|
| 0 | Estate & data reconnaissance | Estate map covering office AND operational layers |
| 1 | Readiness scoring | Scored five-domain baseline, pillar-mapped |
| 2 | Governance gate | Access, sharing, labelling remediated to threshold |
| 3 | Safety-first evaluation gate | Candidate use case passes its worst-failure recall bar on a labelled set |
| 4 | Bounded enablement | Capability live under least-capability integration pattern |
| 5 | Operational observability & ROI accountability | Monitoring live; cost and SLA ownership assigned; re-score scheduled |

### Stage 0 — Estate & data reconnaissance
**Purpose:** establish what AI could touch before deciding what it should.
**Method:** automated tenant scan (identity, access, sharing posture, labelling, licensing prerequisites) plus a structured operational-data inventory: sensor and BMS telemetry, repairs history, compliance records, resident communications — where each lives, who can reach it, what statutory duty attaches to it.
**Instruments:** readiness scan script; operational data readiness module.
**Exit gate:** a written estate map spanning both layers. **Failure handling:** unscannable or unowned systems are logged as findings, not skipped.

### Stage 1 — Readiness scoring
**Purpose:** convert reconnaissance into a comparable, decision-ready baseline.
**Method:** five scored domains — data governance; identity and access; licensing and technical prerequisites; governance and policy; use cases and adoption — each mapped to the ROI pillar it gates (efficiency, transformation, productivity, solution cost, SLAs), so the executive summary reads as an investment case rather than an IT snag list. The scoring is scan-based: it scores what a scan of the live estate finds, not what a questionnaire respondent believes — the distinction from the self-assessment readiness tools now common in the sector (§6).
**Instruments:** assessment report template; scorecard with pillar column.
**Exit gate:** scored report delivered with a prioritised, pillar-tagged remediation roadmap.

### Stage 2 — Governance gate
**Purpose:** make the estate safe to point an AI at.
**Method:** remediate who-can-see-what before any capability is enabled: access rationalisation, sharing-link posture, sensitivity labelling, loss-prevention policy. The principle is the separation of **capability from assurance** — the long-standing independence principle of audit and IV&V, applied here to AI enablement in a channel where the same reseller often both sells and certifies: building models is a different discipline from independently verifying that permissions and governance survived organisational change, mergers, and estate consolidation.
**Exit gate:** governance findings above the agreed severity threshold are closed or explicitly risk-accepted by the accountable owner, in writing.
**Failure handling:** if the organisation declines remediation, the method proceeds only to advisory output, not to enablement. In a Casey IT engagement, scope is stated in the signed SOW, which prevails.

### Stage 3 — Safety-first evaluation gate
**Purpose:** evidence, on a labelled test set and before deployment, that a candidate AI use case fails in the safe direction. (Test-set performance does not warrant field performance, and statutory duties remain the organisation's throughout.)
**Method:** build a labelled case set for the use case, including known worst-failure cases derived from the applicable statutory duty per §2.1 — for UK housing triage: damp and mould serious-hazard reports; for US federally assisted housing triage: reports describing NSPIRE life-threatening or severe deficiencies. Run competing prompt/configuration variants A/B over the set. Score with an explicit metric hierarchy: **worst-failure recall first, headline accuracy second, cost and latency third.** Apply an asymmetric decision rule: a variant that over-escalates is preferred to one that ever misses a hazard, whatever their respective accuracy headlines. **The bar is explicit: 100% recall on the seeded worst-failure cases in the labelled set.** This is a floor on the test set, not a field guarantee, and on a small labelled set it is a necessary condition, not a sufficient one.
**Illustration that this gate can change decisions:** in the method's reference implementation — a 20-case synthetic labelled set built for the purpose, evaluated in a single run — the variant with the higher headline accuracy (90% vs 85%) was rejected because it missed 3 of 11 seeded serious hazards (72.7% hazard recall) while the winning variant caught 11 of 11, erring only upward, at a measured cost premium (~62% per case at uncached rates; with prompt caching applied to the shared rubric prefix, the repository's own cost study shows the effective premium falls substantially) and a latency penalty (p95 9.3s vs 3.8s) that the decision rule prices in explicitly. **Methodological disclosure:** two of the winning variant's few-shot exemplars closely mirror two test cases, and its rubric wording anticipates a third; excluding those three cases, the winning variant still catches the one seeded hazard the accuracy-led variant misses (9/9 vs 8/9 recall) while the headline accuracy difference disappears (both 88.2%). The safety-ordering conclusion survives the exclusion; the accuracy contrast does not, and is reported here only with this disclosure. A held-out evaluation set with no lexical overlap with any prompt exemplar is the specified next iteration of the harness, and the single-run design means all figures carry sampling variability that repeat runs would be required to bound.
**Instruments:** evaluation harness with scored results output and an encoded pass/fail recall bar; architecture decision records documenting each rule.
**Exit gate:** the selected variant meets its worst-failure recall bar on the labelled set, and the trade-off (cost, latency) is signed off by the accountable owner.
**Failure handling:** no variant passes → the use case is deferred, not softened. The bar does not move to meet the model.

### Stage 4 — Bounded enablement
**Purpose:** deploy the capability with the smallest surface that delivers the value.
**Method:** least-capability integration patterns — read-only tool surfaces by construction where the use case permits; typed, narrow tool definitions; entry-point selection matched to the user population; a single audited write path where writing is genuinely required. Two engagement lanes are offered downstream of the same gates: **safe acceleration** (build and enable under the method) and **independent assurance** (verify what others built), and the lane is chosen by the organisation's pillar priorities identified in Stage 1.
**Instruments:** integration reference patterns (tool-server with read-only surface, resource notifications, single-writer design); prompt assets under change control (see provenance note, §10).
**Exit gate:** capability live, surface documented, rollback path tested.

### Stage 5 — Operational observability & ROI accountability
**Purpose:** keep the deployed capability honest over time.
**Method:** event logging of every tool call and decision; drift and threshold monitoring on the operational data the capability consumes; a live dashboard for the accountable owner; named ownership of the two pillars the vendor channel leaves orphaned — **solution cost** (per-case run cost tracked against the Stage 3 baseline) and **SLAs** (latency, accuracy floor, escalation path when the model is wrong). Quarterly re-score against the Stage 1 baseline.
**Exit gate (recurring):** monitoring reviewed, costs within envelope, re-score scheduled. A breach of the safety metric is a defined trigger — owned by the organisation's accountable owner — for reverting the use case to the Stage 3 gate.

## 4. Embedded decision frameworks

Three frameworks are applied inside the stages rather than sold beside them:

1. **The four-lens sourcing decision** (from *The Sourcing Shift*, Casey, 2026): before any capability is considered for AI at all, it is screened through the whitepaper's four lenses — capability, economics, strategic value, and risk & governance — yielding an explicit sourcing outcome per function (AI-source now · hybrid · human-led AI-augmented · human-only). Stage 0/1 input.
2. **The delegation screens** (reversibility · stakes · accountability), applied per task inside a capability: can a wrong call be undone, what does it cost, who answers for it. A convergent discipline now also taught in mainstream AI-fluency practice, applied here as the test for where human-in-the-loop is mandatory. Stage 3/4 input.
3. **The ROI pillar model** (efficiency · transformation · productivity · solution cost · SLAs): every finding, remediation item, and enablement decision is tagged to the pillar it protects or unlocks, and the two structurally unowned pillars are assigned owners. Stages 1 and 5.

## 5. Commercial form and adoption economics

The method is deliberately packaged at SMB scale, and the packaging is part of the evidence that the mechanism is deliverable at this scale by any competent practitioner: it is offered as a fixed-price, fixed-scope assessment (Stages 0–2 plus roadmap) purchasable on a single purchase order without a lengthy procurement exercise, with enablement and assurance lanes as separately-scoped follow-ons. Licence independence is a structural feature of the assessment lane: the assessing party sells no licences and takes no reseller margin on the estate it scores, so no finding needs to look better than it is. In any Casey IT engagement, the signed SOW states and governs the actual scope.

## 6. Position among established frameworks, and what distinguishes the method

The method stands on established practice and says so. Readiness scoring, access governance, model evaluation, and observability all exist in enterprise use. Pre-deployment evaluation discipline exists in the major frameworks — NIST's AI Risk Management Framework (the MEASURE and MANAGE functions) and its Generative AI Profile; ISO/IEC 42001's requirement for a documented AI impact assessment before deployment; Microsoft's own deployment guidance, which sequences data-governance remediation ahead of assistant enablement. Operational-technology scoping exists in IT/OT convergence practice (CISA guidance; NIST SP 800-82). Sector-specific readiness tools now exist too: the SFHA/Altair AI Readiness Assessment (2025) offers Scottish housing associations a 16-question self-assessment with a scored PDF output. The separation of capability from assurance is the independence principle of audit and IV&V. None of these components is claimed as new here.

The method's contribution is the **binding composition, anchored where the law already is**:

1. **The gating metric is derived from the organisation's statutory duty** (Awaab's Law and HHSRS in UK social housing; NSPIRE in US federally assisted housing; §2.1 gives the derivation), not from a generic model benchmark. The frameworks above require *an* impact assessment; none of them tells an essential-service SMB *which* failure its gate must catch. The statute does, and the method operationalises that.
2. **The gate is a precondition of enablement, not a recommendation.** In the frameworks it is guidance; here it is a hard exit gate with an explicit recall bar (Stage 3), and in commercial application a contractual one.
3. **The operational technology layer is in scope from Stage 0**, not bolted on after an office-estate rollout — because that is the layer where the statutory duties live.
4. **Assurance is separated from capability** as an engagement principle — the audit/IV&V independence principle applied to a channel where the same reseller often both sells and certifies — giving mature organisations a purchasable second-opinion lane rather than an argument.
5. **Solution cost and SLAs get named owners**, the two pillars the licence-reseller incentive model structurally leaves unowned.
6. **The whole is packaged at a scope and price an essential-service SMB can adopt**, where the enterprise frameworks above assume capacity these organisations do not have; and the readiness baseline is scan-derived rather than self-reported, which distinguishes it from questionnaire-based sector tools.

The asymmetric decision rule itself — preferring over-escalation to a missed hazard — is standard safety-critical practice; it is nowhere standard in the SMB AI-enablement channel. That is the gap the method closes. The reference implementation (§3, Stage 3) illustrates, with disclosed limitations, that the ordering can reverse the decision an accuracy-led process reaches.

## 7. Adoption and independent implementation

The method is published to be used, not only read. Under this document's licence (CC BY 4.0 for the text; MIT for the reference implementation code), any practitioner, in-house team, or consultancy may implement, adapt, and commercially apply the method with attribution. The published artefact set is sufficient to do so independently of Casey IT: this playbook (the stage definitions, gates, and decision rules), the evaluation harness with its labelled-set design and metric hierarchy, the integration reference patterns as working code, the architecture decision record catalogue, and the cost/caching study. Replication of the Stage 3 evaluation — ideally on a held-out set, per the disclosure in §3 — and derivations of the safety metric for other statutory regimes (§2.1 shows the mechanical form) are explicitly invited; corrections and derivations will be credited in future versions. The instruments that remain in the private delivery kit (§8) are conveniences of delivery, not preconditions of adoption: everything normative about the method is in this document and the public repository.

## 8. The instrument set

| Instrument | Form | Public? | Status at v1.1 |
|---|---|---|---|
| Readiness scan script (`Invoke-CaseyReadinessScan.ps1`) | PowerShell, modules 1–5 | Private delivery kit | Applied to Casey IT production tenant, Jun 2026 |
| Assessment report template + scorecard | Document template | Private delivery kit; redacted sample to prospects on request | In market. ROI-pillar mapping exists as a separate authoring reference (25 Jul 2026), applied per report; not yet folded into the template itself |
| Evaluation harness | Code: labelled 20-case housing-repair set, A/B runner, metric hierarchy, results JSON | **Public repository** | Built and run Jul 2026; results and disclosure in §3 Stage 3 |
| Integration reference patterns | Tool server (read-only surface, typed tools, resource notifications), single-writer dashboard, retrieval layer with provenance | **Public repository** | Built and smoke-tested Jul 2026 |
| Cost/caching study | Runnable study with documented minimum-cacheable-prefix constraint | **Public repository** | Built Jul 2026 |
| Architecture decision records | ADR catalogue 1–15 | **Public repository** | Maintained with the reference implementation |
| Operational dashboard | Live event-log tail, estate gauges, hazard banner, activity feed | **Public repository** | Built and browser-verified Jul 2026 |

## 9. Applications to date

Honest register, as of v1.1:

- **Casey IT production tenant (June 2026):** full Stage 0–1 application to the author's own operating estate. Baseline findings across the identity, sharing, and labelling domains were documented in the scan report that became the redacted sample provided to prospects; identity-layer remediation was applied per the resulting roadmap and verified at a 21 June re-check, with the remaining items tracked on a prioritised roadmap under documented, risk-based decisions. (Specific findings and configuration decisions are held in the private engagement record, as they would be for any client.)
- **Reference implementation (July 2026):** complete Stage 0–5 build on a synthetic housing estate (sensor telemetry, repairs triage, asset documents — all data fictional), including the Stage 3 evaluation whose results and limitations are stated above and a Stage 5 dashboard with live event observability. Published in the accompanying repository.
- **Client engagements:** the assessment is in market; no client deployment is claimed at v1.1. This register will be updated per engagement.

## 10. Provenance and change log

Consolidated from instruments and documents dated 30 May – 25 July 2026: assessment offer and SOW template (2 Jun); own-tenant scan and sample report (11 Jun); two-lane engagement model and operational data readiness module (11 Jul); evaluation harness and results (13–16 Jul); integration patterns, retrieval layer, cost study, dashboard (16 Jul); ROI-pillar sales framing (25 Jul); four-lens framework (*The Sourcing Shift*, whitepaper first published March 2026; relaunched at thesourcingshift.com 6 Jun 2026; ungated 24 Jun 2026).

**Provenance note:** the reference implementation was placed under public version control on 11 August 2026; the git history therefore evidences dates from that point forward. Authorship and dating of the July 2026 work rest on the source register above, the file-level timestamps of the original artefacts, and the dated instruments themselves — not on the git log. The deposited (DOI-stamped) publication date of this document is the date of deposit, and no earlier date is claimed for the publication event itself.

| Version | Date | Change |
|---|---|---|
| 1.0 | 25 Jul 2026 | First consolidated edition (internal). |
| 1.0.1 | 25 Jul 2026 | Same-day corrections following a three-reviewer internal adversarial review: own-tenant remediation scope stated precisely; framework citation corrected to the whitepaper's actual four lenses; instrument statuses aligned to the record; cost figure recomputed from raw run output (~62%); synthetic-set caveat moved inline; contractual wording bounded to the signed SOW; §6 claim restated as the ordering constraint. |
| 1.1.0 | 22 Aug 2026 | Pre-publication edition following a structured ten-lens adversarial review. Method decoupled from the delivering firm; US statutory anchor (NSPIRE) made load-bearing with a worked derivation (§2.1); prior-art positioning added and the distinctiveness claim narrowed to the binding composition (§6); adoption and independent-implementation pathway added (§7); Stage 3 recall bar stated explicitly and the evaluation's exemplar–test overlap disclosed with contamination-excluded figures; own-tenant application summarised at engagement-record level; abstract, keywords, citation block, and licences added; Sourcing Shift publication dates reconciled; provenance note added. |

*Text © Matt Casey / Casey IT Limited 2026, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Reference implementation code licensed under the MIT License. The method was developed independently on Casey IT's own time and instruments.*
