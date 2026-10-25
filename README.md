# ERA energy settlement extension

A proposed OWL/RDF extension of the ERA ontology, in the namespace `http://data.europa.eu/dy6/def/energy/` (prefix `ens:`), for traction-energy readings, allocation components, exchange evidence, and links to ERA telematics/RINF concepts. The example data is synthetic. This is an ontology proposal, not a certified settlement implementation or legal compliance assessment.

## Run the checks

Requires Python 3.10+:

```sh
python3 -m pip install -r requirements.txt
python3 cq_suite.py --md era-energy-settlement-cqs.md
```

The runner uses the committed `era-ontology-v4.0.0-rc.3.ttl` snapshot by default. To test another ERA ontology file, pass its path as the first argument. The suite checks the sample graph with SHACL, runs the competency-question SPARQL tests, verifies allocation component arithmetic in Python, and confirms that deliberately invalid EVN, allocation, data-forwarding and EMS-installation fixtures are rejected.

## Files

- `era-energy-settlement-draft.ttl` — extension vocabulary and mappings. Energy readings follow SOSA/SSN and SSN-Ext: a reading is a `sosa:ObservationCollection` of `sosa:Observation`s with QUDT results.
- `era-energy-settlement-shapes.ttl` — SHACL constraints, the normalized EVN-to-vehicle rule and the rule deriving reading shortcuts from SOSA observations.
- `era-energy-settlement-examples.ttl` — synthetic sample data.
- `cq_suite.py` — executable competency questions and arithmetic/negative checks.
- `era-energy-settlement-cqs.md` — generated test report and open requirements.
- `ONTOLOGY-REVIEW-AND-PLAN.md` — ontology engineering review and update roadmap toward an ERA proposal.
- `LEGAL-AND-TELEMATICS-REVIEW.md` — implementation decisions and remaining legal/operational checks.
- `era-ontology-v4.0.0-rc.3.ttl` — upstream ERA ontology snapshot used for repeatable local validation.

See `THIRD-PARTY-NOTICES.md` for attribution and the ERA ontology license.

## Licence

The extension (vocabulary, shapes, examples and test suite) is licensed under the [European Union Public Licence v1.2](LICENSE) (EUPL-1.2, Commission Implementing Decision (EU) 2017/863), the licence of the ERA ontology. The vendored ERA ontology snapshot keeps its own terms; see `THIRD-PARTY-NOTICES.md`.
