# Electoral Drift

This context describes the language used to analyze electoral change across Polish municipalities. It separates observed electoral and socioeconomic facts from the analytical identities and classifications derived from them.

## Territorial units

**Region**:
A territorial unit represented at a particular point in its administrative history. In the current scope, a region is a municipality (`gmina`), including a city with county rights represented at municipality level.
_Avoid_: County, canonical region, municipality name as identity

**Historical region**:
A region as identified and described by the TERC snapshot appropriate to a particular election period.
_Avoid_: Canonical region, current municipality

**Canonical region**:
A stable analytical identity that connects historical region versions treated as the same municipality across elections. It complements rather than replaces each source region and its historical TERC identifier.
_Avoid_: Region, current region, canonical municipality

**TERYT**:
The Polish national registry of territorial division. This project uses its TERC subsystem to identify municipalities.
_Avoid_: TERYT code, TERC

**PKW municipality code**:
The six-digit municipality code present in PKW election data. It identifies the municipality area but does not encode its type.
_Avoid_: TERC identifier, canonical region ID

**TERC identifier**:
The seven-digit historical identifier of a territorial unit, including its unit type. Different identifiers remain distinct source-region identities even when they belong to one canonical region.
_Avoid_: PKW municipality code, canonical region ID

## Elections

**Election**:
A dated electoral event of a defined type and round. A second voting round is a distinct election event.
_Avoid_: Election year, campaign

**Committee**:
A committee, party list, party, or candidate as presented in one election. Its identity is election-specific and must not be assumed stable over time.
_Avoid_: Political bloc, party when the source identifies a committee or candidate

**Political bloc**:
A normalized analytical grouping that makes election-specific committees comparable across elections. Assigning a committee to a political bloc is an interpretation, not a source result.
_Avoid_: Committee, party

**Election result**:
An observed result for one committee in one region and election, expressed through votes and related participation measures. It is a source fact independent of later analytical classification.
_Avoid_: Bloc result, prediction

## Structural data

**Socioeconomic variable**:
A defined demographic, economic, migration, urbanization, or religiosity measure available for territorial analysis.
_Avoid_: Feature

**Socioeconomic observation**:
The value of one socioeconomic variable for one region and year, with its source provenance.
_Avoid_: Election result, model feature

**Registered unemployment working-age share**:
The percentage of registered unemployed persons in the working-age population of a region. It is distinct from the official registered unemployment rate, whose denominator is the economically active civilian population.
_Avoid_: Unemployment rate, registered unemployment rate

## Electoral change

**Political drift**:
A change in electoral support, bloc margin, or winning political bloc for a region across elections.
_Avoid_: Prediction, political stability

**Political stability**:
A derived characterization of a region's pattern of winners, margins, and changes across elections.
_Avoid_: Election result, political drift

**Safe region**:
A region with at least two uniquely decided elections, no winner change, and continuous wins by the same PiS or KO political bloc.
_Avoid_: Stable region

**Swing region**:
A region with at least two changes between unique winning political blocs across consecutive elections with unique winners.
_Avoid_: Emerging-shift region, volatile region

**Emerging-shift region**:
A region with exactly one change between unique winning political blocs across consecutive elections with unique winners.
_Avoid_: Swing region

**Fragmented or local region**:
A region whose available history is insufficient for a safe-region classification or whose unique winners do not remain exclusively within the PiS or KO political blocs.
_Avoid_: Other region, unknown region
