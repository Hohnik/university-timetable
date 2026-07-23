"""
Curriculum data transcribed from HS Landshut SPOs and Studien- und Prüfungspläne.
Sources: "konsolidierte Fassung" SPOs fetched July 2026 (IF, WIF, KI, AIF, DVM);
SA/KIJ Studien- und Prüfungspläne (WiSe 2026/27) fetched from haw-landshut.de.

Why this file exists
--------------------
The Primuss export says *that* a course is taught, never whether a student
must attend it. The SPO says exactly that. Without it, the scheduler treats a
6th-semester curriculum as 22 simultaneous mandatory courses (52 timeslots a
week), which is why checking the published timetable produced 104 phantom
"curriculum clash" violations.

Only mandatory courses (PFM) bind every student in a curriculum. Elective
courses (WPFM) are picked a few at a time, so they may overlap with each
other — the SPOs even say so explicitly: "kein Anspruch darauf, dass keine
zeitlichen Überschneidungen sämtlicher wählbarer Module existieren."

Each entry: course code -> (name, semester, ECTS, SWS). The IF-faculty
programs only transcribe the summer-semester curricula present in that
scraped data (semester 2, 4, 6); the SA-faculty programs below cover all 7
semesters. Semester 5 (IF) / 4 (SA) / 5 (KIJ) is the Praxissemester and has
almost no teaching. SA semester 6 offers "N6.1 and 2 of {N6.2..N6.5}" as a
themed choice — those four are electives, not transcribed here, matching how
WPF courses are excluded everywhere else in this file.
"""

# --- mandatory modules per program, summer semesters -----------------------
MANDATORY = {
    "Bachelor Informatik": {
        2: [("IB061", "Software Engineering I", 5, 4),
            ("IB015", "Grundlagen der theoretischen Informatik", 7, 6),
            ("IB040", "Mathematik II", 7, 6),
            ("IB250", "Programmieren II", 7, 6),
            ("IB440", "Präsentation und Kommunikation", 5, 4)],
        4: [("IB345", "Rechnerarchitektur", 7, 6),
            ("IB330", "Algorithmen und Datenstrukturen", 5, 4),
            ("IB430", "Statistik", 5, 4),
            ("IB400", "Betriebssysteme", 5, 4),
            ("IB420", "Datenkommunikation", 5, 4)],
        6: [("IB630", "Verteilte Systeme", 5, 4),
            ("IB640", "Internettechnologien", 5, 4),
            ("IB651", "Seminar", 3, 2),
            ("IB351", "Studienprojekt", 5, 4)],
    },
    "Bachelor Wirtschaftsinformatik": {
        2: [("WIF210", "Software Engineering I", 5, 4),
            ("WIF230", "Mathematik II", 7, 6),
            ("WIF260", "Programmieren II", 7, 6),
            ("WIF430", "Kosten- und Leistungsrechnung", 3, 2),
            ("WIF290", "Foundations of Scientific Work in Business Informatics", 4, 4)],
        4: [("WIF250", "Finanzen, Investition", 5, 4),
            ("WIF330", "Statistik", 5, 4),
            ("WIF410", "Algorithmen und Datenstrukturen", 5, 4),
            ("WIF420", "IT-Infrastrukturen", 5, 4),
            ("WIF450", "Grundlagen Produktion, Logistik und Dienstleistungen", 5, 4),
            ("WIF460", "Operations Research", 5, 4)],
        6: [("WIF610", "Internettechnologien", 5, 4),
            ("WIF650", "IT-Management", 5, 4),
            ("WIF660", "Unternehmenssoftware", 5, 4),
            ("WIF640", "Seminar", 3, 2),
            ("WIF490", "Praxisorientiertes Studienprojekt", 5, 4)],
    },
    "Bachelor Künstliche Intelligenz": {
        2: [("KI210", "Data Science II", 3, 3),
            ("KI220", "Mathematik II", 7, 6),
            ("KI230", "Programmieren II", 7, 6),
            ("KI240", "Software Engineering I", 5, 4),
            ("KI250", "Statistik", 5, 4),
            ("KI260", "Technische Grundlagen der KI", 3, 3)],
        4: [("KI410", "Algorithmen und Datenstrukturen", 5, 4),
            ("KI420", "Internet of Things", 5, 4),
            ("KI430", "Natural Language Processing", 5, 4),
            ("KI440", "Machine Learning II", 6, 4),
            ("KI450", "Künstliche Intelligenz II", 5, 4)],
        6: [("KI610", "Big Data Algorithms and Systems", 5, 4),
            ("KI620", "Machine Learning III", 5, 4),
            ("KI630", "Praxisorientiertes Studienprojekt", 5, 4)],
    },
    "Bachelor Automobilinformatik": {
        2: [("AIF211", "Programmieren II", 7, 6),
            ("AIF220", "Ingenieurmathematik II", 7, 6),
            ("AIF240", "Elektronik und Messtechnik", 7, 6),
            ("AIF241", "Angewandte Physik", 7, 6)],
        4: [("AIF212", "Software Engineering", 5, 4),
            ("AIF410", "Echtzeitbetriebssysteme", 5, 4),
            ("AIF411", "Algorithmen und Datenstrukturen", 5, 4),
            ("AIF413", "Modellbasierte Entwicklung II", 5, 4),
            ("AIF450", "Grundlagen der Automobiltechnik", 5, 4),
            ("AIF612", "Softwarearchitekturen", 5, 4)],
        6: [("AIF390", "Studienprojekt", 5, 4),
            ("AIF620", "Entwicklung sicherheitskritischer Systeme", 7, 6),
            ("AIF630", "Autonome Fahrzeuge", 5, 4),
            ("AIF650", "Fahrwerktechnik", 5, 4),
            ("AIF651", "Antriebskonzepte", 5, 4)],
    },
    "Bachelor Digitales Verwaltungsmanagement": {
        2: [("DVM210", "Software Engineering I", 5, 4),
            ("DVM230", "Open Government & Open Data", 5, 4),
            ("DVM260", "Programmieren II", 7, 6),
            ("DVM270", "Effizienz im öffentlichen Sektor", 3, 2),
            ("DVM290", "Foundations of Scientific Work in Smart Administration", 4, 4)],
        4: [("DVM440", "IT-Business Case", 5, 4),
            ("DVM410", "Process Mining", 5, 4),
            ("DVM430", "Visual Analytics", 5, 4),
            ("DVM420", "IT-Infrastrukturen", 5, 4),
            ("DVM450", "Management von Veränderungsprojekten und -prozessen", 5, 4),
            ("DVM460", "Verwaltungsrecht", 5, 4)],
        6: [("DVM610", "Internettechnologien", 5, 4),
            ("DVM650", "IT-Management", 5, 4),
            ("DVM660", "Standard-IT-Anwendungen in der Verwaltung", 5, 4),
            ("DVM640", "Seminar", 3, 2),
            ("DVM490", "Praxisorientiertes Studienprojekt", 5, 4)],
    },
    "Soziale Arbeit": {
        1: [("N1.1", "Menschliches Verhalten, Entwicklung, Erziehung und Bildung", 6, 6),
            ("N1.2", "Theorien und Organisationen der Sozialen Arbeit", 6, 6),
            ("N1.3", "Gesellschaft und Politik", 6, 6),
            ("N1.4", "Strukturen des Rechts", 6, 4),
            ("N1.5", "Propädeutikum", 6, 4)],
        2: [("N2.1", "Handlungskompetenz - Basisstrategien", 8, 6),
            ("N2.2", "Wissenschaft und Praxis Sozialer Arbeit", 5, 4),
            ("N2.3", "Methoden Sozialwissenschaftlicher Forschung", 5, 4),
            ("N2.4", "Sozialleistungrecht und Formen des Zusammenlebens", 6, 6),
            ("N2.5", "Projektwerkstatt", 4, 2),
            ("N2.6", "MentLA", 2, 1)],
        3: [("N3.1", "Handlungskompetenz - Differenzielle Methoden", 6, 4),
            ("N3.2", "Soziale Arbeit und Diversität", 6, 4),
            ("N3.3", "Soziale Arbeit und Gesundheit", 6, 4),
            ("N3.4", "Soziale Arbeit und Sozialraum", 6, 4),
            ("N3.5", "Soziale Arbeit und soziale Ungleichheit", 6, 4)],
        4: [("N4.1", "Studium Generale", 6, 6),
            ("N4.2", "Soziale Arbeit und Diversität - Methoden", 6, 4),
            ("N4.3", "Soziale Arbeit und Gesundheit - Methoden Klinischer Sozialarbeit", 6, 4),
            ("N4.4", "Soziale Arbeit und Sozialraum - Methoden sozialräumlichen Arbeitens", 6, 4),
            ("N4.5", "Soziale Arbeit und soziale Ungleichheit - Methoden", 6, 4)],
        5: [("N5.1", "Praxisstudium und Praxisreflexion", 30, 4)],
        6: [("N6.1", "Forschendes Lernen", 6, 5)],
        7: [("N7.1", "Bachelorarbeit mit Begleitseminar", 14, 1),
            ("N7.2", "Berufliches und berufsethisches Selbstverständnis in der Sozialen Arbeit", 5, 4),
            ("N7.3", "Handlungskompetenz - Diagnostik und Fallarbeit", 6, 6),
            ("N7.4", "Sozialökonomie und Soziale Arbeit", 5, 4)],
    },
    "Soziale Arbeit in der Kinder- und Jugendhilfe": {
        1: [("J1.1", "Menschliches Verhalten, Entwicklung, Erziehung und Bildung", 6, 6),
            ("J1.2", "Theorien und Organisationen der Sozialen Arbeit", 6, 6),
            ("J1.3", "Gesellschaft und Politik", 5, 6),
            ("J1.4", "Strukturen des Rechts", 6, 4),
            ("J1.5", "Propädeutikum", 5, 4),
            ("J1.6", "MentLA", 2, 1)],
        2: [("J2.1", "Handlungskompetenz - Basisstrategien", 7, 6),
            ("J2.2", "Wissenschaft und Praxis Sozialer Arbeit", 6, 4),
            ("J2.3", "Methoden Sozialwissenschaftlicher Forschung", 5, 4),
            ("J2.4", "Sozialleistungrecht und Formen des Zusammenlebens", 6, 6),
            ("J2.5", "Projektwerkstatt", 4, 2),
            ("J2.6", "MentLA", 2, 1)],
        3: [("N3.1", "Handlungskompetenz - Differenzielle Methoden", 6, 4),
            ("J3.2", "Entwicklung von Kindern und Jugendlichen - Grundlagen und Einflussfaktoren", 6, 4),
            ("J3.3", "Organisationsformen und Handlungsfelder der inklusiven Kinder-, Jugend- und Familienhilfe", 6, 4),
            ("J3.4", "Kinder- und Jugendhilferecht", 6, 4),
            ("J3.5", "Kinderschutz in Theorie und Praxis", 6, 4)],
        4: [("J4.1", "Praxisstudium und Praxisreflexion", 30, 4)],
        5: [("J5.1", "Handlungskompetenz - Diagnostik in der Kinder- und Jugendhilfe", 6, 4),
            ("J5.2", "Lebens- und Problemlagen im Kindes- und Jugendalter", 6, 4),
            ("J5.3", "Diversität als Herausforderung für Jugendforschung und Jugendpolitik", 6, 4),
            ("J5.4", "Kindertagesbetreuung und Förderung der Erziehung in der Familie", 6, 4),
            ("J5.5", "Jugendarbeit und Jugendbildungsarbeit", 6, 4)],
        6: [("N6.1", "Forschendes Lernen", 6, 5),
            ("J6.2", "Teilstationäre und stationäre Hilfen zur Erziehung", 6, 4),
            ("J6.3", "Ambulante Hilfen zur Erziehung", 6, 4),
            ("J6.4", "Gesundheitsförderung und Prävention", 6, 4),
            ("J6.5", "Jugendhilfe in öffentlicher Verantwortung", 6, 4)],
        7: [("N7.1", "Bachelorarbeit mit Begleitseminar", 14, 1),
            ("N7.2", "Berufliches und berufsethisches Selbstverständnis in der Sozialen Arbeit", 5, 4),
            ("J7.3", "Studium Generale", 6, 6),
            ("N7.4", "Sozialökonomie und Soziale Arbeit", 5, 4)],
    },
}


def mandatory_names(program, semester):
    """Lowercased course names a curriculum of this program/semester must attend."""
    entries = MANDATORY.get(program, {}).get(semester, [])
    return {name.lower() for _code, name, _e, _s in entries}


def expected_sws(program, semester):
    """Total SWS the SPO prescribes — a sanity check against the scraped data."""
    return sum(sws for _c, _n, _e, sws in MANDATORY.get(program, {}).get(semester, []))
