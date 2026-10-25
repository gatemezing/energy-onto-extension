# Third-party notices

## European Union Agency for Railways ontology snapshot

`era-ontology-v4.0.0-rc.3.ttl` is an unmodified ERA ontology snapshot retrieved from the ERA ontology GitLab repository at the `v4.0.0-rc.3` ref:

<https://gitlab.com/era-europa-eu/public/interoperable-data-programme/era-ontology/era-ontology/-/raw/v4.0.0-rc.3/ontology.ttl>

The upstream repository identifies the ontology as licensed under the European Union Public Licence, version 1.2 (EUPL-1.2). The license text is available at:

<https://gitlab.com/era-europa-eu/public/interoperable-data-programme/era-ontology/era-ontology/-/raw/v4.0.0-rc.3/LICENSE>

The ERA ontology remains the work of its original authors and contributors. This notice does not relicense that work. See the upstream repository for the complete license and attribution terms.

## W3C/OGC SOSA, SSN and SSN-Ext vocabularies

`vendor/w3c/sosa.ttl`, `vendor/w3c/ssn.ttl` and `vendor/w3c/ssn-ext.ttl` are unmodified copies of the W3C/OGC Semantic Sensor Network vocabularies (SOSA and SSN, W3C Recommendation 2017; SSN Extensions, W3C Working Group Note), retrieved from the W3C Spatial Data on the Web repository:

- <https://raw.githubusercontent.com/w3c/sdw/gh-pages/ssn/integrated/sosa.ttl>
- <https://raw.githubusercontent.com/w3c/sdw/gh-pages/ssn/integrated/ssn.ttl>
- <https://raw.githubusercontent.com/w3c/sdw/gh-pages/ssn-extensions/rdf/ssn-ext.ttl>

Copyright 2017–2019 W3C/OGC. They are distributed under the [W3C Software and Document License](http://www.w3.org/Consortium/Legal/2015/copyright-software-and-document) and the [OGC Software License](http://www.opengeospatial.org/ogc/Software). They are used only by the OWL 2 DL consistency check (`dl_check.py`).

## HermiT reasoner

`dl_check.py` runs HermiT, the OWL 2 DL reasoner of the University of Oxford, from the jar bundled with the `owlready2` Python package (installed from `requirements.txt`, not vendored here). HermiT is licensed under the GNU Lesser General Public License v3 or later.
