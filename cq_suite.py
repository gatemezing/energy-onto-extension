# SPDX-License-Identifier: EUPL-1.2
"""Competency question test suite for the ERA energy settlement extension.

Each competency question (CQ) is an executable SPARQL query with an
expected answer, so the CQs act as acceptance tests (LOT validation).

Usage:
    python3 cq_suite.py [era-ontology-v4.0.0-rc.3.ttl] [--md era-energy-settlement-cqs.md] [--skip-dl]

Steps:
  1. Load the ontology draft and the example data.
  2. Run the SHACL shapes against the pinned ERA ontology snapshot: this
     checks the examples and derives ens:tractionUnitVehicle.
  3. Run every CQ and compare with its expected answer.
  4. Check OWL 2 DL consistency with HermiT (dl_check.py) on the ERA
     snapshot, the extension, the examples and SOSA/SSN/SSN-Ext, and prove
     with two fixtures that inconsistency and unsatisfiable classes are
     detected. Needs Java; --skip-dl skips it.
  5. Optionally render the Markdown report.
"""
import argparse
import sys
from collections import defaultdict
from decimal import Decimal

import pyshacl
import rdflib
from rdflib.namespace import SH

import dl_check
import era_shapes_check

DRAFT = "era-energy-settlement-draft.ttl"
SHAPES = "era-energy-settlement-shapes.ttl"
EXAMPLES = "era-energy-settlement-examples.ttl"
DEFAULT_ERA_ONTOLOGY = "era-ontology-v4.0.0-rc.3.ttl"

PREFIXES = """
PREFIX ens:      <http://data.europa.eu/dy6/def/energy/>
PREFIX ensc:     <http://data.europa.eu/dy6/def/energy/concepts/>
PREFIX era:     <http://data.europa.eu/949/>
PREFIX d:       <http://example.org/data/>
PREFIX rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos:    <http://www.w3.org/2004/02/skos/core#>
PREFIX time:    <http://www.w3.org/2006/time#>
PREFIX geo:     <http://www.opengis.net/ont/geosparql#>
PREFIX xsd:     <http://www.w3.org/2001/XMLSchema#>
PREFIX sosa:    <http://www.w3.org/ns/sosa/>
PREFIX ssn:     <http://www.w3.org/ns/ssn/>
PREFIX qudt:    <http://qudt.org/schema/qudt/>
PREFIX owl:     <http://www.w3.org/2002/07/owl#>
PREFIX saref:   <https://saref.etsi.org/core/>
PREFIX country: <http://publications.europa.eu/resource/authority/country/>
"""

# ---------------------------------------------------------------------
# The 15 CQ sets. Each set: id, title, user story, sources, CQs.
# Each CQ: id, question, archetype, kind (ABox/TBox), query, expected.
# Archetypes follow Ren et al. (2014) / CLaRO (Keet et al., 2019).
# ---------------------------------------------------------------------

SETS = [
    {
        "id": "S1", "title": "On-board energy measurement system",
        "story": "As a settlement operator, I want to know which EMS is fitted on which traction unit and what it consists of, so that I can trust the origin of metered data.",
        "sources": "EN 50463-1/-2/-3; LOC & PAS TSI 4.2.8.2.8; AS-03 §3.1.1",
        "cqs": [
            ("CQ1.1", "Which EMS is installed on the vehicle with EVN 918061890013?",
             "Selection: Which [CE1] [OPE] [CE2]?", "ABox",
             """SELECT ?ems WHERE {
  ?vehicle era:vehicleNumber "918061890013" .
  ?ems sosa:isHostedBy ?vehicle .
}""", [("ems1",)]),
            ("CQ1.2", "Which components (measurement function, data handling system) does EMS ems1 host?",
             "Selection over a property hierarchy", "ABox",
             """SELECT ?component WHERE {
  ?p rdfs:subPropertyOf* sosa:hosts .
  d:ems1 ?p ?component .
}""", [("dhs1",), ("emf1",)]),
            ("CQ1.3", "Is every EMS both a SAREF meter and a SOSA platform?",
             "Existence (TBox): Is [CE1] a [CE2]?", "TBox",
             """ASK {
  ens:EnergyMeasurementSystem rdfs:subClassOf saref:Meter , sosa:Platform .
}""", [("true",)]),
            ("CQ1.4", "Which observable properties does the measurement function of EMS ems1 observe?",
             "Selection through SOSA hosting and observation", "ABox",
             """SELECT ?property WHERE {
  d:ems1 sosa:hosts ?emf .
  ?emf a ens:EnergyMeasurementFunction ;
       sosa:observes ?property .
}""", [("ConsumedActiveEnergy",), ("MeasuredReactiveEnergy",), ("RegeneratedActiveEnergy",)]),
        ],
    },
    {
        "id": "S2", "title": "Consumption point identity",
        "story": "As a DCS administrator, I want each consumption point identified by the traction unit's EVN, so that metered data can be matched to train composition messages.",
        "sources": "prEN 50463 revision (EMS vs consumption point); TEL TSI Annex 2.5.1(16)",
        "cqs": [
            ("CQ2.1", "Which consumption point does EMS ems1 measure, and what is its identifier?",
             "Selection with attribute", "ABox",
             """SELECT ?cp ?id WHERE {
  d:ems1 ens:measuresConsumptionPoint ?cp .
  ?cp ens:consumptionPointId ?id .
}""", [("cp1", "918061890013")]),
            ("CQ2.2", "Which registered vehicle does the consumption point identifier '91 80 6189 001-3' designate?",
             "Selection with value matching", "ABox",
             """SELECT ?vehicle WHERE {
  ?cp ens:consumptionPointOf ?vehicle .
  ?cp ens:consumptionPointId ?id .
  ?vehicle era:vehicleNumber ?evn .
  FILTER (REPLACE(STR(?id), "[ -]", "") = REPLACE("91 80 6189 001-3", "[ -]", ""))
  FILTER (REPLACE(STR(?evn), "[ -]", "") = REPLACE(STR(?id), "[ -]", ""))
}""", [("loco1",)]),
            ("CQ2.3", "How many consumption points have an identifier different from their vehicle's EVN?",
             "Counting: How many [CE1] [OPE] [CE2]?", "ABox",
             """SELECT (COUNT(?cp) AS ?n) WHERE {
  ?cp ens:consumptionPointId ?id ; ens:consumptionPointOf/era:vehicleNumber ?evn .
  FILTER (REPLACE(STR(?id), "[ -]", "") != REPLACE(STR(?evn), "[ -]", ""))
}""", [("0",)]),
        ],
    },
    {
        "id": "S3", "title": "Compiled energy billing data and readings",
        "story": "As a settlement operator, I want to read the CEBD sent by an EMS, period by period, so that I can validate and bill consumption.",
        "sources": "EN 50463-3 (CEBD); ENE TSI 4.2.17; AS-03 Table 4 (Belgium, ReadingBlock)",
        "cqs": [
            ("CQ3.1", "Which readings does CEBD cebd1 contain, and when does each period start?",
             "Selection with temporal attribute", "ABox",
             """SELECT ?reading (SUBSTR(STR(?start), 12, 5) AS ?hhmm) WHERE {
  d:cebd1 sosa:hasMember ?reading .
  ?reading sosa:phenomenonTime/time:hasBeginning/time:inXSDDateTimeStamp ?start .
}""", [("r1", "06:00"), ("r2", "06:05"), ("r3", "08:40")]),
            ("CQ3.2", "What is the total active energy consumed by consumption point cp1 during UTC day 15 October 2026?",
             "Aggregation over a time window", "ABox",
             """SELECT (SUM(?kwh) AS ?total) WHERE {
  ?reading sosa:hasFeatureOfInterest d:cp1 ;
           ens:activeEnergyConsumed ?kwh ;
           sosa:phenomenonTime/time:hasBeginning/time:inXSDDateTimeStamp ?start ;
           sosa:phenomenonTime/time:hasEnd/time:inXSDDateTimeStamp ?end .
  FILTER (STR(?start) >= "2026-10-15T00:00:00Z" &&
          STR(?start) < "2026-10-16T00:00:00Z")
}""", [("885.7",)]),
            ("CQ3.3", "Which readings are one-minute reading blocks?",
             "Selection by subtype", "ABox",
             """SELECT ?reading WHERE { ?reading a ens:ReadingBlock . }""", [("r3",)]),
            ("CQ3.4", "Which observed property, value and unit does each member observation of reading r1 report?",
             "Selection through the SOSA observation collection", "ABox",
             """SELECT ?property ?value ?unit WHERE {
  d:r1 rdf:type/rdfs:subClassOf* sosa:ObservationCollection ;
       sosa:hasMember ?observation .
  ?observation a sosa:Observation ;
               sosa:observedProperty ?property ;
               sosa:hasResult [ qudt:numericValue ?value ; qudt:unit ?unit ] .
}""", [("ConsumedActiveEnergy", "410.5", "KiloW-HR"),
       ("MeasuredReactiveEnergy", "30.2", "KiloVAR-HR"),
       ("RegeneratedActiveEnergy", "12.0", "KiloW-HR")]),
        ],
    },
    {
        "id": "S4", "title": "Regenerative braking",
        "story": "As an RU, I want energy returned through regenerative braking to be measured and credited, so that eco-driving is rewarded.",
        "sources": "AS-03 §3.1 and §5.6.2(g); EN 50463-2; TEL TSI composition data",
        "cqs": [
            ("CQ4.1", "How much energy did consumption point cp1 return to the contact line during UTC day 15 October 2026?",
             "Aggregation", "ABox",
             """SELECT (SUM(?kwh) AS ?total) WHERE {
  ?reading sosa:hasFeatureOfInterest d:cp1 ;
           ens:activeEnergyRegenerated ?kwh ;
           sosa:phenomenonTime/time:hasBeginning/time:inXSDDateTimeStamp ?start .
  FILTER (STR(?start) >= "2026-10-15T00:00:00Z" &&
          STR(?start) < "2026-10-16T00:00:00Z")
}""", [("23.6",)]),
            ("CQ4.2", "What is the net energy (consumed minus regenerated) of each reading of cp1?",
             "Derived value per individual", "ABox",
             """SELECT ?reading ((?in - ?out) AS ?net) WHERE {
  ?reading sosa:hasFeatureOfInterest d:cp1 ;
           ens:activeEnergyConsumed ?in ; ens:activeEnergyRegenerated ?out .
}""", [("r1", "398.5"), ("r2", "371.5"), ("r3", "92.1")]),
            ("CQ4.3", "Is a regenerative brake fitted on the traction unit of train 41234?",
             "Existence via reused term (rc.3 telematics)", "ABox",
             """SELECT ?fitted WHERE {
  ?msg era:operationalTrainNumberIdentifier/era:operationalTrainNumber "41234" ;
       era:trainCompositionJourneySection/era:regenerativeBrake/era:regenerativeBrakeFitted ?fitted .
}""", [("true",)]),
        ],
    },
    {
        "id": "S5", "title": "Position and grid context",
        "story": "As a settlement operator, I want to place each reading on the network, so that I know the country, track and supply system where energy was drawn.",
        "sources": "EN 50463-3 (GPS position); RINF parameters 1.1.1.2.2.1.2 and 1.1.1.2.2.2",
        "cqs": [
            ("CQ5.1", "On which running track and in which country was reading r1 taken?",
             "Selection along a path", "ABox",
             """SELECT ?track ?country WHERE {
  d:r1 ens:readingOnTrack ?track .
  ?track era:inCountry ?country .
}""", [("trackNO", "NOR")]),
            ("CQ5.2", "Which energy supply system and maximum train current applied where reading r3 was taken?",
             "Selection along a path to reused RINF terms", "ABox",
             """SELECT ?supply ?maxCurrent WHERE {
  d:r3 ens:readingOnTrack/era:contactLineSystem ?cls .
  ?cls era:energySupplySystem ?supply ; era:maxTrainCurrent ?maxCurrent .
}""", [("ess15kV", "1000")]),
            ("CQ5.3", "How many readings lack a position?",
             "Counting (data completeness)", "ABox",
             """SELECT (COUNT(?reading) AS ?n) WHERE {
  ?reading a/rdfs:subClassOf* ens:EnergyReading .
  FILTER NOT EXISTS { ?reading geo:hasGeometry ?g . }
}""", [("0",)]),
        ],
    },
    {
        "id": "S6", "title": "Data collecting system",
        "story": "As an IM, I want to know which DCS receives each EMS's data and where it goes next, so that I can demonstrate ENE TSI compliance.",
        "sources": "ENE TSI 4.2.17 and Art. 9(1); AS-03 §5.1 and Table 2",
        "cqs": [
            ("CQ6.1", "Which DCS receives the data of EMS ems1?",
             "Selection: Which [CE1] [OPE] [CE2]?", "ABox",
             """SELECT ?dcs WHERE { ?dcs a ens:DataCollectingSystem ; ens:receivesFrom d:ems1 . }""",
             [("eressDCS",)]),
            ("CQ6.2", "To which exchange function does that DCS forward data?",
             "Selection along a path", "ABox",
             """SELECT ?exchange WHERE {
  ?dcs ens:receivesFrom d:ems1 ; ens:forwardsTo ?exchange .
  ?exchange a ens:ExchangeFunction .
}""", [("erex",)]),
            ("CQ6.3", "Which organisation administers the DCS that receives ems1's data?",
             "Selection through a role", "ABox",
             """SELECT ?org WHERE {
  ?dcs ens:receivesFrom d:ems1 ; ens:operatedBy ?role .
  ?role a ens:DCSAdministratorRole ; era:roleOf ?org .
}""", [("eress",)]),
            ("CQ6.5", "Which classes does the extension declare as subclasses of ssn:System?",
             "Taxonomy (TBox): Which [CE] are subclasses of [CE]?", "TBox",
             """SELECT ?class WHERE {
  ?class rdfs:subClassOf ssn:System ;
         rdfs:isDefinedBy <http://data.europa.eu/dy6/def/energy/> .
}""", [("DataCollectingSystem",), ("DataHandlingSystem",), ("EnergyMeasurementSystem",),
       ("ExchangeFunction",), ("SettlementSystem",)]),
            ("CQ6.4", "Which auditable exchanges delivered composition data to the Norwegian and Swedish infrastructure managers?",
             "Selection over exchange activity", "ABox",
             """SELECT ?org ?outcome WHERE {
  ?exchange a ens:DataExchangeActivity ;
            ens:exchangedMessage d:tcm1 ;
            ens:exchangeRecipient/era:roleOf ?org ;
            ens:exchangeOutcome ?outcome ;
            ens:exchangeAuthority ?authority ;
            ens:retentionPolicy ?retention .
}""", [("baneNor", "received"), ("trafikverket", "received")]),
        ],
    },
    {
        "id": "S7", "title": "Exchange function and cross-border exchange",
        "story": "As Eress, I want to know which settlement systems and foreign exchange functions Erex exchanges with, and over which protocol, so that cross-border trains are settled correctly.",
        "sources": "UIC IRS 90930; AS-03 §5.6.2(c), §5.6.3(a); Sector Declaration 2020",
        "cqs": [
            ("CQ7.1", "Which settlement systems does Erex feed?",
             "Selection", "ABox",
             """SELECT ?settlement WHERE {
  d:erex ens:forwardsTo ?settlement . ?settlement a ens:SettlementSystem .
}""", [("settleNO",), ("settleSE",)]),
            ("CQ7.2", "With which exchange functions does Erex exchange data, and with which protocol?",
             "Selection over a symmetric relation", "ABox",
             """SELECT ?other ?protocol WHERE {
  d:erex ens:exchangesWith|^ens:exchangesWith ?other .
  ?other ens:exchangeProtocol ?protocol .
}""", [("foreignExchange", "IRS90930")]),
            ("CQ7.3", "Which exchange functions still use a legacy protocol?",
             "Selection by value", "ABox",
             """SELECT ?exchange WHERE { ?exchange ens:exchangeProtocol ensc:UTILTS . }""",
             [("legacyExchange",)]),
        ],
    },
    {
        "id": "S8", "title": "Settlement systems and zones",
        "story": "As ERA, I want to see which settlement system covers which zone and country, so that the ENE TSI Art. 9(4) obligation can be monitored per Member State.",
        "sources": "ENE TSI Art. 9(4); AS-03 Figure 4 and Table 4",
        "cqs": [
            ("CQ8.1", "Which zone and country does each settlement system serve?",
             "Selection with several attributes", "ABox",
             """SELECT ?settlement ?zone ?country WHERE {
  ?settlement ens:servesZone ?zone . ?zone ens:zoneCountry ?country .
}""", [("settleNO", "zoneNO", "NOR"), ("settleSE", "zoneSE", "SWE")]),
            ("CQ8.2", "Which settlement system is responsible for energy consumed in Sweden?",
             "Selection by value", "ABox",
             """SELECT ?settlement WHERE {
  ?settlement ens:servesZone/ens:zoneCountry country:SWE .
}""", [("settleSE",)]),
            ("CQ8.3", "Which organisation operates the Norwegian settlement system?",
             "Selection through a role", "ABox",
             """SELECT ?org WHERE {
  ?settlement ens:servesZone/ens:zoneCountry country:NOR ; ens:operatedBy/era:roleOf ?org .
}""", [("baneNor",)]),
        ],
    },
    {
        "id": "S9", "title": "Border points",
        "story": "As an exchange function, I want zones delimited by the same border points as RINF, so that a reading can be allocated to the right side of a border.",
        "sources": "IRS 90930 border point lists; RINF reference border points (era:referenceBorderPoint)",
        "cqs": [
            ("CQ9.1", "Which reference border points delimit the Norwegian zone, and what are their identifiers?",
             "Selection with attribute", "ABox",
             """SELECT ?rbp ?id WHERE { d:zoneNO ens:delimitedBy ?rbp . ?rbp era:borderPointId ?id . }""",
             [("rbpMagnor", "NO-SE-MAG")]),
            ("CQ9.2", "Which operational points refer to border point NO-SE-MAG?",
             "Selection by inverse path", "ABox",
             """SELECT ?op WHERE {
  ?op era:referenceBorderPoint ?rbp . ?rbp era:borderPointId "NO-SE-MAG" .
}""", [("opMagnor",)]),
            ("CQ9.3", "Which pairs of settlement zones are adjacent through a shared border point?",
             "Relation between individuals", "ABox",
             """SELECT ?zone1 ?zone2 WHERE {
  ?zone1 ens:delimitedBy ?rbp . ?zone2 ens:delimitedBy ?rbp .
  FILTER (STR(?zone1) < STR(?zone2))
}""", [("zoneNO", "zoneSE")]),
        ],
    },
    {
        "id": "S10", "title": "Roles (IRS 90930)",
        "story": "As a settlement operator, I want the IRS 90930 roles expressed as ERA organisation roles, so that keepers, consumers and EMS responsibles are identified consistently with EVR.",
        "sources": "UIC IRS 90930 roles; EVR (era:vehicleKeeper); AS-03 §5.4.2 (keeper fallback)",
        "cqs": [
            ("CQ10.1", "Who is the keeper of the traction unit with EVN 918061890013?",
             "Selection through a role (reused EVR term)", "ABox",
             """SELECT ?org WHERE {
  ?vehicle era:vehicleNumber "918061890013" ; era:vehicleKeeper/era:roleOf ?org .
}""", [("railLease",)]),
            ("CQ10.2", "Which IRS 90930 roles specialise era:OrganisationRole?",
             "Taxonomy (TBox): What are the subtypes of [CE1]?", "TBox",
             """SELECT ?role WHERE {
  ?role rdfs:subClassOf era:OrganisationRole .
  FILTER STRSTARTS(STR(?role), "http://data.europa.eu/dy6/def/energy/")
}""", [("DCSAdministratorRole",), ("EMSResponsibleRole",), ("EnergyConsumerRole",), ("SettlementOperatorRole",)]),
            ("CQ10.3", "Which organisation is responsible for EMS ems1?",
             "Selection through a role", "ABox",
             """SELECT ?org WHERE { d:ems1 ens:emsResponsible/era:roleOf ?org . }""",
             [("railLease",)]),
            ("CQ10.4", "Does any current ens: property point to an era:Body rather than to an era:OrganisationRole?",
             "Existence (TBox): Is there a [P] with range [CE]?", "TBox",
             """ASK {
  ?property rdfs:isDefinedBy <http://data.europa.eu/dy6/def/energy/> ;
            rdfs:range era:Body .
  FILTER NOT EXISTS { ?property owl:deprecated true }
}""", [("false",)]),
        ],
    },
    {
        "id": "S11", "title": "Train composition (TEL TSI 2.5.1(16))",
        "story": "As a settlement system, I want the composition message to give me each traction unit's EVN and the train mass in time, so that I can allocate and validate consumption.",
        "sources": "TEL TSI Annex 2.5.1(16); rc.3 telematics module; AS-03 §3.2.1",
        "cqs": [
            ("CQ11.1", "What traction unit EVN and total train mass were declared for train 41234?",
             "Selection with attributes (reused rc.3 terms)", "ABox",
             """SELECT ?loco ?mass WHERE {
  ?msg era:operationalTrainNumberIdentifier/era:operationalTrainNumber "41234" ;
       era:trainCompositionJourneySection ?js .
  ?js era:locoNumber ?loco ;
      era:trainRunningData/era:trainRunningTechData/era:trainWeight ?mass .
}""", [("918061890013", "1450")]),
            ("CQ11.2", "Which registered vehicle is the traction unit of train 41234?",
             "Selection via normalized identifier rule", "ABox",
             """SELECT ?vehicle WHERE {
  ?msg era:operationalTrainNumberIdentifier/era:operationalTrainNumber "41234" ;
       era:trainCompositionJourneySection/ens:tractionUnitVehicle ?vehicle .
}""", [("loco1",)]),
            ("CQ11.3", "Which composition messages were created after the train's evidenced actual departure?",
             "Temporal comparison", "ABox",
             """SELECT ?msg WHERE {
  ?msg a era:TrainCompositionMessage ;
       era:messageHeader/era:messageDateTimeCreated ?sent ;
       ens:aboutRunningTrain/ens:actualDepartureTime ?departure .
  FILTER (?sent > ?departure)
}""", [("tcm2",)]),
        ],
    },
    {
        "id": "S12", "title": "Train running information (TEL TSI 2.5.2(8))",
        "story": "As a settlement system, I want the train's running information, so that I can tell when a train crossed a border and on whose behalf.",
        "sources": "TEL TSI Annex 2.5.2(8); rc.3 telematics module",
        "cqs": [
            ("CQ12.1", "Where and when was train 41234 reported, and which RU was responsible?",
             "Selection with temporal attributes", "ABox",
             """SELECT ?place (SUBSTR(STR(?when), 12, 5) AS ?hhmm) ?ru WHERE {
  ?msg a era:TrainRunningInformationMessage ;
       era:operationalTrainNumberIdentifier/era:operationalTrainNumber "41234" ;
       era:responsibleRU ?ru ;
       era:trainLocationReport ?report .
  ?report era:location/era:primaryLocationName ?place ; era:locationDateTime ?when .
}""", [("Charlottenberg", "08:38", "3801"), ("Kongsvinger", "07:10", "3801"), ("Magnor", "08:30", "3801")]),
            ("CQ12.2", "Which settlement systems received running information for train 41234?",
             "Selection", "ABox",
             """             SELECT DISTINCT ?settlement WHERE {
               ?msg a era:TrainRunningInformationMessage ;
                    era:operationalTrainNumberIdentifier/era:operationalTrainNumber "41234" ;
                    ens:aboutRunningTrain d:run1 .
               ?exchange a ens:DataExchangeActivity ;
                         ens:exchangedMessage ?msg ;
                         ens:exchangePurpose ensc:energySettlement .
               ?settlement ens:exchangeContains ?exchange .
             }""", [("settleNO",), ("settleSE",)]),
            ("CQ12.3", "When did train 41234 pass a border operational point, and which one?",
             "Join of telematics and RINF data", "ABox",
             """SELECT ?op (SUBSTR(STR(?when), 12, 5) AS ?hhmm) WHERE {
  ?msg era:operationalTrainNumberIdentifier/era:operationalTrainNumber "41234" ;
       era:trainLocationReport ?report .
  ?report era:location ?location ; era:locationDateTime ?when .
  ?op era:primaryLocation ?location ; era:referenceBorderPoint ?rbp .
}""", [("opMagnor", "08:30")]),
            ("CQ12.4", "Which organization is identified as the responsible RU on running message tri1, and in which ERA role?",
             "Selection through a role", "ABox",
             """SELECT ?org ?role WHERE {
  d:tri1 ens:responsibleRailwayUndertaking ?ruRole .
  ?ruRole era:roleOf ?org ; era:hasOrganisationRole ?role .
}""",
             [("nordCargo", "RU-3")]),
            ("CQ12.5", "Which railway undertaking operates running train 41234 departing on 15 October 2026, in which ERA role, and under which company code?",
             "Selection through the ERA organisation-role pattern", "ABox",
             """SELECT ?org ?role ?code WHERE {
  ?run ens:runningTrainNumberIdentifier/era:operationalTrainNumber "41234" ;
       ens:departureDate "2026-10-15"^^xsd:date ;
       ens:operatingRailwayUndertaking ?ruRole .
  ?ruRole era:roleOf ?org ;
          era:hasOrganisationRole ?role .
  ?org era:organisationCode ?code .
}""",
             [("nordCargo", "RU-3", "3801")]),
            ("CQ12.6", "Which running trains used operational train number 41234, and on which departure dates?",
             "Selection with temporal attributes (reused identifier)", "ABox",
             """SELECT ?run ?date WHERE {
  ?run ens:runningTrainNumberIdentifier/era:operationalTrainNumber "41234" ;
       ens:departureDate ?date .
}""", [("run1", "2026-10-15"), ("run3", "2026-10-16")]),
            ("CQ12.7", "Under which TAF/TAP path, from which location and at what scheduled time does running train run1 run?",
             "Selection through era:TrainIdent", "ABox",
             """SELECT ?path ?place ?scheduled WHERE {
  d:run1 ens:runningTrainIdent ?ident .
  ?ident era:pathIdent ?path ;
         era:pathDepartureLocation/era:primaryLocationName ?place ;
         era:scheduledDepartureDateTime ?scheduled .
}""", [("PA-NO01-2026-41234", "Alnabru", "2026-10-15T06:00:00+00:00")]),
        ],
    },
    {
        "id": "S13", "title": "Allocation and matching",
        "story": "As an RU, I want to see which of my trains' consumption was allocated to me, in which zone and on which evidence, so that I can check my invoice.",
        "sources": "ENE TSI Art. 9(4) (allocate to correct parties); AS-03 §5.6.2(d)",
        "cqs": [
            ("CQ13.1", "To which consumer and zone is reading r1 allocated?",
             "Selection through a role", "ABox",
             """SELECT ?org ?zone WHERE {
  ?allocation ens:allocatesReading d:r1 ;
              ens:allocatedTo/era:roleOf ?org ; ens:allocatedInZone ?zone .
}""", [("nordCargo", "zoneNO")]),
            ("CQ13.2", "How much metered energy is allocated to Nord Cargo in each settlement zone?",
             "Aggregation grouped by individual", "ABox",
             """SELECT ?zone (SUM(?kwh) AS ?total) WHERE {
  ?allocation ens:allocatedTo/era:roleOf d:nordCargo ;
              ens:allocationStatus ensc:meteredValid ;
              ens:allocatedInZone ?zone ;
                           ens:allocatedActiveEnergyConsumed ?kwh .
} GROUP BY ?zone""", [("zoneNO", "790.5"), ("zoneSE", "95.2")]),
            ("CQ13.3", "Which composition and running information were used for allocation alloc1?",
             "Selection (traceability)", "ABox",
             """SELECT ?composition ?running WHERE {
  d:alloc1 ens:matchedComposition ?composition ; ens:matchedRunningInformation ?running .
}""", [("tcm1", "tri1")]),
            ("CQ13.4", "What consumed, regenerated, and net energy quantities were allocated in each zone?",
             "Selection with explicit settlement quantities", "ABox",
             """SELECT ?zone ?consumed ?regenerated ?net WHERE {
  ?allocation ens:allocatedInZone ?zone ;
              ens:allocatedActiveEnergyConsumed ?consumed ;
              ens:allocatedActiveEnergyRegenerated ?regenerated ;
              ens:allocatedNetActiveEnergy ?net .
}""", [("zoneNO", "790.5", "20.5", "770.0"),
       ("zoneSE", "95.2", "3.1", "92.1"),
       ("zoneNO", "250.0", "0.0", "250.0")]),
        ],
    },
    {
        "id": "S14", "title": "Data quality, estimation and provenance",
        "story": "As a regulatory body, I want to separate metered from estimated billing and trace any allocation back to its meter, so that charges are transparent.",
        "sources": "AS-03 §3.1 and §5.6.2(g); ENE TSI Art. 9(4) (estimate missing data)",
        "cqs": [
            ("CQ14.1", "Which allocations are estimated rather than metered?",
             "Selection by value", "ABox",
             """SELECT ?allocation WHERE { ?allocation ens:allocationStatus ensc:estimated . }""",
             [("alloc3",)]),
            ("CQ14.2", "Which readings have not been allocated to any consumer?",
             "Negation (closed-world check)", "ABox",
             """SELECT ?reading WHERE {
  ?reading a/rdfs:subClassOf* ens:EnergyReading .
  FILTER NOT EXISTS { ?allocation ens:allocatesReading ?reading . }
}""", [("r4",)]),
            ("CQ14.3", "From which EMS does allocation alloc2 ultimately derive?",
             "Provenance path", "ABox",
             """SELECT DISTINCT ?ems WHERE {
  d:alloc2 ens:allocatesReading ?reading .
  ?cebd sosa:hasMember ?reading ; ens:compiledBy ?ems .
}""", [("ems1",)]),
        ],
    },
    {
        "id": "S15", "title": "Conformity with standards and vehicle registers",
        "story": "As ERA or a notified body, I want to see which EN 50463 edition each EMS follows and whether ERATV declares the meter, so that cross-acceptance issues can be spotted.",
        "sources": "EN 50463:2012/2017; ERATV 4.10.12 (era:hasOnboardEnergyMeasurement); AS-03 §5.5–5.6",
        "cqs": [
            ("CQ15.1", "Which EN 50463 edition does each EMS declare?",
             "Selection with label", "ABox",
             """SELECT ?ems ?edition WHERE {
  ?ems ens:emsStandardVersion/skos:prefLabel ?edition .
}""", [("ems1", "EN 50463:2017"), ("ems2", "EN 50463:2012")]),
            ("CQ15.2", "Which vehicles carry an EMS although their type does not declare an energy meter?",
             "Negation across registers (cf. SHACL R4)", "ABox",
             """SELECT ?vehicle WHERE {
  ?ems sosa:isHostedBy ?vehicle . ?vehicle era:vehicleType ?type .
  FILTER NOT EXISTS { ?type era:configDependentParameter/era:hasOnboardEnergyMeasurement true . }
}""", [("loco2",)]),
            ("CQ15.3", "How many EMS lack a declared standard edition?",
             "Counting (completeness)", "ABox",
             """SELECT (COUNT(?ems) AS ?n) WHERE {
  ?ems a ens:EnergyMeasurementSystem .
  FILTER NOT EXISTS { ?ems ens:emsStandardVersion ?v . }
}""", [("0",)]),
        ],
    },
]

# CQs the model cannot answer yet, recorded as open requirements.
GAPS = [
    ("G1", "Was a composition message sent after departure justified by an anomaly?",
     "The draft records a timing assessment, evidence reference, and authority reference, but the cited rule, allowed window, and meaning of a qualifying anomaly have not been verified against the official instrument.",
     "Verify the operative TEL TSI text and message schema with ERA/legal experts; use a controlled outcome vocabulary and evidence mapping without treating a populated link as proof of compliance."),
    ("G2", "What was the train's actual departure time?",
     "ens:actualDepartureTime now distinguishes actual from booked time and requires an evidence reference; no authoritative departure event or interface mapping is validated by the synthetic example.",
     "Map an authoritative operating event and its provenance for each deployment; do not infer departure from the first location report without an approved operational rule."),
    ("G3", "Which energy supplier delivered the allocated energy, and at what price?",
     "Supplier, contract, and price data are outside this iteration and must not be inferred from settlement party or infrastructure operator.",
     "Add a separate market/contract module after verifying the operative legal interface obligations and responsible actors."),
    ("G4", "How were network losses allocated between consumers?",
     "Loss coefficients and their allocation (AS-03 §5.6.2(g), Infrabel 96 % rule) are not modelled.",
     "Add a loss allocation method concept and coefficient to ens:EnergyAllocation."),
    ("G5", "In which unit is the train weight of a composition message expressed?",
     "era:trainWeight (xsd:int) has no era:unitOfMeasure in rc.3.",
     "Raise with ERA (TAF practice: tonnes)."),
    ("G6", "Which legal, privacy, security, and retention controls govern each exchange?",
     "The exchange record now links a purpose, authority reference, recipient, outcome, and retention-policy reference, but example references are explicit placeholders and access controls are external to RDF.",
     "Have the controller/processor roles, legal basis, purpose limitation, recipient authorization, retention/deletion schedule, security controls, and audit needs approved for each deployment."),
]


def short(term):
    if isinstance(term, rdflib.URIRef):
        s = str(term)
        return s.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
    return str(term)


def run(rc3_path=DEFAULT_ERA_ONTOLOGY, skip_dl=False):
    data = rdflib.Graph()
    data.parse(DRAFT)
    data.parse(EXAMPLES)

    ont = rdflib.Graph()
    ont.parse(rc3_path)
    ont.parse(DRAFT)
    conforms, report, _ = pyshacl.validate(
        data, shacl_graph=SHAPES, ont_graph=ont, inference="none",
        advanced=True, allow_warnings=True, inplace=True)
    if not isinstance(report, rdflib.Graph):
        raise RuntimeError(f"SHACL validation could not run: {report}")
    shacl = []
    for r in report.subjects(rdflib.RDF.type, SH.ValidationResult):
        shacl.append((short(report.value(r, SH.resultSeverity)),
                      short(report.value(r, SH.focusNode))))

    results = []
    for cq_set in SETS:
        for cq_id, question, archetype, kind, query, expected in cq_set["cqs"]:
            res = data.query(PREFIXES + query)
            if res.type == "ASK":
                got = [(str(res.askAnswer).lower(),)]
            else:
                got = [tuple(short(v) for v in row) for row in res]
            ok = sorted(got) == sorted(expected)
            results.append((cq_set["id"], cq_id, ok, sorted(got)))
    dl = None if skip_dl else validate_dl(rc3_path)
    return (conforms, sorted(shacl), results,
            validate_allocation_accounting(data),
            validate_negative_cases(data, ont), dl)


def validate_external_terms(rc3_path):
    """Check that every reused sosa:, ssn: and era: term is declared at its source.

    Terms are looked up in the vendored W3C SOSA/SSN/SSN-Ext files and in the
    ERA ontology snapshot (ERA concept schemes and shapes are published
    separately and are not checked). Returns the number of terms checked and
    the undeclared ones.
    """
    sosa, ssn, era = ("http://www.w3.org/ns/sosa/", "http://www.w3.org/ns/ssn/",
                      "http://data.europa.eu/949/")
    w3c = rdflib.Graph()
    for path in dl_check.W3C_VOCABULARIES:
        w3c.parse(path)
    era_graph = rdflib.Graph().parse(rc3_path)
    used = set()
    for path in (DRAFT, SHAPES, EXAMPLES):
        for triple in rdflib.Graph().parse(path):
            used.update(t for t in triple if isinstance(t, rdflib.URIRef))
    checked, missing = 0, []
    for term in sorted(used):
        iri = str(term)
        if iri.startswith((sosa, ssn)):
            source = w3c
        elif iri.startswith(era) and not iri.startswith((era + "concepts/", era + "shapes/")):
            source = era_graph
        else:
            continue
        checked += 1
        if (term, None, None) not in source:
            missing.append(iri)
    return checked, missing


def validate_era_shapes(rc3_path):
    """Validate the examples against ERA's telematics shapes, and one fixture they must reject."""
    shapes = era_shapes_check.load_shapes()
    data = era_shapes_check.data_graph()
    result = era_shapes_check.validate(data, rc3_path, shapes)
    failures = []
    era = rdflib.Namespace("http://data.europa.eu/949/")
    d = rdflib.Namespace("http://example.org/data/")
    no_status = rdflib.Graph()
    for triple in data:
        no_status.add(triple)
    no_status.remove((d.tri1, era.messageStatus, None))
    if era_shapes_check.validate(no_status, rc3_path, shapes).conforms:
        failures.append("ERA shapes accepted a running information message without era:messageStatus")
    return result, failures


def validate_dl(rc3_path):
    """Run HermiT on the merged graph and on two fixtures it must reject."""
    era = rdflib.Namespace("http://data.europa.eu/949/")
    ens = rdflib.Namespace("http://data.europa.eu/dy6/def/energy/")
    d = rdflib.Namespace("http://example.org/data/")
    merged = dl_check.load(dl_check.default_inputs(rc3_path))
    result = dl_check.run_hermit(merged)
    failures = []

    # Two location reports on one message: era:trainLocationReport and
    # era:locationDateTime are functional, so this must be inconsistent.
    second_report = rdflib.Graph()
    for triple in merged:
        second_report.add(triple)
    report = rdflib.BNode()
    second_report.add((d.tri1, era.trainLocationReport, report))
    second_report.add((report, era.locationDateTime,
                       rdflib.Literal("2026-10-15T08:30:00Z", datatype=rdflib.XSD.dateTime)))
    if dl_check.run_hermit(second_report).consistent:
        failures.append("HermiT accepted a running message with two location reports")

    # A class under both era:Body and era:OrganisationRole, which rc.3
    # declares disjoint, must be reported as unsatisfiable.
    unsatisfiable = rdflib.Graph()
    for triple in merged:
        unsatisfiable.add(triple)
    unsatisfiable.add((ens.BodyRoleFixture, rdflib.RDF.type, rdflib.OWL.Class))
    unsatisfiable.add((ens.BodyRoleFixture, rdflib.RDFS.subClassOf, era.Body))
    unsatisfiable.add((ens.BodyRoleFixture, rdflib.RDFS.subClassOf, era.OrganisationRole))
    fixture = dl_check.run_hermit(unsatisfiable)
    if not any("BodyRoleFixture" in c for c in fixture.unsatisfiable):
        failures.append("HermiT did not report a class under two disjoint classes as unsatisfiable")
    return result, failures


def validate_allocation_accounting(data):
    """Check arithmetic that requires aggregation across allocation components."""
    ex = rdflib.Namespace("http://data.europa.eu/dy6/def/energy/")
    exc = rdflib.Namespace("http://data.europa.eu/dy6/def/energy/concepts/")
    issues = []
    allocated_by_reading = defaultdict(lambda: [Decimal(0), Decimal(0)])

    for allocation in data.subjects(rdflib.RDF.type, ex.EnergyAllocation):
        components = list(data.objects(allocation, ex.hasAllocationComponent))
        for property_, allocation_property in (
            (ex.componentActiveEnergyConsumed, ex.allocatedActiveEnergyConsumed),
            (ex.componentActiveEnergyRegenerated, ex.allocatedActiveEnergyRegenerated),
            (ex.componentNetActiveEnergy, ex.allocatedNetActiveEnergy),
        ):
            component_total = sum(
                (Decimal(str(value)) for component in components
                 for value in data.objects(component, property_)),
                Decimal(0),
            )
            declared = [Decimal(str(value)) for value in data.objects(allocation, allocation_property)]
            if len(declared) != 1 or component_total != declared[0]:
                issues.append(f"{allocation}: allocation total does not equal component total for {property_}")

        for component in components:
            reading = data.value(component, ex.componentReading)
            if reading is not None:
                for prop, index in (
                    (ex.componentActiveEnergyConsumed, 0),
                    (ex.componentActiveEnergyRegenerated, 1),
                ):
                    amount = data.value(component, prop)
                    if amount is not None:
                        allocated_by_reading[reading][index] += Decimal(str(amount))
        if (data.value(allocation, ex.allocationStatus) == exc.meteredValid
                and set(data.objects(allocation, ex.allocatesReading))
                != {data.value(component, ex.componentReading) for component in components
                    if data.value(component, ex.componentReading) is not None}):
            issues.append(f"{allocation}: cited readings differ from component source readings")

    for reading, (consumed, regenerated) in allocated_by_reading.items():
        source_consumed = data.value(reading, ex.activeEnergyConsumed)
        source_regenerated = data.value(reading, ex.activeEnergyRegenerated)
        if source_consumed is not None and consumed > Decimal(str(source_consumed)):
            issues.append(f"{reading}: allocated consumption exceeds measured consumption")
        if source_regenerated is not None and regenerated > Decimal(str(source_regenerated)):
            issues.append(f"{reading}: allocated regeneration exceeds measured regeneration")
    return issues


def validate_negative_cases(data, ont):
    """Prove the main identity and allocation constraints reject bad fixtures."""
    ex = rdflib.Namespace("http://data.europa.eu/dy6/def/energy/")
    d = rdflib.Namespace("http://example.org/data/")
    failures = []

    bad_identity = rdflib.Graph()
    for triple in data:
        bad_identity.add(triple)
    old_ids = list(bad_identity.objects(d.cp1, ex.consumptionPointId))
    for value in old_ids:
        bad_identity.remove((d.cp1, ex.consumptionPointId, value))
    bad_identity.add((d.cp1, ex.consumptionPointId, rdflib.Literal("918061890014")))
    identity_conforms, identity_report, _ = pyshacl.validate(
        bad_identity, shacl_graph=SHAPES, ont_graph=ont, inference="none",
        advanced=True, allow_warnings=True, inplace=True)
    if identity_conforms or not isinstance(identity_report, rdflib.Graph):
        failures.append("SHACL accepted a consumption-point EVN that differs from its vehicle")

    bad_allocation = rdflib.Graph()
    for triple in data:
        bad_allocation.add(triple)
    sosa = rdflib.Namespace("http://www.w3.org/ns/sosa/")
    qudt = rdflib.Namespace("http://qudt.org/schema/qudt/")
    consumed_result = bad_allocation.value(d["r1-consumed"], sosa.hasResult)
    bad_allocation.remove((consumed_result, qudt.numericValue, None))
    bad_allocation.add((consumed_result, qudt.numericValue, rdflib.Literal("400.0", datatype=rdflib.XSD.decimal)))
    bad_allocation.remove((d.r1, ex.activeEnergyConsumed, None))
    allocation_conforms, allocation_report, _ = pyshacl.validate(
        bad_allocation, shacl_graph=SHAPES, ont_graph=ont, inference="none",
        advanced=True, allow_warnings=True, inplace=True)
    accounting_issues = validate_allocation_accounting(bad_allocation)
    if allocation_conforms and not accounting_issues:
        failures.append("Validation accepted allocation components exceeding the source reading")
    if not isinstance(allocation_report, rdflib.Graph):
        failures.append(f"SHACL allocation negative test could not run: {allocation_report}")

    bad_forwarding = rdflib.Graph()
    for triple in data:
        bad_forwarding.add(triple)
    bad_forwarding.add((d.eressDCS, ex.forwardsTo, d.settleNO))
    forwarding_conforms, _, _ = pyshacl.validate(
        bad_forwarding, shacl_graph=SHAPES, ont_graph=ont, inference="none",
        advanced=True, allow_warnings=True, inplace=True)
    if forwarding_conforms:
        failures.append("SHACL accepted a DCS forwarding directly to a settlement system")

    bad_ems = rdflib.Graph()
    for triple in data:
        bad_ems.add(triple)
    bad_ems.remove((d.ems1, rdflib.URIRef("http://www.w3.org/ns/sosa/isHostedBy"), None))
    ems_conforms, _, _ = pyshacl.validate(
        bad_ems, shacl_graph=SHAPES, ont_graph=ont, inference="none",
        advanced=True, allow_warnings=True, inplace=True)
    if ems_conforms:
        failures.append("SHACL accepted an EMS that is not installed on a vehicle")

    org_roles = rdflib.Namespace("http://data.europa.eu/949/concepts/organisation-roles/")
    era = rdflib.Namespace("http://data.europa.eu/949/")
    bad_ru_cases = {
        "an operating RU role typed as vehicle keeper": (
            [(d.nordCargoRU, era.hasOrganisationRole, None)],
            [(d.nordCargoRU, era.hasOrganisationRole, org_roles.Keeper)]),
        "two running trains with the same train number and departure date": (
            [(d.run3, ex.departureDate, None)],
            [(d.run3, ex.departureDate, rdflib.Literal("2026-10-15", datatype=rdflib.XSD.date))]),
    }
    unit_ns = rdflib.Namespace("http://qudt.org/vocab/unit/")
    regenerated_result = data.value(d["r1-regenerated"], sosa.hasResult)
    bad_ru_cases["an active energy result in kvarh"] = (
        [(regenerated_result, qudt.unit, None)],
        [(regenerated_result, qudt.unit, unit_ns["KiloVAR-HR"])])
    bad_ru_cases["a reading without a consumed active energy observation"] = (
        [(d.r2, sosa.hasMember, d["r2-consumed"])], [])
    bad_ru_cases["an exchange sender given as a body instead of a role"] = (
        [(d.exchangeTcm1NO, ex.exchangeSender, None)],
        [(d.exchangeTcm1NO, ex.exchangeSender, d.baneNor)])
    bad_ru_cases["an exchange recipient role that does not operate the receiving system"] = (
        [(d.exchangeTcm1NO, ex.exchangeRecipient, None)],
        [(d.exchangeTcm1NO, ex.exchangeRecipient, d.settleOpSE)])
    bad_ru_cases["an organisation role without a body"] = (
        [(d.imNO, era.roleOf, None)], [])
    bad_ru_cases["a responsible RU role whose body has another code"] = (
        [(d.tri1, era.responsibleRU, None)],
        [(d.tri1, era.responsibleRU, rdflib.Literal("9999"))])
    for label, (removed, added) in bad_ru_cases.items():
        bad_ru = rdflib.Graph()
        for triple in data:
            bad_ru.add(triple)
        for pattern in removed:
            bad_ru.remove(pattern)
        for triple in added:
            bad_ru.add(triple)
        ru_conforms, _, _ = pyshacl.validate(
            bad_ru, shacl_graph=SHAPES, ont_graph=ont, inference="none",
            advanced=True, allow_warnings=True, inplace=True)
        if ru_conforms:
            failures.append(f"SHACL accepted {label}")
    return failures


def render(conforms, shacl, results, accounting_issues, md_path, dl=None, external=None, era=None):
    by_id = {cq_id: (ok, got) for _, cq_id, ok, got in results}
    passed = sum(1 for r in results if r[2])
    out = []
    w = out.append
    w("# Competency questions – ERA energy settlement extension\n")
    w("Validation of the ontology draft **v0.9** (`era-energy-settlement-draft.ttl`) and its shapes "
      "against **ERA ontology v4.0.0-rc.3**, following the LOT methodology.\n")
    w(f"**Result: {passed} of {len(results)} competency questions pass.** "
      f"SHACL conforms: **{conforms}**; allocation arithmetic issues: **{len(accounting_issues)}**; "
      f"SHACL results: **{len(shacl)}**.\n")
    if dl is None:
        w("OWL 2 DL check (HermiT): **skipped**.\n")
    else:
        dl_result, dl_failures = dl
        w(f"OWL 2 DL check (HermiT): consistent **{dl_result.consistent}**; unsatisfiable classes: "
          f"**{len(dl_result.unsatisfiable)}**; DL negative tests: **{'passed' if not dl_failures else 'failed'}**.\n")
    if era is not None:
        era_result, era_failures = era
        w(f"ERA telematics shapes (v4.0.0-rc.3): conforms **{era_result.conforms}**; results: "
          f"**{len(era_result.results)}**; negative test: **{'passed' if not era_failures else 'failed'}**.\n")
    if external is not None:
        checked, missing = external
        w(f"Reused sosa:, ssn: and era: terms declared at their source: **{checked - len(missing)} of {checked}**.\n")
    w("Generated by `cq_suite.py`, which runs every CQ as a SPARQL query over the draft plus "
      "`era-energy-settlement-examples.ttl`. Re-run it after any change to the ontology.\n")

    w("## 1. Method\n")
    w("The CQs were produced and validated with current practice in ontology requirements engineering:\n")
    w("- **LOT methodology** (Poveda-Villalón et al., 2022). Requirements specification "
      "produces functional requirements as CQs grouped by theme, each traced to its source. Validation turns each CQ "
      "into a test run against the implemented ontology, and failing CQs feed the next iteration.")
    w("- **Competency questions** (Grüninger and Fox, 1995) written from the documents LOT treats as domain sources: "
      "the ERA AS-03 study, TEL TSI Annex 2.5.1(16) and 2.5.2(8), ENE TSI Art. 9, EN 50463 and UIC IRS 90930.")
    w("- **User stories per set.** Each set starts from a stakeholder need (IM, RU, settlement operator, Eress, ERA, "
      "regulatory body), as LOT recommends for collaborative requirement elicitation.")
    w("- **CQ archetypes** (Ren et al., 2014) and the **CLaRO** controlled language (Keet et al., 2019). Every CQ is "
      "tagged with its pattern (selection, counting, aggregation, existence, taxonomy, negation, temporal), which "
      "shows the requirement types are balanced.")
    w("- **CQs as executable tests.** Each CQ is translated into SPARQL with an expected answer, as in the "
      "CQ-to-SPARQL-OWL dataset (Potoniec et al., 2020). TBox CQs play the role of Themis-style requirement tests "
      "(Fernández-Izquierdo and García-Castro, 2019) checking axioms; ABox CQs check the model answers real questions "
      "over example data.")
    w("- **SHACL** checks normalized EVN matching, measurement periods, allocation structure, run/message identity, "
      "exchange evidence fields, and evidence requirements for late composition messages. Python aggregation checks "
      "allocation-component totals and that components do not over-allocate source readings.")
    w("- **LLM-assisted drafting with expert review.** The CQs were drafted with an LLM, an approach studied in "
      "OntoChat (Zhang et al., 2024). They need review by domain experts (Eress, Bane NOR) before the requirements "
      "are frozen.\n")

    w("### Scope (ORSD summary)\n")
    w("| Item | Content |")
    w("|---|---|")
    w("| Purpose | Represent traction energy measurement, exchange and settlement data, linked to ERA registers and TEL TSI messages |")
    w("| Scope | EMS to CEBD to DCS to exchange function to settlement system to allocation; matching with composition and running information; borders and grid context |")
    w("| Out of scope (this iteration) | Energy market and supply contracts, prices, network losses (see section 4) |")
    w("| Implementation | OWL 2 (RDFS-level axioms) and SHACL, `ens:` extension of `era:` v4.0.0-rc.3, reusing SOSA/SSN, SAREF, QUDT, PROV-O, OWL-Time, GeoSPARQL |")
    w("| Intended users | Eress partner IMs, settlement operators, RUs, ERA, regulatory bodies |")
    w("| Intended uses | Cross-border allocation support, evidence-oriented ENE TSI review, settlement reconciliation, EMS cross-acceptance analysis |\n")

    w("## 2. Summary\n")
    w("| Set | Theme | CQs | Passed |")
    w("|---|---|---|---|")
    for cq_set in SETS:
        ids = [c[0] for c in cq_set["cqs"]]
        n_ok = sum(1 for i in ids if by_id[i][0])
        w(f"| {cq_set['id']} | {cq_set['title']} | {', '.join(ids)} | {n_ok}/{len(ids)} |")
    w("")

    w("## 3. Competency question sets\n")
    for cq_set in SETS:
        w(f"### {cq_set['id']}. {cq_set['title']}\n")
        w(f"**User story:** {cq_set['story']}\n")
        w(f"**Sources:** {cq_set['sources']}\n")
        for cq_id, question, archetype, kind, query, expected in cq_set["cqs"]:
            ok, got = by_id[cq_id]
            status = "PASS" if ok else "FAIL"
            w(f"#### {cq_id} – {question}\n")
            w(f"- Archetype: {archetype}")
            w(f"- Type: {kind}")
            w(f"- Expected: {'; '.join(', '.join(t) for t in sorted(expected))}")
            w(f"- Result: {'; '.join(', '.join(t) for t in got) or '(none)'} → **{status}**\n")
            w("```sparql")
            w(query)
            w("```\n")

    w("## 4. Open requirements and unverified claims\n")
    w("These questions have not been settled by this proposal. Some now have model fields, but cannot be answered "
      "reliably for an operational or legal case without authoritative source data and expert-verified rules.\n")
    w("| ID | Competency question | Why it fails | Proposed action |")
    w("|---|---|---|---|")
    for gid, q, why, action in GAPS:
        w(f"| {gid} | {q} | {why} | {action} |")
    w("")
    w("This list distinguishes data-model coverage from evidence quality: a populated evidence link is not proof that "
      "a legal condition is satisfied. Outstanding items need authoritative source or deployment decisions before "
      "production settlement use.\n")

    w("## 5. Notes on the tests\n")
    w("- **CQs run without a reasoner.** Subclass and subproperty entailments are written as property paths "
      "(`rdf:type/rdfs:subClassOf*`, `rdfs:subPropertyOf*`). CQ7.2 uses `ens:exchangesWith|^ens:exchangesWith` because "
      "the symmetry of the property is only entailed by a reasoner.")
    w("- **OWL 2 DL consistency is checked with HermiT** (`dl_check.py`) on the ERA snapshot, the extension, the "
      "examples and the vendored W3C SOSA, SSN and SSN-Ext files. Two fixtures prove that it detects an inconsistent "
      "ABox (two location reports on one running message, against the functional `era:trainLocationReport`) and an "
      "unsatisfiable class (a subclass of the disjoint `era:Body` and `era:OrganisationRole`).")
    if dl is not None and dl[0].adjustments:
        w("  Inputs adjusted for OWL 2 DL before reasoning: " + "; ".join(dl[0].adjustments) + ". "
          "HermiT runs with `--ignoreUnsupportedDatatypes` because `xsd:date` is outside the OWL 2 datatype map.")
    w("- **CQ11.2 depends on a SHACL rule.** The link from the composition journey section's normalized `era:locoNumber` "
      "to a registered vehicle is derived only when it matches a valid 12-digit vehicle number.")
    w("- **Readings are SOSA observation collections.** The source data states each energy value as a member "
      "`sosa:Observation` with a QUDT result. The compact `ens:activeEnergyConsumed`, `ens:activeEnergyRegenerated` "
      "and `ens:reactiveEnergy` values used by the S3, S4 and S13 questions are derived from those observations by "
      "the `enssh:EnergyReadingShape` rule.")
    w("- **Allocation arithmetic checks** verify component totals and cap aggregate component values at each source "
      "reading. The energy quantities are not prices and do not define market, contract, tax, or network-loss treatment.")
    w("- **Legal and privacy caveat:** exchange authority and retention references in examples are placeholders. "
      "The shapes validate reference presence, not legal validity, a GDPR basis, controller/processor allocation, "
      "access control, or retention compliance.")
    w("- **Example data is illustrative.** Organisation names are real; EVNs, train numbers, energy values, the "
      "border point ID and the energy supply concept are not.")
    w("- **To re-run:** `python3 cq_suite.py --md era-energy-settlement-cqs.md` "
      "(uses the vendored ERA ontology snapshot; needs the packages in `requirements.txt`).\n")

    w("## References\n")
    w("- Fernández-Izquierdo, A., García-Castro, R. (2019). Themis: a tool for validating ontologies through requirements. SEKE 2019.")
    w("- Grüninger, M., Fox, M. S. (1995). Methodology for the design and evaluation of ontologies. IJCAI Workshop on Basic Ontological Issues in Knowledge Sharing.")
    w("- Keet, C. M., Mahlaza, Z., Antia, M.-J. (2019). CLaRO: a controlled language for authoring competency questions. MTSR 2019.")
    w("- Potoniec, J., Wiśniewski, D., Ławrynowicz, A., Keet, C. M. (2020). Dataset of ontology competency questions to SPARQL-OWL queries translations. Data in Brief 29.")
    w("- Poveda-Villalón, M., Fernández-Izquierdo, A., Fernández-López, M., García-Castro, R. (2022). LOT: An industrial oriented ontology engineering framework. Engineering Applications of Artificial Intelligence 111.")
    w("- Ren, Y., Parvizi, A., Mellish, C., Pan, J. Z., van Deemter, K., Stevens, R. (2014). Towards competency question-driven ontology authoring. ESWC 2014.")
    w("- Zhang, B., et al. (2024). OntoChat: a framework for conversational ontology engineering using language models. ESWC 2024 Satellite Events.")
    w("- European Union Agency for Railways (2026). Study on the implementation of on-ground energy data collecting systems in the EU railway system (AS-03).")
    w("- Commission Implementing Regulation (EU) 2026/253 (TEL TSI), Annex 2.5.1(16) and 2.5.2(8).")

    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rc3", nargs="?", default=DEFAULT_ERA_ONTOLOGY,
                    help=f"ERA ontology Turtle file (default: {DEFAULT_ERA_ONTOLOGY})")
    ap.add_argument("--md")
    ap.add_argument("--skip-dl", action="store_true", help="skip the HermiT OWL 2 DL consistency check")
    args = ap.parse_args()
    conforms, shacl, results, accounting_issues, negative_failures, dl = run(args.rc3, args.skip_dl)
    print(f"SHACL conforms: {conforms}; results: {shacl}")
    for set_id, cq_id, ok, got in results:
        print(f"{'PASS' if ok else 'FAIL'} {cq_id:<7} {got}")
    print(f"{sum(r[2] for r in results)}/{len(results)} passed")
    if accounting_issues:
        for issue in accounting_issues:
            print("FAIL allocation accounting:", issue)
    else:
        print("Allocation component accounting: passed")
    if negative_failures:
        for failure in negative_failures:
            print("FAIL negative constraint test:", failure)
    else:
        print("Negative constraint tests: passed")
    era = validate_era_shapes(args.rc3)
    era_result, era_failures = era
    for adjustment in era_result.adjustments:
        print("ERA shapes adjusted:", adjustment)
    for focus, path_, message in era_result.results:
        print(f"FAIL ERA shapes: {focus} {path_}: {message}")
    for failure in era_failures:
        print("FAIL ERA shapes negative test:", failure)
    print(f"ERA telematics shapes: conforms={era_result.conforms}; results: {len(era_result.results)}")
    era_ok = era_result.conforms and not era_failures
    external = validate_external_terms(args.rc3)
    checked, missing = external
    for iri in missing:
        print("FAIL undeclared reused term:", iri)
    print(f"Reused sosa:, ssn: and era: terms declared at their source: {checked - len(missing)}/{checked}")
    dl_ok = True
    if dl is None:
        print("OWL 2 DL check (HermiT): skipped")
    else:
        result, dl_failures = dl
        for adjustment in result.adjustments:
            print("DL input adjusted:", adjustment)
        if result.error:
            print("FAIL HermiT error:", result.error)
        print(f"OWL 2 DL check (HermiT): consistent={result.consistent}; "
              f"unsatisfiable classes: {result.unsatisfiable or 'none'}")
        for failure in dl_failures:
            print("FAIL DL negative test:", failure)
        if not dl_failures:
            print("DL negative tests: passed")
        dl_ok = result.consistent and not result.unsatisfiable and not dl_failures
    if args.md:
        render(conforms, shacl, results, accounting_issues, args.md, dl, external, era)
        print("wrote", args.md)
    sys.exit(0 if all(r[2] for r in results) and conforms and dl_ok and era_ok and not missing
             and not accounting_issues and not negative_failures else 1)


if __name__ == "__main__":
    main()
