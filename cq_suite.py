"""Competency question test suite for the ERA energy settlement extension.

Each competency question (CQ) is an executable SPARQL query with an
expected answer, so the CQs act as acceptance tests (LOT validation).

Usage:
    python3 cq_suite.py [era-ontology-v4.0.0-rc.3.ttl] [--md era-energy-settlement-cqs.md]

Steps:
  1. Load the ontology draft and the example data.
  2. Run the SHACL shapes against the pinned ERA ontology snapshot: this
     checks the examples and derives ex:tractionUnitVehicle.
  3. Run every CQ and compare with its expected answer.
  4. Optionally render the Markdown report.
"""
import argparse
import sys
from collections import defaultdict
from decimal import Decimal

import pyshacl
import rdflib
from rdflib.namespace import SH

DRAFT = "era-energy-settlement-draft.ttl"
SHAPES = "era-energy-settlement-shapes.ttl"
EXAMPLES = "era-energy-settlement-examples.ttl"
DEFAULT_ERA_ONTOLOGY = "era-ontology-v4.0.0-rc.3.ttl"

PREFIXES = """
PREFIX ex:      <http://example.org/era-energy#>
PREFIX exc:     <http://example.org/era-energy/concepts/>
PREFIX era:     <http://data.europa.eu/949/>
PREFIX d:       <http://example.org/data/>
PREFIX rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos:    <http://www.w3.org/2004/02/skos/core#>
PREFIX time:    <http://www.w3.org/2006/time#>
PREFIX geo:     <http://www.opengis.net/ont/geosparql#>
PREFIX xsd:     <http://www.w3.org/2001/XMLSchema#>
PREFIX sosa:    <http://www.w3.org/ns/sosa/>
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
  ?ems ex:installedOn ?vehicle .
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
  ex:EnergyMeasurementSystem rdfs:subClassOf saref:Meter , sosa:Platform .
}""", [("true",)]),
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
  d:ems1 ex:measuresConsumptionPoint ?cp .
  ?cp ex:consumptionPointId ?id .
}""", [("cp1", "918061890013")]),
            ("CQ2.2", "Which registered vehicle does the consumption point identifier '91 80 6189 001-3' designate?",
             "Selection with value matching", "ABox",
             """SELECT ?vehicle WHERE {
  ?cp ex:consumptionPointOf ?vehicle .
  ?cp ex:consumptionPointId ?id .
  ?vehicle era:vehicleNumber ?evn .
  FILTER (REPLACE(STR(?id), "[ -]", "") = REPLACE("91 80 6189 001-3", "[ -]", ""))
  FILTER (REPLACE(STR(?evn), "[ -]", "") = REPLACE(STR(?id), "[ -]", ""))
}""", [("loco1",)]),
            ("CQ2.3", "How many consumption points have an identifier different from their vehicle's EVN?",
             "Counting: How many [CE1] [OPE] [CE2]?", "ABox",
             """SELECT (COUNT(?cp) AS ?n) WHERE {
  ?cp ex:consumptionPointId ?id ; ex:consumptionPointOf/era:vehicleNumber ?evn .
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
  d:cebd1 ex:hasReading ?reading .
  ?reading ex:readingPeriod/time:hasBeginning/time:inXSDDateTimeStamp ?start .
}""", [("r1", "06:00"), ("r2", "06:05"), ("r3", "08:40")]),
            ("CQ3.2", "What is the total active energy consumed by consumption point cp1 during UTC day 15 October 2026?",
             "Aggregation over a time window", "ABox",
             """SELECT (SUM(?kwh) AS ?total) WHERE {
  ?reading ex:readingOfConsumptionPoint d:cp1 ;
           ex:activeEnergyConsumed ?kwh ;
           ex:readingPeriod/time:hasBeginning/time:inXSDDateTimeStamp ?start ;
           ex:readingPeriod/time:hasEnd/time:inXSDDateTimeStamp ?end .
  FILTER (STR(?start) >= "2026-10-15T00:00:00Z" &&
          STR(?start) < "2026-10-16T00:00:00Z")
}""", [("885.7",)]),
            ("CQ3.3", "Which readings are one-minute reading blocks?",
             "Selection by subtype", "ABox",
             """SELECT ?reading WHERE { ?reading a ex:ReadingBlock . }""", [("r3",)]),
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
  ?reading ex:readingOfConsumptionPoint d:cp1 ;
           ex:activeEnergyRegenerated ?kwh ;
           ex:readingPeriod/time:hasBeginning/time:inXSDDateTimeStamp ?start .
  FILTER (STR(?start) >= "2026-10-15T00:00:00Z" &&
          STR(?start) < "2026-10-16T00:00:00Z")
}""", [("23.6",)]),
            ("CQ4.2", "What is the net energy (consumed minus regenerated) of each reading of cp1?",
             "Derived value per individual", "ABox",
             """SELECT ?reading ((?in - ?out) AS ?net) WHERE {
  ?reading ex:readingOfConsumptionPoint d:cp1 ;
           ex:activeEnergyConsumed ?in ; ex:activeEnergyRegenerated ?out .
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
  d:r1 ex:readingOnTrack ?track .
  ?track era:inCountry ?country .
}""", [("trackNO", "NOR")]),
            ("CQ5.2", "Which energy supply system and maximum train current applied where reading r3 was taken?",
             "Selection along a path to reused RINF terms", "ABox",
             """SELECT ?supply ?maxCurrent WHERE {
  d:r3 ex:readingOnTrack/era:contactLineSystem ?cls .
  ?cls era:energySupplySystem ?supply ; era:maxTrainCurrent ?maxCurrent .
}""", [("ess15kV", "1000")]),
            ("CQ5.3", "How many readings lack a position?",
             "Counting (data completeness)", "ABox",
             """SELECT (COUNT(?reading) AS ?n) WHERE {
  ?reading a/rdfs:subClassOf* ex:EnergyReading .
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
             """SELECT ?dcs WHERE { ?dcs a ex:DataCollectingSystem ; ex:receivesFrom d:ems1 . }""",
             [("eressDCS",)]),
            ("CQ6.2", "To which exchange function does that DCS forward data?",
             "Selection along a path", "ABox",
             """SELECT ?exchange WHERE {
  ?dcs ex:receivesFrom d:ems1 ; ex:forwardsTo ?exchange .
  ?exchange a ex:ExchangeFunction .
}""", [("erex",)]),
            ("CQ6.3", "Which organisation administers the DCS that receives ems1's data?",
             "Selection through a role", "ABox",
             """SELECT ?org WHERE {
  ?dcs ex:receivesFrom d:ems1 ; ex:operatedBy ?role .
  ?role a ex:DCSAdministratorRole ; era:roleOf ?org .
}""", [("eress",)]),
            ("CQ6.4", "Which auditable exchanges delivered composition data to the Norwegian and Swedish infrastructure managers?",
             "Selection over exchange activity", "ABox",
             """SELECT ?recipient ?outcome WHERE {
  ?exchange a ex:DataExchangeActivity ;
            ex:exchangedMessage d:tcm1 ;
            ex:exchangeRecipient ?recipient ;
            ex:exchangeOutcome ?outcome ;
            ex:exchangeAuthority ?authority ;
            ex:retentionPolicy ?retention .
}""", [("settleNO", "received"), ("settleSE", "received")]),
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
  d:erex ex:forwardsTo ?settlement . ?settlement a ex:SettlementSystem .
}""", [("settleNO",), ("settleSE",)]),
            ("CQ7.2", "With which exchange functions does Erex exchange data, and with which protocol?",
             "Selection over a symmetric relation", "ABox",
             """SELECT ?other ?protocol WHERE {
  d:erex ex:exchangesWith|^ex:exchangesWith ?other .
  ?other ex:exchangeProtocol ?protocol .
}""", [("foreignExchange", "IRS90930")]),
            ("CQ7.3", "Which exchange functions still use a legacy protocol?",
             "Selection by value", "ABox",
             """SELECT ?exchange WHERE { ?exchange ex:exchangeProtocol exc:UTILTS . }""",
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
  ?settlement ex:servesZone ?zone . ?zone ex:zoneCountry ?country .
}""", [("settleNO", "zoneNO", "NOR"), ("settleSE", "zoneSE", "SWE")]),
            ("CQ8.2", "Which settlement system is responsible for energy consumed in Sweden?",
             "Selection by value", "ABox",
             """SELECT ?settlement WHERE {
  ?settlement ex:servesZone/ex:zoneCountry country:SWE .
}""", [("settleSE",)]),
            ("CQ8.3", "Which organisation operates the Norwegian settlement system?",
             "Selection through a role", "ABox",
             """SELECT ?org WHERE {
  ?settlement ex:servesZone/ex:zoneCountry country:NOR ; ex:operatedBy/era:roleOf ?org .
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
             """SELECT ?rbp ?id WHERE { d:zoneNO ex:delimitedBy ?rbp . ?rbp era:borderPointId ?id . }""",
             [("rbpMagnor", "NO-SE-MAG")]),
            ("CQ9.2", "Which operational points refer to border point NO-SE-MAG?",
             "Selection by inverse path", "ABox",
             """SELECT ?op WHERE {
  ?op era:referenceBorderPoint ?rbp . ?rbp era:borderPointId "NO-SE-MAG" .
}""", [("opMagnor",)]),
            ("CQ9.3", "Which pairs of settlement zones are adjacent through a shared border point?",
             "Relation between individuals", "ABox",
             """SELECT ?zone1 ?zone2 WHERE {
  ?zone1 ex:delimitedBy ?rbp . ?zone2 ex:delimitedBy ?rbp .
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
  FILTER STRSTARTS(STR(?role), "http://example.org/era-energy#")
}""", [("DCSAdministratorRole",), ("EMSResponsibleRole",), ("EnergyConsumerRole",), ("SettlementOperatorRole",)]),
            ("CQ10.3", "Which organisation is responsible for EMS ems1?",
             "Selection through a role", "ABox",
             """SELECT ?org WHERE { d:ems1 ex:emsResponsible/era:roleOf ?org . }""",
             [("railLease",)]),
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
}""", [("91 80 6189 001-3", "1450")]),
            ("CQ11.2", "Which registered vehicle is the traction unit of train 41234?",
             "Selection via normalized identifier rule", "ABox",
             """SELECT ?vehicle WHERE {
  ?msg era:operationalTrainNumberIdentifier/era:operationalTrainNumber "41234" ;
       era:trainCompositionJourneySection/ex:tractionUnitVehicle ?vehicle .
}""", [("loco1",)]),
            ("CQ11.3", "Which composition messages were created after the train's evidenced actual departure?",
             "Temporal comparison", "ABox",
             """SELECT ?msg WHERE {
  ?msg era:messageHeader/era:messageDateTimeCreated ?sent ;
       ex:aboutTrainRun/ex:actualDepartureTime ?departure .
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
                    ex:aboutTrainRun d:run1 .
               ?exchange a ex:DataExchangeActivity ;
                         ex:exchangedMessage ?msg ;
                         ex:exchangeRecipient ?settlement ;
                         ex:exchangePurpose exc:energySettlement .
             }""", [("settleNO",), ("settleSE",)]),
            ("CQ12.3", "When did train 41234 pass a border operational point, and which one?",
             "Join of telematics and RINF data", "ABox",
             """SELECT ?op (SUBSTR(STR(?when), 12, 5) AS ?hhmm) WHERE {
  ?msg era:operationalTrainNumberIdentifier/era:operationalTrainNumber "41234" ;
       era:trainLocationReport ?report .
  ?report era:location ?location ; era:locationDateTime ?when .
  ?op era:primaryLocation ?location ; era:referenceBorderPoint ?rbp .
}""", [("opMagnor", "08:30")]),
            ("CQ12.4", "Which organization is identified as the responsible RU on running message tri1?",
             "Selection through the resolved organization link", "ABox",
             """SELECT ?org WHERE { d:tri1 ex:responsibleRUOrganisation ?org . }""",
             [("nordCargo",)]),
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
  ?allocation ex:allocatesReading d:r1 ;
              ex:allocatedTo/era:roleOf ?org ; ex:allocatedInZone ?zone .
}""", [("nordCargo", "zoneNO")]),
            ("CQ13.2", "How much metered energy is allocated to Nord Cargo in each settlement zone?",
             "Aggregation grouped by individual", "ABox",
             """SELECT ?zone (SUM(?kwh) AS ?total) WHERE {
  ?allocation ex:allocatedTo/era:roleOf d:nordCargo ;
              ex:allocationStatus exc:meteredValid ;
              ex:allocatedInZone ?zone ;
                           ex:allocatedActiveEnergyConsumed ?kwh .
} GROUP BY ?zone""", [("zoneNO", "790.5"), ("zoneSE", "95.2")]),
            ("CQ13.3", "Which composition and running information were used for allocation alloc1?",
             "Selection (traceability)", "ABox",
             """SELECT ?composition ?running WHERE {
  d:alloc1 ex:matchedComposition ?composition ; ex:matchedRunningInformation ?running .
}""", [("tcm1", "tri1")]),
            ("CQ13.4", "What consumed, regenerated, and net energy quantities were allocated in each zone?",
             "Selection with explicit settlement quantities", "ABox",
             """SELECT ?zone ?consumed ?regenerated ?net WHERE {
  ?allocation ex:allocatedInZone ?zone ;
              ex:allocatedActiveEnergyConsumed ?consumed ;
              ex:allocatedActiveEnergyRegenerated ?regenerated ;
              ex:allocatedNetActiveEnergy ?net .
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
             """SELECT ?allocation WHERE { ?allocation ex:allocationStatus exc:estimated . }""",
             [("alloc3",)]),
            ("CQ14.2", "Which readings have not been allocated to any consumer?",
             "Negation (closed-world check)", "ABox",
             """SELECT ?reading WHERE {
  ?reading a/rdfs:subClassOf* ex:EnergyReading .
  FILTER NOT EXISTS { ?allocation ex:allocatesReading ?reading . }
}""", [("r4",)]),
            ("CQ14.3", "From which EMS does allocation alloc2 ultimately derive?",
             "Provenance path", "ABox",
             """SELECT DISTINCT ?ems WHERE {
  d:alloc2 ex:allocatesReading ?reading .
  ?cebd ex:hasReading ?reading ; ex:compiledBy ?ems .
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
  ?ems ex:emsStandardVersion/skos:prefLabel ?edition .
}""", [("ems1", "EN 50463:2017"), ("ems2", "EN 50463:2012")]),
            ("CQ15.2", "Which vehicles carry an EMS although their type does not declare an energy meter?",
             "Negation across registers (cf. SHACL R4)", "ABox",
             """SELECT ?vehicle WHERE {
  ?ems ex:installedOn ?vehicle . ?vehicle era:vehicleType ?type .
  FILTER NOT EXISTS { ?type era:configDependentParameter/era:hasOnboardEnergyMeasurement true . }
}""", [("loco2",)]),
            ("CQ15.3", "How many EMS lack a declared standard edition?",
             "Counting (completeness)", "ABox",
             """SELECT (COUNT(?ems) AS ?n) WHERE {
  ?ems a ex:EnergyMeasurementSystem .
  FILTER NOT EXISTS { ?ems ex:emsStandardVersion ?v . }
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
     "ex:actualDepartureTime now distinguishes actual from booked time and requires an evidence reference; no authoritative departure event or interface mapping is validated by the synthetic example.",
     "Map an authoritative operating event and its provenance for each deployment; do not infer departure from the first location report without an approved operational rule."),
    ("G3", "Which energy supplier delivered the allocated energy, and at what price?",
     "Supplier, contract, and price data are outside this iteration and must not be inferred from settlement party or infrastructure operator.",
     "Add a separate market/contract module after verifying the operative legal interface obligations and responsible actors."),
    ("G4", "How were network losses allocated between consumers?",
     "Loss coefficients and their allocation (AS-03 §5.6.2(g), Infrabel 96 % rule) are not modelled.",
     "Add a loss allocation method concept and coefficient to ex:EnergyAllocation."),
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


def run(rc3_path=DEFAULT_ERA_ONTOLOGY):
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
    return (conforms, sorted(shacl), results,
            validate_allocation_accounting(data),
            validate_negative_cases(data, ont))


def validate_allocation_accounting(data):
    """Check arithmetic that requires aggregation across allocation components."""
    ex = rdflib.Namespace("http://example.org/era-energy#")
    exc = rdflib.Namespace("http://example.org/era-energy/concepts/")
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
    ex = rdflib.Namespace("http://example.org/era-energy#")
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
    bad_allocation.remove((d.r1, ex.activeEnergyConsumed, rdflib.Literal("410.5", datatype=rdflib.XSD.decimal)))
    bad_allocation.add((d.r1, ex.activeEnergyConsumed, rdflib.Literal("400.0", datatype=rdflib.XSD.decimal)))
    allocation_conforms, allocation_report, _ = pyshacl.validate(
        bad_allocation, shacl_graph=SHAPES, ont_graph=ont, inference="none",
        advanced=True, allow_warnings=True, inplace=True)
    accounting_issues = validate_allocation_accounting(bad_allocation)
    if allocation_conforms and not accounting_issues:
        failures.append("Validation accepted allocation components exceeding the source reading")
    if not isinstance(allocation_report, rdflib.Graph):
        failures.append(f"SHACL allocation negative test could not run: {allocation_report}")
    return failures


def render(conforms, shacl, results, accounting_issues, md_path):
    by_id = {cq_id: (ok, got) for _, cq_id, ok, got in results}
    passed = sum(1 for r in results if r[2])
    out = []
    w = out.append
    w("# Competency questions – ERA energy settlement extension\n")
    w("Validation of the ontology draft **v0.5** (`era-energy-settlement-draft.ttl`) and its shapes "
      "against **ERA ontology v4.0.0-rc.3**, following the LOT methodology.\n")
    w(f"**Result: {passed} of {len(results)} competency questions pass.** "
      f"SHACL conforms: **{conforms}**; allocation arithmetic issues: **{len(accounting_issues)}**; "
      f"SHACL results: **{len(shacl)}**.\n")
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
    w("| Implementation | OWL 2 (RDFS-level axioms) and SHACL, `ex:` extension of `era:` v4.0.0-rc.3, reusing SOSA/SSN, SAREF, QUDT, PROV-O, OWL-Time, GeoSPARQL |")
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
    w("- **No OWL reasoner is used.** Subclass and subproperty entailments are written as property paths "
      "(`rdf:type/rdfs:subClassOf*`, `rdfs:subPropertyOf*`). CQ7.2 uses `ex:exchangesWith|^ex:exchangesWith` because "
      "the symmetry of the property is only entailed by a reasoner.")
    w("- **CQ11.2 depends on a SHACL rule.** The link from the composition journey section's normalized `era:locoNumber` "
      "to a registered vehicle is derived only when it matches a valid 12-digit vehicle number.")
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
    args = ap.parse_args()
    conforms, shacl, results, accounting_issues, negative_failures = run(args.rc3)
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
    if args.md:
        render(conforms, shacl, results, accounting_issues, args.md)
        print("wrote", args.md)
    sys.exit(0 if all(r[2] for r in results) and conforms
             and not accounting_issues and not negative_failures else 1)


if __name__ == "__main__":
    main()
