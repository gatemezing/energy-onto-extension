# SPDX-License-Identifier: EUPL-1.2
"""Validate the example data against ERA's own telematics SHACL shapes.

The shapes (`vendor/era/telematics-shacl.ttl`) and the ERA concept schemes the
examples use (`vendor/era/skos/`) are vendored from the ERA ontology
repository at v4.0.0-rc.3.

Usage:
    python3 era_shapes_check.py

One adjustment is made before validating, and reported: ERA gives the numeric
bounds of several properties (sh:minInclusive, sh:maxInclusive, ...) as plain
strings ("0001", "9999", "99999") although the values must be xsd:integer,
xsd:int or xsd:positiveInteger. A number cannot be compared with a string, so
no data could conform; each such bound is cast to the datatype of its
property shape.
"""
import glob
import sys
from dataclasses import dataclass, field

import pyshacl
import rdflib
from rdflib.namespace import SH, XSD

DEFAULT_ERA_ONTOLOGY = "era-ontology-v4.0.0-rc.3.ttl"
DRAFT = "era-energy-settlement-draft.ttl"
EXAMPLES = "era-energy-settlement-examples.ttl"
ERA_SHAPES = "vendor/era/telematics-shacl.ttl"
ERA_CONCEPTS = sorted(glob.glob("vendor/era/skos/*.ttl"))

NUMERIC = {XSD.integer, XSD.int, XSD.long, XSD.short, XSD.positiveInteger,
           XSD.nonNegativeInteger, XSD.decimal, XSD.double, XSD.float}
FACETS = (SH.minInclusive, SH.maxInclusive, SH.minExclusive, SH.maxExclusive)
USED_BY_EXAMPLES = {"trainLength", "trainWeight", "stationLocationPrimaryCode", "freightLocationPrimaryCode"}


@dataclass
class EraShapesResult:
    conforms: bool
    results: list = field(default_factory=list)
    adjustments: list = field(default_factory=list)


def load_shapes(path=ERA_SHAPES):
    """Return ERA's shapes with string-typed numeric bounds cast, and a report."""
    shapes = rdflib.Graph().parse(path)
    cast = {}
    for prop_shape, datatype in list(shapes.subject_objects(SH.datatype)):
        if datatype not in NUMERIC:
            continue
        for facet in FACETS:
            for value in list(shapes.objects(prop_shape, facet)):
                if isinstance(value, rdflib.Literal) and value.datatype != datatype:
                    shapes.remove((prop_shape, facet, value))
                    shapes.add((prop_shape, facet, rdflib.Literal(str(value), datatype=datatype)))
                    path_ = shapes.value(prop_shape, SH.path)
                    cast.setdefault(str(path_).rsplit("/", 1)[-1], set()).add(datatype.n3(shapes.namespace_manager))
    used = sorted(name for name in cast if name in USED_BY_EXAMPLES)
    adjustments = [f"cast the string-typed numeric bounds of {len(cast)} ERA properties to their "
                   f"datatype, among them {', '.join('era:' + n for n in used)}"] if cast else []
    return shapes, adjustments


def data_graph(extra=()):
    graph = rdflib.Graph()
    for path in (DRAFT, EXAMPLES, *ERA_CONCEPTS, *extra):
        graph.parse(path)
    return graph


def validate(data, era_ontology=DEFAULT_ERA_ONTOLOGY, shapes=None):
    """Validate data against ERA's telematics shapes; return an EraShapesResult."""
    if shapes is None:
        shapes, adjustments = load_shapes()
    else:
        shapes, adjustments = shapes
    ont = rdflib.Graph().parse(era_ontology).parse(DRAFT)
    conforms, report, _ = pyshacl.validate(
        data, shacl_graph=shapes, ont_graph=ont, inference="none",
        advanced=True, allow_warnings=True)
    results = []
    for result in report.subjects(rdflib.RDF.type, SH.ValidationResult):
        focus = report.value(result, SH.focusNode)
        path_ = report.value(result, SH.resultPath)
        results.append((str(focus).rsplit("/", 1)[-1],
                        str(path_).rsplit("/", 1)[-1] if path_ else "-",
                        str(report.value(result, SH.resultMessage))))
    return EraShapesResult(conforms, sorted(set(results)), adjustments)


def main():
    result = validate(data_graph())
    for adjustment in result.adjustments:
        print("adjusted:", adjustment)
    for focus, path_, message in result.results:
        print(f"FAIL {focus} {path_}: {message}")
    print(f"ERA telematics shapes: conforms={result.conforms}; results: {len(result.results)}")
    sys.exit(0 if result.conforms else 1)


if __name__ == "__main__":
    main()
