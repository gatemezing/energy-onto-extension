# ERA energy settlement extension

A proposed OWL 2 extension of the [ERA ontology](https://gitlab.com/era-europa-eu/public/interoperable-data-programme/era-ontology/era-ontology) for on-board traction energy measurement, energy data exchange and settlement allocation, linked to ERA telematics (TEL TSI) and RINF concepts. It is prepared as a proposal for ERA governance.

| | |
|---|---|
| Namespace | `http://data.europa.eu/dy6/def/energy/` (prefix `ens:`); concepts `…/concepts/` (`ensc:`), shapes `…/shapes/` (`enssh:`) |
| Version | 0.9.0 (`owl:versionIRI <http://data.europa.eu/dy6/def/energy/0.9.0>`) |
| Baseline | ERA ontology v4.0.0-rc.3 (vendored) |
| Licence | [EUPL v1.2](LICENSE) |
| Status | Draft; all terms `vs:term_status "unstable"` |

The example data is synthetic. This is an ontology proposal, not a certified settlement implementation or a legal compliance assessment.

## Model at a glance

| Module | Main terms | Reused vocabularies |
|---|---|---|
| On-board measurement (EN 50463) | `ens:EnergyMeasurementSystem` (⊑ `saref:Meter`, `sosa:Platform`), `ens:EnergyMeasurementFunction` (⊑ `sosa:Sensor`), `ens:DataHandlingSystem`, `ens:ConsumptionPoint` (⊑ `sosa:FeatureOfInterest`) | SOSA/SSN, SAREF, `era:Vehicle` |
| Readings | `ens:CompiledEnergyBillingData` and `ens:EnergyReading`, both `sosa:ObservationCollection` (SSN-Ext); member `sosa:Observation`s of `ens:ConsumedActiveEnergy`, `ens:RegeneratedActiveEnergy`, `ens:MeasuredReactiveEnergy` with `qudt:QuantityValue` results | SOSA/SSN, SSN-Ext, QUDT, OWL-Time, GeoSPARQL |
| Grid and borders | `ens:readingOnTrack` → `era:RunningTrack`; `ens:SettlementZone` (⊑ `era:Feature`) delimited by `era:ReferenceBorderPoint` | RINF |
| Ground systems (IRS 90930) | `ens:DataCollectingSystem` → `ens:ExchangeFunction` → `ens:SettlementSystem` (`ens:forwardsTo`), all `ssn:System`, like the EMS and the data handling system | SSN |
| Roles | Every party-valued property targets an `era:OrganisationRole`, played by an `era:Body` (`era:roleOf`) and typed with an ERA organisation-roles concept: consumer, EMS responsible, operators, exchange sender and recipient, operating and responsible RU | ERA organisation roles |
| Running trains (TEL TSI) | `ens:RunningTrain` ⊑ `era:Train`, keyed by `era:operationalTrainNumber` + `era:trainDepartureDate`; linked from `era:TrainCompositionMessage` and `era:TrainRunningInformationMessage` | ERA telematics |
| Allocation | `ens:EnergyAllocation` with `ens:AllocationComponent`s per source reading; consumer, zone, status, method, rule | PROV-O |
| Exchange evidence | `ens:DataExchangeActivity` (⊑ `prov:Activity`): message, version, sender, recipient, time, outcome, purpose, authority, retention | PROV-O |

A reading in the sample data:

```turtle
d:r1 a ens:EnergyReading ;                      # ⊑ sosa:ObservationCollection
    sosa:hasFeatureOfInterest d:cp1 ;
    sosa:phenomenonTime [ a time:Interval ; … ] ;
    sosa:hasMember d:r1-consumed , d:r1-regenerated , d:r1-reactive .

d:r1-consumed a sosa:Observation ;
    sosa:madeBySensor d:emf1 ;                  # on the member, not the collection (see R21)
    sosa:observedProperty ens:ConsumedActiveEnergy ;
    sosa:hasResult [ a qudt:QuantityValue ; qudt:numericValue 410.5 ; qudt:unit unit:KiloW-HR ] .
```

## Run the checks

Requires Python 3.10+ and a Java runtime (17 or later) for HermiT:

```sh
python3 -m pip install -r requirements.txt
python3 cq_suite.py --md era-energy-settlement-cqs.md
```

`cq_suite.py` exits non-zero if any check fails. It:

1. validates the example graph with SHACL and applies the SHACL rules (EVN-to-vehicle link, reading shortcuts derived from SOSA observations);
2. runs the 53 competency questions as SPARQL queries with expected answers;
3. verifies allocation component arithmetic;
4. confirms that invalid fixtures are rejected: EVN mismatch, over-allocation, wrong data-forwarding chain, EMS without vehicle, non-RU operating role, RU code mismatch, duplicate train key, sender given as a body, recipient not operating the receiving system, role without body, responsible RU code mismatch, wrong energy unit, missing consumed-energy observation;
5. checks **OWL 2 DL consistency with HermiT** on the ERA snapshot, the extension, the examples and SOSA/SSN/SSN-Ext, reports unsatisfiable classes, and proves with two fixtures that an inconsistent ABox and an unsatisfiable class are detected;
6. checks that every reused `sosa:`, `ssn:` and `era:` term is declared in the vendored W3C files or the ERA snapshot.

Options: pass another ERA ontology file as the first argument; `--skip-dl` skips step 5. The DL check also runs on its own with `python3 dl_check.py [extra.ttl …]`; it prints the adjustments it makes where the inputs are outside OWL 2 DL (see the module docstring).

The same suite runs in GitHub Actions on every push and pull request (`.github/workflows/checks.yml`), which also fails when the committed report is out of date.

## Files

- `era-energy-settlement-draft.ttl` — extension vocabulary and alignments.
- `era-energy-settlement-shapes.ttl` — SHACL constraints and rules.
- `era-energy-settlement-examples.ttl` — synthetic sample data (a Norway–Sweden freight run).
- `cq_suite.py` — competency questions, SHACL, arithmetic, negative and DL checks.
- `dl_check.py` — HermiT OWL 2 DL consistency check.
- `era-energy-settlement-cqs.md` — generated test report and open requirements.
- `ONTOLOGY-REVIEW-AND-PLAN.md` — ontology engineering review, findings (R1–R25) and roadmap.
- `LEGAL-AND-TELEMATICS-REVIEW.md` — implementation decisions and remaining legal/operational checks.
- `era-ontology-v4.0.0-rc.3.ttl` — upstream ERA ontology snapshot used for repeatable validation.
- `vendor/w3c/` — W3C/OGC SOSA, SSN and SSN-Ext vocabularies used by the DL check.

## Presentation

A 15-slide overview (architecture figures of the main concepts and relations, including the organisation-role pattern and the model at a glance, sample competency questions, quality gates and requests to ERA) is published as a Claude artifact: <https://claude.ai/artifact/7PfPUbvX7nmpfyEXc7VKp7>. The link is private until its owner shares it.

## Roadmap

See `ONTOLOGY-REVIEW-AND-PLAN.md`. Next: apply the role pattern to the responsible RU and the energy consumer, make the ground systems explicit PROV agents, separate the concept schemes into their own file, model allocation corrections, then network losses and the market/contract module. Upstream requests to ERA are listed there as well.

## Licence

The extension (vocabulary, shapes, examples and scripts) is licensed under the [European Union Public Licence v1.2](LICENSE) (EUPL-1.2, Commission Implementing Decision (EU) 2017/863), the licence of the ERA ontology. Vendored third-party files keep their own terms; see `THIRD-PARTY-NOTICES.md`.
