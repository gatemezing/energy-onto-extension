# Ontology engineering review and update plan

Scope: `era-energy-settlement-draft.ttl` (vocabulary), `era-energy-settlement-shapes.ttl`, the example graph and the competency-question suite, reviewed against ERA ontology v4.0.0-rc.3. Target: a **proposal to ERA governance**, published under `http://data.europa.eu/dy6/def/energy/`.

The legal and telematics review (`LEGAL-AND-TELEMATICS-REVIEW.md`) and open requirements G1–G6 (`era-energy-settlement-cqs.md` §4) remain valid; this document covers modelling quality, reuse and publication.

## 1. Assessment summary

**Strengths**

- A clear requirements basis: 49 executable competency questions, plus SHACL tests, arithmetic checks and negative fixtures, run against a vendored ERA release (LOT-style ORSD → implementation → evaluation).
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
| R5 | `ens:TrainRun` typed as `prov:Entity` and disconnected from the telematics train concepts | Medium | **Fixed in v0.6**: renamed `ens:RunningTrain` (cf. `era:RunningTrack`), `⊑ era:Train` |
| R6 | Run identity not aligned with TAF/TAP: rc.3 has `era:TrainIdent` (unique contracted train ID) and `era:operationalTrainNumber` | Medium | **Partly fixed in v0.6**: `era:operationalTrainNumber` reused directly, `ens:runningTrainIdent → era:TrainIdent`; test data still missing |
| R7 | `ens:allocatesReading` duplicates the component path without a stated relation | Medium | **Fixed in v0.6**: OWL 2 property chain |
| R8 | `ens:forwardsTo` / `ens:exchangeProtocol` without domain/range; no check of admissible flow | Low | **Fixed in v0.6** + `enssh:ForwardsToShape` |
| R9 | Header comments contradicted the model (TrainRun "removed") and the CQ count | Low | **Fixed in v0.6** |
| R10 | Inconsistent party pattern: some properties target `era:Body` (`exchangeSender`, `responsibleRUOrganisation`), others `era:OrganisationRole` (`operatedBy`, `allocatedTo`) | High | Open → P1 |
| R11 | Implicit PROV agents: `compiledBy`/`producedBy` ⊑ `prov:wasAttributedTo` (range `prov:Agent`) make EMS and settlement systems agents by inference only; ground systems have no superclass | Medium | Open → P1 |
| R12 | `ens:railwayCompanyCode` duplicates `era:organisationCode` (ERA-allocated code on `era:Body`) | Medium | **Fixed in v0.6**: deprecated, `dct:isReplacedBy era:organisationCode` |
| R20 | `era:trainOperatingRU` is a datatype property (company code string), but the operating RU should be the organisation role of a body acting as railway undertaking | Medium | **Fixed locally in v0.6**: `ens:operatingRailwayUndertaking → era:OrganisationRole` typed with ERA `organisation-roles/RU` (or `RU-1`…`RU-7`); the code stays in `era:trainOperatingRU` and must equal the body's `era:organisationCode`. Upstream request in P4 |
| R13 | `ens:EnergyReading` is both `sosa:Observation` and `geo:Feature` and carries several results as datatype properties (CEBD record shape) | Medium | **Fixed in v0.7**: reading = `sosa:ObservationCollection` (SSN-Ext) of `sosa:Observation`s with `qudt:QuantityValue` results; GPS fix stays as `geo:hasGeometry` on the reading |
| R14 | Concept schemes are defined only in the example data; `AllocationStatuses` mixes status and method (`estimated`, `fallback-to-keeper`) | Medium | Open → P2 |
| R15 | Corrections expressed as `ens:allocationVersion` string; no supersession or reversal | Medium | Open → P2 |
| R16 | Time modelled two ways: `time:Interval` for readings, `xsd:dateTime` pair for runs; timezone not enforced | Low | Open → P2 |
| R18 | `skos:closeMatch` between OWL classes/properties (`ens:EnergyReading`–`saref:Measurement`): with the SKOS schema, an RDFS or OWL RL reasoner types both as `skos:Concept` (domain/range of `skos:semanticRelation`), and declaring it an annotation property clashes with SKOS's object-property declaration in OWL 2 DL | Medium | **Fixed in v0.6**: `rdfs:seeAlso`; no SKOS mapping properties on ontology terms (verified with owlrl) |
| R19 | `era:Train` is a TAF/TAP message element (its other subclasses are `era:TrainStopType` and `era:WagonStatusMessage`) and carries ERA shape links; if ERA shapes target `era:Train`, running trains will be validated against them | Low | Open → P1: run the ERA shapes on the examples |
| R21 | With the full SSN axioms (`sosa:Sensor ⊑ ∀ sosa:madeObservation.sosa:Observation`, inverse of `sosa:madeBySensor`), stating the sensor on an observation collection, as SSN-Ext allows, makes the collection an observation | Medium | **Fixed in v0.7**: `sosa:madeBySensor` on each member observation, forbidden on readings by SHACL (verified with owlrl and SOSA/SSN/SSN-Ext loaded) |
| R22 | `ens:` aliases of SOSA properties (`readingOfConsumptionPoint`, `measuredBy`, `readingPeriod`, `hasReading`, `installedOn`, `hasMeasurementFunction`, `hasDataHandlingSystem`) only restated SOSA with a narrower domain/range | Low | **Fixed in v0.7**: SOSA properties used directly; aliases deprecated with `dct:isReplacedBy`; domain/range checks moved to SHACL |
| R17 | `ens:exchangeContains` (settlement system → activity) is the undeclared inverse of `ens:exchangeRecipient`; name does not say "received" | Low | Open → P2 |

## 2. Changes in v0.7

1. Licence: EUPL v1.2 (`dct:license <http://data.europa.eu/eli/dec_impl/2017/863/oj>`, `LICENSE` copied from the ERA ontology repository at v4.0.0-rc.3, SPDX headers on the sources). `owl:versionIRI …/0.7.0`, `owl:priorVersion …/0.6.0`.
2. SOSA/SSN reuse for measurement:
   - `ens:EnergyReading ⊑ sosa:ObservationCollection, geo:Feature`; `ens:CompiledEnergyBillingData ⊑ prov:Entity, sosa:ObservationCollection` with readings as `sosa:hasMember`.
   - Each value is a member `sosa:Observation` with `sosa:observedProperty` (`ens:ConsumedActiveEnergy`, `ens:RegeneratedActiveEnergy`, `ens:MeasuredReactiveEnergy`, all `sosa:ObservableProperty`), `sosa:madeBySensor` (the EMF) and `sosa:hasResult [ a qudt:QuantityValue ; qudt:numericValue ; qudt:unit ]`.
   - On the reading: `sosa:hasFeatureOfInterest` (consumption point) and `sosa:phenomenonTime` (period). EMS: `sosa:isHostedBy` the vehicle, `sosa:hosts` EMF/DHS; the EMF `sosa:observes` the three properties.
   - `ens:activeEnergyConsumed`, `ens:activeEnergyRegenerated`, `ens:reactiveEnergy` are shortcuts derived by a SHACL rule, not source data.
3. Shapes: reading and observation shapes (required observed properties, no duplicates, decimal non-negative results, kWh/kvarh units), CEBD shape, EMS hosting. SPARQL constraints avoid `VALUES` (not allowed in SHACL SPARQL constraints).
4. Tests: CQ1.4 (properties observed by the EMF) and CQ3.4 (observed property, value and unit of each observation); negative tests for a kvarh unit on active energy and a reading without a consumed-energy observation. 51/51 CQs pass.

## 2a. Changes in v0.6

1. Namespace `http://data.europa.eu/dy6/def/energy/`; prefixes `ens:` (vocabulary), `ensc:` (concepts), `enssh:` (shapes). Synthetic instances stay in `http://example.org/data/`.
2. Ontology header: `dct:title`, `dct:description`, `owl:versionIRI <http://data.europa.eu/dy6/def/energy/0.6.0>`, `owl:versionInfo "0.6.0"`, `dct:modified`, `vann:preferredNamespacePrefix/Uri`, `vs:term_status` (ERA convention).
3. Every `ens:` term: `rdfs:label`, `rdfs:isDefinedBy`, `vs:term_status "unstable"`, and a `skos:definition` or comment.
4. `ens:TrainRun` renamed `ens:RunningTrain ⊑ era:Train` (hence `⊑ era:OperationalTrainNumberIdentifier`), so `era:operationalTrainNumber` replaces `ens:operationalTrainNumber` and `era:trainDepartureDate`/`era:trainOperatingRU` become available; renamed properties `ens:aboutRunningTrain`, `ens:matchedRunningTrain`; `ens:runningTrainId` removed, the key is `era:operationalTrainNumber` + `era:trainDepartureDate` (uniqueness checked in SHACL); new `ens:runningTrainIdent → era:TrainIdent`; `runStart`/`runEnd` documented as an attribution window, not actual departure.
5. `skos:closeMatch` removed from ontology terms (replaced by `rdfs:seeAlso`), see R18.
   Operating RU: `ens:operatingRailwayUndertaking` to an `era:OrganisationRole` with `era:hasOrganisationRole` RU/RU-n and `era:roleOf` a body; `enssh:RailwayUndertakingRoleShape`; `ens:railwayCompanyCode` deprecated for `era:organisationCode` (R12, R20). New CQ12.5 and three negative tests (non-RU role, code mismatch, duplicate train key).
6. `ens:allocatesReading owl:propertyChainAxiom (ens:hasAllocationComponent ens:componentReading)`.
7. Domains/ranges for `ens:forwardsTo` and `ens:exchangeProtocol`.
8. Shapes moved to `enssh:`; new `enssh:EnergyMeasurementSystemShape` and `enssh:ForwardsToShape`; dangling validation-rule links fixed. Two new negative tests (DCS → settlement system; EMS without vehicle).

Result: 49/49 CQs, SHACL conforms, accounting and all negative tests pass.

## 3. Roadmap

### P1 – v0.7: agents, roles and identity (needs a decision, see §4)

- Apply one party pattern (recommended: **roles for responsibilities in context, bodies for identity**, linked by `era:roleOf`): `exchangeSender`/`exchangeRecipient` → roles or agents; `responsibleRUOrganisation` kept as the resolution of a code to a body.
- Declare ground systems and EMS as `prov:SoftwareAgent` (or `sosa:System` + `prov:Agent`) so the PROV attribution is explicit; give `ens:operatedBy` a domain.
- Apply the operating-RU role pattern to `ens:responsibleRUOrganisation` (message → role instead of body) and to `ens:consumerRole`, and type `ens:EnergyConsumerRole` instances with an ERA role concept where one fits.
- Add test data and CQs with `era:TrainIdent` (TAF/TAP core elements) and a reused operational train number across two runs.

### P2 – v0.8: measurement, vocabularies and lifecycle

- Readings (done in v0.7, R13). Remaining: QUDT quantity kinds on the observable properties, `sosa:usedProcedure` for the EN 50463 measurement procedure instead of `ens:emsStandardVersion`, and `sosa:resultTime` for the CEBD compilation time.
- Move all concept schemes into `era-energy-settlement-concepts.ttl` under `ensc:` with definitions and `skos:notation`; split allocation **status** (valid, rejected, superseded) from **method** (metered, estimated, fallback-to-keeper).
- Corrections: `prov:wasRevisionOf` / `ens:supersedes` between allocations, reversal components, and a CQ "current allocation for a run and zone".
- Harmonise time: run interval as `time:Interval` or `prov:startedAtTime/endedAtTime` for actual times; require `xsd:dateTimeStamp` where timezone matters.
- Rename `ens:exchangeContains` → `ens:receivedExchange`, `owl:inverseOf ens:exchangeRecipient`.

### P3 – v0.9: scope extensions (open requirements)

- G4 network losses: `ens:LossAllocationMethod` concept + coefficient on allocation, with arithmetic tests.
- G3 market/contract: separate module (`dy6/def/energy` sub-module), not merged into the core, once legal interface duties are verified.
- Richer test data: multi-day runs, mixed time zones, multiple consumers, estimated and split components.
- EVN check-digit validation once the rule is confirmed against the authoritative register.

### P4 – publication and ERA governance (in parallel)

- Confirm with the Publications Office / ERA that `dy6/def/energy` is the allocated path and set up dereferencing and content negotiation for terms, `0.6.0` version IRIs and shapes.
- Licence: done in v0.7 (EUPL v1.2). Contributors still to be added to the header.
- Quality gates in CI: `cq_suite.py`, OWL 2 DL profile check (ROBOT `validate-profile`), OOPS! pitfall scan, HTML documentation (pyLODE or Widoco).
- Upstream change requests to the ERA ontology: object link from `era:LocoIdent`/`era:locoNumber` to `era:Vehicle`; unit of `era:trainWeight` (G5); clarify whether the run key should be `era:TrainIdent`; make `era:trainOperatingRU` (and `era:responsibleRU`) object properties to `era:OrganisationRole`, or add object counterparts, so `ens:operatingRailwayUndertaking` can be retired.

## 4. Decisions needed

1. Party pattern: roles vs bodies for sender, recipient and operator (R10).
2. Confirmation of the `dy6/def/energy` allocation with the Publications Office / ERA.

Settled: SOSA/SSN is the normative measurement model (v0.7); licence EUPL v1.2.
