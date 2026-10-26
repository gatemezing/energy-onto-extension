# Ontology engineering review and update plan

Scope: `era-energy-settlement-draft.ttl` (vocabulary), `era-energy-settlement-shapes.ttl`, the example graph and the competency-question suite, reviewed against ERA ontology v4.0.0-rc.3. Target: a **proposal to ERA governance**, published under `http://data.europa.eu/dy6/def/energy/`.

**Current draft: 0.9.0** (`owl:versionIRI <http://data.europa.eu/dy6/def/energy/0.9.0>`), licensed under EUPL v1.2.

The legal and telematics review (`LEGAL-AND-TELEMATICS-REVIEW.md`) and open requirements G1–G6 (`era-energy-settlement-cqs.md` §4) remain valid; this document covers modelling quality, reuse and publication.

## 1. Assessment summary

**Status at 0.9.0**

| | |
|---|---|
| Competency questions | 56 of 56 pass, in 15 sets |
| Invalid fixtures rejected | 15 (12 by SHACL or the arithmetic check, 1 by ERA's telematics shapes, 2 by HermiT) |
| ERA telematics shapes | The examples conform to ERA's own shapes (vendored from rc.3) |
| OWL 2 DL (HermiT) | Consistent; no unsatisfiable classes |
| Terms | 96 `ens:` terms, each labelled, defined and given a term status; 9 deprecated with `dct:isReplacedBy` |
| Reused terms | 113 of 113 `sosa:`, `ssn:` and `era:` terms declared at their source |
| CI | `cq_suite.py` runs on every push and pull request (GitHub Actions) |
| Findings | 31 recorded: 21 fixed, 1 partly fixed, 5 worked around or reported upstream, 4 open |

**Strengths**

- A clear requirements basis: executable competency questions, SHACL shapes and rules, arithmetic checks, negative fixtures and an OWL 2 DL consistency check, run against a vendored ERA release (LOT-style ORSD → implementation → evaluation).
- Strong reuse: SOSA/SSN and SSN-Ext for measurement, QUDT quantities, PROV-O for evidence and exchange, OWL-Time, GeoSPARQL, SAREF, and RINF/telematics anchors (`era:Vehicle`, `era:RunningTrack`, `era:ReferenceBorderPoint`, `era:OperationalTrainNumberIdentifier`, `era:TrainIdent`, the TEL TSI messages).
- One party pattern: every party-valued property targets `era:OrganisationRole`, as ERA does.
- Clean separation between the data model, its validation and legal evidence; the model never claims compliance.
- No modification of `era:` terms, only extension; upstream issues are recorded as change requests.

**Findings**

| # | Finding | Severity | Status |
|---|---|---|---|
| R1 | `example.org` namespace; prefix `ex:` signals example terms | High (blocks proposal) | **Fixed in 0.6** |
| R2 | `era:shaclShapeValidationRule` pointed to four `exsh:` shapes that did not exist; shapes were declared in the vocabulary namespace | High | **Fixed in 0.6**: shapes in `enssh:`, links resolve |
| R3 | 70+ terms without `rdfs:label`, ~35 without any definition; no `rdfs:isDefinedBy` or term status | Medium | **Fixed in 0.6** |
| R4 | No ontology metadata (title, description, versionIRI, preferred prefix, licence) | Medium | **Fixed in 0.6**, licence in 0.7 |
| R5 | `ens:TrainRun` typed as `prov:Entity` and disconnected from the telematics train concepts | Medium | **Fixed in 0.6**: renamed `ens:RunningTrain` (cf. `era:RunningTrack`), `⊑ era:Train` (superclass dropped in 0.9, R19) |
| R6 | Run identity not aligned with TAF/TAP: rc.3 has `era:TrainIdent` (unique contracted train ID) and `era:operationalTrainNumber` | Medium | **Fixed in 0.9**: a run is keyed by its `era:OperationalTrainNumberIdentifier` (`ens:runningTrainNumberIdentifier`, the node the messages carry) and `ens:departureDate`, unique together by SHACL; `ens:runningTrainIdent → era:TrainIdent` in the data; the number 41234 runs on two days (CQ12.6) |
| R7 | `ens:allocatesReading` duplicates the component path without a stated relation | Medium | **Fixed in 0.6**: OWL 2 property chain |
| R8 | `ens:forwardsTo` / `ens:exchangeProtocol` without domain/range; no check of admissible flow | Low | **Fixed in 0.6**, with `enssh:ForwardsToShape` |
| R9 | Header comments contradicted the model (TrainRun "removed") and the CQ count | Low | **Fixed in 0.6** |
| R10 | Inconsistent party pattern: some properties targeted `era:Body` (`exchangeSender`, `responsibleRUOrganisation`), others `era:OrganisationRole` | High | **Fixed in 0.8**: every party-valued `ens:` property targets `era:OrganisationRole`; CQ10.4 guards it |
| R11 | Implicit PROV agents: `compiledBy`/`producedBy` ⊑ `prov:wasAttributedTo` (range `prov:Agent`) make EMS and settlement systems agents by inference only; ground systems have no superclass | Medium | **Fixed in 0.9**: the EMS, data handling, data collecting, exchange and settlement systems are `ssn:System`; agency stays an inference (decision, §4); CQ6.5 |
| R12 | `ens:railwayCompanyCode` duplicates `era:organisationCode` (ERA-allocated code on `era:Body`) | Medium | **Fixed in 0.6**: deprecated, `dct:isReplacedBy era:organisationCode` |
| R13 | `ens:EnergyReading` was both `sosa:Observation` and `geo:Feature` and carried several results as datatype properties | Medium | **Fixed in 0.7**: reading = `sosa:ObservationCollection` (SSN-Ext) of `sosa:Observation`s with `qudt:QuantityValue` results |
| R14 | Concept schemes are defined only in the example data; `AllocationStatuses` mixes status and method (`estimated`, `fallback-to-keeper`) | Medium | Open → 0.10 |
| R15 | Corrections expressed as an `ens:allocationVersion` string; no supersession or reversal | Medium | Open → 0.10 |
| R16 | Time modelled two ways: `time:Interval` for readings, an `xsd:dateTime` pair for runs; timezone not enforced | Low | Open → 0.10 |
| R17 | `ens:exchangeContains` (settlement system → activity) does not say "received"; since 0.8 it links the receiving system while `ens:exchangeRecipient` names the receiving role | Low | Open → 0.10 |
| R18 | `skos:closeMatch` between OWL terms: with the SKOS schema, an RDFS or OWL RL reasoner types them as `skos:Concept`, and an annotation-property declaration clashes with SKOS in OWL 2 DL | Medium | **Fixed in 0.6**: `rdfs:seeAlso`; no SKOS mapping properties on ontology terms (verified with owlrl) |
| R19 | `era:Train` is a TAF/TAP message element (its other subclasses are `era:TrainStopType` and `era:WagonStatusMessage`) with ERA shape links; if ERA shapes target `era:Train`, running trains are validated against them | Low | **Fixed in 0.9**: ERA's TAP shape for `era:Train` requires `era:trainNb`, a train service number that running trains do not carry, so `ens:RunningTrain` is no longer `⊑ era:Train` (decision, §4) |
| R20 | `era:trainOperatingRU` and `era:responsibleRU` are datatype properties (company code strings), but the RU is the organisation role of a body | Medium | **Fixed locally in 0.6 and 0.8**: `ens:operatingRailwayUndertaking` and `ens:responsibleRailwayUndertaking` → RU role; the source code must equal the body's `era:organisationCode`. Upstream request in §3 |
| R21 | With the full SSN axioms (`sosa:Sensor ⊑ ∀ sosa:madeObservation.sosa:Observation`), stating the sensor on an observation collection makes the collection an observation | Medium | **Fixed in 0.7**: `sosa:madeBySensor` on each member observation, forbidden on readings by SHACL |
| R22 | `ens:` aliases of SOSA properties only restated SOSA with a narrower domain/range | Low | **Fixed in 0.7**: SOSA properties used directly; aliases deprecated; domain/range checks in SHACL |
| R23 | Example message `d:tri1` carried three `era:trainLocationReport`s, but rc.3 declares it functional; HermiT found the ABox inconsistent (SHACL and the CQs did not) | High | **Fixed in 0.7**: one location report per message; a DL negative test keeps it detected |
| R24 | ERA rc.3 restricts `era:dNvroll` to `xsd:double` with `xsd:decimal` facet values, which is not valid OWL 2 DL | Low (upstream) | Worked around in `dl_check.py` (facets cast and reported); upstream request in §3 |
| R25 | SSN (property chains defining `sosa:usedProcedure`) combined with SSN-Ext (`ObservationCollection ⊑ ≤1 sosa:usedProcedure`) is outside OWL 2 DL | Low (W3C) | Worked around in `dl_check.py`: that one SSN-Ext axiom (unused here) is dropped and reported |
| R26 | `ens:DataHandlingSystem ⊑ sosa:System`, a term W3C SOSA/SSN does not define (the class is `ssn:System`); nothing checked that reused terms exist | Medium | **Fixed in 0.9**: `ssn:System`; `cq_suite.py` now checks that every reused `sosa:`, `ssn:` and `era:` term is declared at its source |
| R27 | The example telematics messages did not conform to ERA's own telematics shapes (missing header, reference, sender and recipient nodes, message status, location codes); nothing ran those shapes | Medium | **Fixed in 0.9**: the examples are valid ERA telematics data; `era_shapes_check.py` gates them in `cq_suite.py` and CI, with a negative fixture |
| R28 | ERA's telematics shapes give the numeric bounds of 182 properties (`era:trainLength`, `era:trainWeight`, location codes, …) as strings, which no number can satisfy | Medium (upstream) | Worked around in `era_shapes_check.py` (bounds cast to the property datatype and reported); upstream request in §3 |
| R29 | ERA declares XSD-type super-properties functional (`era:freeText`, `era:companyCode`, `era:countryIdentISO`, `era:numberOfPassengerType`, `era:trackDataParameter`) although several sub-properties share them: a message reference with both `era:messageType` and `era:messageIdentifier`, which ERA's shapes require, is inconsistent in OWL | High (upstream) | Worked around in `dl_check.py` (functional axiom removed from super-properties with ≥ 2 sub-properties, reported); upstream request in §3; cf. ERA issue #482 |
| R30 | `era:primaryLocationName` has range `rdf:langString` in the ontology, but ERA's telematics shapes require `xsd:string` | Low (upstream) | The examples follow the shapes (plain strings); upstream request in §3 |
| R31 | The ERA organisation-roles scheme has no concept for the energy consumer, the EMS responsible, the DCS administrator or the settlement operator | Low | **Partly fixed in 0.9**: RU, IM and keeper roles carry `eraor:` concepts; CQ10.5 lists the five roles without one; request new concepts from ERA (§3) |

## 2. Version history

### 0.9.0 – systems on SSN, run identity and ERA telematics conformance

1. The EMS, the data handling system, the data collecting system, the exchange function and the settlement system are subclasses of `ssn:System` (R11). No `prov:Agent` superclass is stated: agency stays an inference from `ens:compiledBy` and `ens:producedBy` (decision, §4).
2. `ens:DataHandlingSystem` used `sosa:System`, which W3C SOSA/SSN does not define; it is now `ssn:System` (R26).
3. New gate in `cq_suite.py`: every reused `sosa:`, `ssn:` and `era:` term must be declared in the vendored W3C files or the ERA snapshot (71 terms; it flags `sosa:System` on 0.8).
4. Every reused class (12 ERA, 7 SOSA/SSN, and PROV-O, OWL-Time, GeoSPARQL, QUDT, SAREF and SKOS classes: 26 in all) is declared as `owl:Class` with the `rdfs:label` of its source vocabulary, in Part 3 of the draft.
5. `ens:RunningTrain` is no longer a subclass of `era:Train` (R19). A run is identified by `ens:runningTrainNumberIdentifier` (→ `era:OperationalTrainNumberIdentifier`, the same node the TCM and TRI messages carry) and `ens:departureDate` (`xsd:date`, `rdfs:seeAlso era:trainDepartureDate`); SHACL requires the pair to be unique and the message number to match the run (R6).
6. The sample data is valid ERA telematics data (R27): message headers with named reference, sender and recipient nodes, `era:messageStatus`, journey sections with origin, destination, responsibility, running, activity and technical data, train running information with location reports and running status, ERA location codes and countries, and an `era:TrainIdent`. Operational train number 41234 runs on two days.
7. New gate: `era_shapes_check.py` validates the draft, the examples and the ERA concept schemes they use against ERA's telematics SHACL shapes (vendored from rc.3 in `vendor/era/`), with a fixture without `era:messageStatus` that must be rejected. It reports the cast of string numeric bounds (R28); `dl_check.py` reports the removal of shared functional super-properties (R29).
8. Role concepts: the keeper role carries `eraor:Keeper`; the energy consumer, EMS responsible, DCS administrator and settlement operator roles have no ERA concept yet (R31).
9. New CQ6.5 (classes declared as `ssn:System`), CQ10.5 (roles without an ERA concept), CQ12.6 (runs sharing a train number) and CQ12.7 (TAF/TAP path, origin and scheduled time of a run). Result: 56/56 CQs, SHACL conforms, accounting and all negative tests pass, ERA telematics shapes conform, 113/113 reused terms declared, HermiT consistent.

### 0.8.0 – one party pattern

1. Every party-valued `ens:` property targets `era:OrganisationRole` (R10). The role reaches its `era:Body` through `era:roleOf` and its kind through `era:hasOrganisationRole` (ERA organisation-roles scheme).
   - `ens:exchangeSender` and `ens:exchangeRecipient` target roles: in the examples the IM roles of Bane NOR and Trafikverket send, the settlement operator roles receive. The receiving system stays linked by `ens:exchangeContains`, and SHACL requires it to be operated by the recipient role.
   - `ens:responsibleRUOrganisation` (message → body) is deprecated for `ens:responsibleRailwayUndertaking` (message → RU role), checked like the operating RU.
   - `ens:operatedBy` has a domain (DCS, exchange function, settlement system); every `era:OrganisationRole` has exactly one `era:roleOf` body.
   - `ens:producedBy` and `ens:compiledBy` keep a system range: they name the technical agent, not a party.
2. Tests: new CQ10.4 (no current `ens:` property ranges over `era:Body`); CQ6.4, CQ12.2 and CQ12.4 follow the role pattern; four new negative fixtures (sender as a body, recipient not operating the receiving system, role without body, responsible RU code mismatch).
3. Result: 52/52 CQs, SHACL conforms, accounting and all negative tests pass, HermiT consistent.

### 0.7.0 – SOSA/SSN, licence and DL reasoning

1. Licence EUPL v1.2 (`dct:license <http://data.europa.eu/eli/dec_impl/2017/863/oj>`, `LICENSE` from the ERA ontology repository at v4.0.0-rc.3, SPDX headers on the sources).
2. Measurement on SOSA/SSN (R13, R21, R22):
   - `ens:EnergyReading ⊑ sosa:ObservationCollection, geo:Feature`; `ens:CompiledEnergyBillingData ⊑ prov:Entity, sosa:ObservationCollection` with readings as `sosa:hasMember`.
   - Each value is a member `sosa:Observation` of `ens:ConsumedActiveEnergy`, `ens:RegeneratedActiveEnergy` or `ens:MeasuredReactiveEnergy` (all `sosa:ObservableProperty`), with `sosa:madeBySensor` and a `qudt:QuantityValue` result.
   - On the reading: `sosa:hasFeatureOfInterest` and `sosa:phenomenonTime`. EMS: `sosa:isHostedBy` the vehicle, `sosa:hosts` EMF and DHS.
   - The compact values `ens:activeEnergyConsumed`, `ens:activeEnergyRegenerated` and `ens:reactiveEnergy` are derived by a SHACL rule.
3. Shapes for readings, observations (units, members), CEBD and EMS hosting; no `VALUES` in SPARQL constraints.
4. OWL 2 DL reasoning: `dl_check.py` runs HermiT on ERA rc.3, the extension, the examples and vendored SOSA/SSN/SSN-Ext, by default in `cq_suite.py`, with two negative fixtures. It found R23. GitHub Actions runs the suite on every push and pull request.
5. Tests: CQ1.4 and CQ3.4 on the SOSA model; negative fixtures for a kvarh unit on active energy and a reading without a consumed-energy observation. Result: 51/51 CQs.

### 0.6.0 – namespace, documentation and identity

1. Namespace `http://data.europa.eu/dy6/def/energy/`; prefixes `ens:`, `ensc:` (concepts) and `enssh:` (shapes); synthetic instances in `http://example.org/data/` (R1).
2. Ontology header and term documentation: title, description, versionIRI, preferred prefix, `vs:term_status`; every term labelled and defined (R3, R4, R9).
3. `ens:RunningTrain ⊑ era:Train`, keyed by `era:operationalTrainNumber` + `era:trainDepartureDate`; `ens:runningTrainIdent → era:TrainIdent` (R5, R6).
4. Operating RU as an `era:OrganisationRole` with the ERA RU concepts; `ens:railwayCompanyCode` deprecated for `era:organisationCode` (R12, R20).
5. `skos:closeMatch` removed from ontology terms (R18); property chain for `ens:allocatesReading` (R7); domains and ranges for `ens:forwardsTo` and `ens:exchangeProtocol` (R8).
6. Shapes moved to `enssh:` with working validation-rule links (R2); EMS and forwarding shapes with negative tests. Result: 49/49 CQs.

## 3. Roadmap

### 0.9 – agents, role concepts and identity (done)

- Ground systems and the EMS as `ssn:System` (R11, R26).
- ERA organisation-roles concepts on every role where one exists (R31; the missing ones are requested from ERA).
- Run identity by operational train number identifier and departure date, with `era:TrainIdent` test data (R6).
- ERA telematics shapes run on the examples and gated in CI (R19, R27).

### 0.10 – vocabularies, lifecycle and time

- Move the concept schemes into `era-energy-settlement-concepts.ttl` under `ensc:` with definitions and `skos:notation`; split allocation **status** (valid, rejected, superseded) from **method** (metered, estimated, fallback-to-keeper) (R14).
- Corrections: `prov:wasRevisionOf` or `ens:supersedes` between allocations, reversal components, and a CQ for the current allocation of a run and zone (R15).
- Harmonise time: the run interval as `time:Interval`, `prov:startedAtTime`/`endedAtTime` for actual times, `xsd:dateTimeStamp` where the timezone matters (R16).
- Rename `ens:exchangeContains` to `ens:receivedExchange` (R17).
- Measurement details: QUDT quantity kinds on the observable properties, `sosa:usedProcedure` for the EN 50463 procedure instead of `ens:emsStandardVersion`, `sosa:resultTime` for the CEBD compilation time.

### 0.11 – scope extensions (open requirements)

- G4 network losses: `ens:LossAllocationMethod` concept and a coefficient on the allocation, with arithmetic tests.
- G3 market and contract: a separate module under `dy6/def/energy`, not merged into the core, once the legal interface duties are verified.
- Richer test data: multi-day runs, mixed time zones, multiple consumers, estimated and split components.
- EVN check-digit validation once the rule is confirmed against the authoritative register.

### Publication and ERA governance (in parallel)

- Confirm with the Publications Office and ERA that `dy6/def/energy` is the allocated path; set up dereferencing and content negotiation for the terms, the release version IRIs (0.6.0–0.8.0) and the shapes.
- Add the contributors to the ontology header.
- Quality gates: the suite with the HermiT check already runs in CI. Still to add: an OWL 2 DL profile report (ROBOT `validate-profile`), an OOPS! pitfall scan, and HTML documentation (pyLODE or Widoco).
- Presentation: a 15-slide overview with the architecture figures, the model at a glance, sample CQs and the quality gates (link in the README).
- Change requests to the ERA ontology:
  - an object link from `era:LocoIdent`/`era:locoNumber` to `era:Vehicle`;
  - the unit of `era:trainWeight` (G5);
  - confirmation that the operational train number identifier plus departure date is the right run key when no `era:TrainIdent` is available (R6);
  - `xsd:double` facet values on `era:dNvroll` (R24);
  - confirmation against the TAF XSD that `era:trainLocationReport` is single-valued (R23);
  - numeric bounds of the telematics shapes typed as numbers, not strings (R28);
  - `owl:FunctionalProperty` removed from XSD-type super-properties shared by several sub-properties (R29; ERA issue #482);
  - one datatype for `era:primaryLocationName` in the ontology and the shapes (R30);
  - organisation-roles concepts for the energy consumer, EMS responsible, DCS administrator and settlement operator, or guidance on which existing concepts apply (R31);
  - `era:trainOperatingRU` and `era:responsibleRU` as object properties to `era:OrganisationRole`, or object counterparts, so that `ens:operatingRailwayUndertaking` and `ens:responsibleRailwayUndertaking` can be retired (R20).

## 4. Decisions

**Needed**

1. Confirmation of the `dy6/def/energy` allocation with the Publications Office and ERA.

**Settled**

- SOSA/SSN is the normative measurement model (0.7).
- Licence: EUPL v1.2 (0.7).
- All party-valued properties target `era:OrganisationRole`; systems stay the range of `ens:producedBy` and `ens:compiledBy` (0.8).
- Ground systems and the EMS are `ssn:System` only; `prov:Agent` is left to inference (0.9).
- `ens:RunningTrain` is not a subclass of `era:Train`: a running train is not a TAP train service and carries no `era:trainNb` (0.9).
- The sample data must conform to ERA's telematics shapes; the check gates CI (0.9).
