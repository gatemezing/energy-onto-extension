# Ontology engineering review and update plan

Scope: `era-energy-settlement-draft.ttl` (vocabulary), `era-energy-settlement-shapes.ttl`, the example graph and the competency-question suite, reviewed against ERA ontology v4.0.0-rc.3. Target: a **proposal to ERA governance**, published under `http://data.europa.eu/dy6/`.

The legal and telematics review (`LEGAL-AND-TELEMATICS-REVIEW.md`) and open requirements G1–G6 (`era-energy-settlement-cqs.md` §4) remain valid; this document covers modelling quality, reuse and publication.

## 1. Assessment summary

**Strengths**

- A clear requirements basis: 48 executable competency questions, plus SHACL tests, arithmetic checks and negative fixtures, run against a vendored ERA release (LOT-style ORSD → implementation → evaluation).
- Good reuse: SOSA/SSN for measurement, SAREF meter, PROV for evidence and exchange, OWL-Time, GeoSPARQL, QUDT units through the ERA `era:unitOfMeasure` convention, and RINF/telematics anchors (`era:Vehicle`, `era:RunningTrack`, `era:ReferenceBorderPoint`, `era:TrainCompositionMessage`).
- Clean separation between the data model, its validation (SHACL) and legal evidence; the model never claims compliance.
- No modification of `era:` terms, only extension.

**Weaknesses found**

| # | Finding | Severity | Status |
|---|---|---|---|
| R1 | `example.org` namespace; prefix `ex:` signals example terms | High (blocks proposal) | **Fixed in v0.6** |
| R2 | `era:shaclShapeValidationRule` pointed to four `exsh:` shapes that did not exist; shapes were declared in the vocabulary namespace | High | **Fixed in v0.6**: shapes in `enssh:`, links resolve |
| R3 | 70+ terms without `rdfs:label`, ~35 without any definition; no `rdfs:isDefinedBy` or term status | Medium | **Fixed in v0.6** |
| R4 | No ontology metadata (title, description, versionIRI, preferred prefix) | Medium | **Fixed in v0.6** (licence still open, see P4) |
| R5 | `ens:TrainRun` typed as `prov:Entity`, although a run is a movement in time | Medium | **Fixed in v0.6**: `prov:Activity` |
| R6 | Run identity not aligned with TAF/TAP: rc.3 has `era:TrainIdent` (unique contracted train ID) and `era:operationalTrainNumber` | Medium | **Partly fixed in v0.6**: `ens:trainRunIdent`, `skos:closeMatch`; test data still missing |
| R7 | `ens:allocatesReading` duplicates the component path without a stated relation | Medium | **Fixed in v0.6**: OWL 2 property chain |
| R8 | `ens:forwardsTo` / `ens:exchangeProtocol` without domain/range; no check of admissible flow | Low | **Fixed in v0.6** + `enssh:ForwardsToShape` |
| R9 | Header comments contradicted the model (TrainRun "removed") and the CQ count | Low | **Fixed in v0.6** |
| R10 | Inconsistent party pattern: some properties target `era:Body` (`exchangeSender`, `responsibleRUOrganisation`), others `era:OrganisationRole` (`operatedBy`, `allocatedTo`) | High | Open → P1 |
| R11 | Implicit PROV agents: `compiledBy`/`producedBy` ⊑ `prov:wasAttributedTo` (range `prov:Agent`) make EMS and settlement systems agents by inference only; ground systems have no superclass | Medium | Open → P1 |
| R12 | `ens:railwayCompanyCode` duplicates `era:organisationCode` (ERA-allocated code on `era:Body`) | Medium | Open → P1 |
| R13 | `ens:EnergyReading` is both `sosa:Observation` and `geo:Feature` and carries several results as datatype properties (CEBD record shape) | Medium | Open → P2 |
| R14 | Concept schemes are defined only in the example data; `AllocationStatuses` mixes status and method (`estimated`, `fallback-to-keeper`) | Medium | Open → P2 |
| R15 | Corrections expressed as `ens:allocationVersion` string; no supersession or reversal | Medium | Open → P2 |
| R16 | Time modelled two ways: `time:Interval` for readings, `xsd:dateTime` pair for runs; timezone not enforced | Low | Open → P2 |
| R17 | `ens:exchangeContains` (settlement system → activity) is the undeclared inverse of `ens:exchangeRecipient`; name does not say "received" | Low | Open → P2 |

## 2. Changes made on this branch (v0.6)

1. Namespace `http://data.europa.eu/dy6/`; prefixes `ens:` (vocabulary), `ensc:` (concepts), `enssh:` (shapes). Synthetic instances stay in `http://example.org/data/`.
2. Ontology header: `dct:title`, `dct:description`, `owl:versionIRI <http://data.europa.eu/dy6/0.6.0>`, `owl:versionInfo "0.6.0"`, `dct:modified`, `vann:preferredNamespacePrefix/Uri`, `vs:term_status` (ERA convention).
3. Every `ens:` term: `rdfs:label`, `rdfs:isDefinedBy`, `vs:term_status "unstable"`, and a `skos:definition` or comment.
4. `ens:TrainRun ⊑ prov:Activity`; new `ens:trainRunIdent → era:TrainIdent`; `ens:operationalTrainNumber skos:closeMatch era:operationalTrainNumber`; `runStart`/`runEnd` documented as an attribution window, not actual departure.
5. `ens:allocatesReading owl:propertyChainAxiom (ens:hasAllocationComponent ens:componentReading)`.
6. Domains/ranges for `ens:forwardsTo` and `ens:exchangeProtocol`.
7. Shapes moved to `enssh:`; new `enssh:EnergyMeasurementSystemShape` and `enssh:ForwardsToShape`; dangling validation-rule links fixed. Two new negative tests (DCS → settlement system; EMS without vehicle).

Result: 48/48 CQs, SHACL conforms, accounting and all negative tests pass.

## 3. Roadmap

### P1 – v0.7: agents, roles and identity (needs a decision, see §4)

- Apply one party pattern (recommended: **roles for responsibilities in context, bodies for identity**, linked by `era:roleOf`): `exchangeSender`/`exchangeRecipient` → roles or agents; `responsibleRUOrganisation` kept as the resolution of a code to a body.
- Declare ground systems and EMS as `prov:SoftwareAgent` (or `sosa:System` + `prov:Agent`) so the PROV attribution is explicit; give `ens:operatedBy` a domain.
- Deprecate `ens:railwayCompanyCode` (`owl:deprecated true`, `dct:isReplacedBy era:organisationCode`) and resolve `era:responsibleRU` through the ERA Organisation Code Register.
- Add test data and CQs with `era:TrainIdent` (TAF/TAP core elements) and a reused operational train number across two runs.

### P2 – v0.8: measurement, vocabularies and lifecycle

- Readings: keep the compact CEBD properties, and define their SOSA expansion (observable-property concepts for consumed/regenerated/reactive energy, `sosa:hasResult` with QUDT quantity values) as documented rules (SHACL rules or SPARQL CONSTRUCT). Decide whether the GPS position stays on the reading (`geo:Feature`) or moves to a sample/location node.
- Move all concept schemes into `era-energy-settlement-concepts.ttl` under `ensc:` with definitions and `skos:notation`; split allocation **status** (valid, rejected, superseded) from **method** (metered, estimated, fallback-to-keeper).
- Corrections: `prov:wasRevisionOf` / `ens:supersedes` between allocations, reversal components, and a CQ "current allocation for a run and zone".
- Harmonise time: run interval as `time:Interval` or `prov:startedAtTime/endedAtTime` for actual times; require `xsd:dateTimeStamp` where timezone matters.
- Rename `ens:exchangeContains` → `ens:receivedExchange`, `owl:inverseOf ens:exchangeRecipient`.

### P3 – v0.9: scope extensions (open requirements)

- G4 network losses: `ens:LossAllocationMethod` concept + coefficient on allocation, with arithmetic tests.
- G3 market/contract: separate module (`dy6` sub-module), not merged into the core, once legal interface duties are verified.
- Richer test data: multi-day runs, mixed time zones, multiple consumers, estimated and split components.
- EVN check-digit validation once the rule is confirmed against the authoritative register.

### P4 – publication and ERA governance (in parallel)

- Confirm with the Publications Office / ERA that `dy6` is the allocated identifier and set up dereferencing and content negotiation for terms, `0.6.0` version IRIs and shapes.
- Licence statement (ERA uses Commission Decision 2017/863 for its ontology) and contributors in the header.
- Quality gates in CI: `cq_suite.py`, OWL 2 DL profile check (ROBOT `validate-profile`), OOPS! pitfall scan, HTML documentation (pyLODE or Widoco).
- Upstream change requests to the ERA ontology: object link from `era:LocoIdent`/`era:locoNumber` to `era:Vehicle`; unit of `era:trainWeight` (G5); clarify whether the run key should be `era:TrainIdent`.

## 4. Decisions needed

1. Party pattern: roles vs bodies for sender, recipient and operator (R10).
2. Whether the SOSA expansion of readings is normative or an optional view (R13).
3. Confirmation of `dy6` allocation and the licence to publish under.
