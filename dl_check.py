# SPDX-License-Identifier: EUPL-1.2
"""OWL 2 DL consistency check with the HermiT reasoner.

HermiT (LGPL, University of Oxford) is the jar bundled with the owlready2
package; it needs a Java runtime. The check merges the ERA ontology
snapshot, the extension, the example data and the W3C SOSA, SSN and
SSN-Ext vocabularies, then asks HermiT whether the merged graph is
consistent and which classes are unsatisfiable.

Usage:
    python3 dl_check.py [extra.ttl ...]

Before reasoning, the merged graph is adjusted where the inputs fall
outside OWL 2 DL. Each adjustment is reported:
  - owl:imports are removed (everything is already merged, so HermiT
    must not fetch them);
  - the SSN-Ext axiom ObservationCollection ⊑ ≤1 sosa:usedProcedure is
    dropped: combined with the SSN property chains that define
    sosa:usedProcedure, it puts a non-simple property in a cardinality
    restriction. The extension does not use sosa:usedProcedure;
  - facet values of xsd:double/xsd:float datatype restrictions that carry
    another datatype are cast to the restricted datatype (rc.3 restricts
    era:dNvroll with xsd:decimal values);
  - owl:FunctionalProperty is removed from ERA super-properties that stand
    for an XSD simple type shared by several sub-properties (era:freeText,
    era:companyCode, ...). A message reference that ERA's shapes require to
    have both era:messageType and era:messageIdentifier, both
    era:freeText, would otherwise be inconsistent. The sub-properties keep
    their own owl:FunctionalProperty.
HermiT runs with --ignoreUnsupportedDatatypes, because xsd:date (used by
ERA and the examples) is not in the OWL 2 datatype map.
"""
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

import rdflib
from rdflib.namespace import OWL, RDF, RDFS, XSD

DEFAULT_ERA_ONTOLOGY = "era-ontology-v4.0.0-rc.3.ttl"
DRAFT = "era-energy-settlement-draft.ttl"
EXAMPLES = "era-energy-settlement-examples.ttl"
W3C_VOCABULARIES = ["vendor/w3c/sosa.ttl", "vendor/w3c/ssn.ttl", "vendor/w3c/ssn-ext.ttl"]
SOSA = rdflib.Namespace("http://www.w3.org/ns/sosa/")


@dataclass
class DLResult:
    consistent: bool
    unsatisfiable: list = field(default_factory=list)
    adjustments: list = field(default_factory=list)
    error: str = ""


def default_inputs(era_ontology=DEFAULT_ERA_ONTOLOGY):
    return [era_ontology, DRAFT, EXAMPLES] + W3C_VOCABULARIES


def hermit_classpath():
    import owlready2
    hermit = os.path.join(os.path.dirname(owlready2.__file__), "hermit")
    return f"{hermit}{os.pathsep}{os.path.join(hermit, 'HermiT.jar')}"


def to_dl_graph(graph):
    """Return a copy of graph adjusted for OWL 2 DL, and the adjustments made."""
    g = rdflib.Graph()
    for triple in graph:
        g.add(triple)
    adjustments = []

    imports = list(g.triples((None, OWL.imports, None)))
    if imports:
        g.remove((None, OWL.imports, None))
        adjustments.append(f"removed {len(imports)} owl:imports")

    for restriction in list(g.subjects(OWL.onProperty, SOSA.usedProcedure)):
        if (restriction, OWL.maxCardinality, None) in g:
            for cls in list(g.subjects(RDFS.subClassOf, restriction)):
                g.remove((cls, RDFS.subClassOf, restriction))
            g.remove((restriction, None, None))
            adjustments.append("dropped SSN-Ext max-cardinality restriction on sosa:usedProcedure")

    for restriction in list(g.subjects(OWL.onDatatype, None)):
        base = g.value(restriction, OWL.onDatatype)
        if base not in (XSD.double, XSD.float):
            continue
        facets = rdflib.collection.Collection(g, g.value(restriction, OWL.withRestrictions))
        for item in facets:
            for facet, value in list(g.predicate_objects(item)):
                if isinstance(value, rdflib.Literal) and value.datatype != base:
                    g.remove((item, facet, value))
                    g.add((item, facet, rdflib.Literal(str(value), datatype=base)))
                    owners = ", ".join(sorted(str(s) for s in g.subjects(None, restriction)))
                    adjustments.append(f"cast {facet.n3(g.namespace_manager)} {value} to "
                                       f"{base.n3(g.namespace_manager)} (restriction of {owners})")
    era = "http://data.europa.eu/949/"
    shared = sorted(p for p in g.subjects(RDF.type, OWL.FunctionalProperty)
                    if str(p).startswith(era)
                    and len(set(g.subjects(RDFS.subPropertyOf, p))) >= 2)
    for prop in shared:
        g.remove((prop, RDF.type, OWL.FunctionalProperty))
    if shared:
        adjustments.append("removed owl:FunctionalProperty from ERA super-properties shared by several "
                           "sub-properties: " + ", ".join(p.n3(g.namespace_manager) for p in shared))
    return g, adjustments


def run_hermit(graph, timeout=900):
    """Check the consistency of graph with HermiT; return a DLResult."""
    dl_graph, adjustments = to_dl_graph(graph)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "merged.owl")
        dl_graph.serialize(path, format="xml")
        proc = subprocess.run(
            ["java", "-Xmx3000M", "-cp", hermit_classpath(),
             "org.semanticweb.HermiT.cli.CommandLine",
             "--ignoreUnsupportedDatatypes", "-k", "-U", "file://" + path],
            capture_output=True, text=True, timeout=timeout)
    output = proc.stdout + proc.stderr
    if "InconsistentOntologyException" in output:
        return DLResult(False, adjustments=adjustments)
    if proc.returncode != 0:
        errors = [line for line in output.splitlines() if "Exception" in line]
        return DLResult(False, adjustments=adjustments, error=errors[0] if errors else output[-500:])
    unsatisfiable = []
    if "Classes equivalent to 'owl:Nothing':" in proc.stdout:
        listing = proc.stdout.split("Classes equivalent to 'owl:Nothing':", 1)[1]
        unsatisfiable = [c for c in listing.split() if c != "owl:Nothing"]
    return DLResult(True, unsatisfiable, adjustments)


def load(paths):
    graph = rdflib.Graph()
    for path in paths:
        graph.parse(path)
    return graph


def main():
    result = run_hermit(load(default_inputs() + sys.argv[1:]))
    for adjustment in result.adjustments:
        print("adjusted:", adjustment)
    if result.error:
        print("HermiT error:", result.error)
    print(f"HermiT: consistent={result.consistent}; unsatisfiable classes: {result.unsatisfiable or 'none'}")
    sys.exit(0 if result.consistent and not result.unsatisfiable else 1)


if __name__ == "__main__":
    main()
