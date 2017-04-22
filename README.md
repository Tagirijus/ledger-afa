Ein Programm zur Berechnung und Anzeige der Abschreibung für Abnutzung (AfA)
auf Grundlage eines ledger Journals.

## Journal

Das Script ist für folgenden Aufbau des Journals vorgesehen:

	2016-01-19 * (a99) Einkauf
	 Inventar:Gegenstand  € 999,00
	 Girokonto

	2016-12-31 * (a99) Abschreibung
	 AfA:Gegenstände  € 99,90
	 Inventar:Gegenstand

- Jeder abzuschreibende Posten hat genau ein eigenes Konto
- Das Kaufdatum ist das der ersten Buchung auf das Konto des Postens,
  der Kaufpreis der Betrag der ersten Buchung.
- Innerhalb eines Jahres werden Abschreibungen von diesem Konto auf
  ein AfA-Konto gebucht. Die Bezeichnung des Kontos kann man in der
  Kommandozeile festlegen.
- "Buchwert Anfang" ist die Summe aller Buchungen auf dem Konto bis
  einschließlich des Vorjahres des Berechnungsjahres sowie alle eingehenden
  Buchungen des Berechnungsjahres. Dies spiegelt die gängige Handhabung
  nachträglicher Anschaffungskosten wider.
- Ausgehende Buchungen innerhalb des Berechnungsjahres ergeben den
  Abschreibungsbetrag.

## Abhängigkeiten

	ledger --with-python

`ledger` gibt es nicht als Python package, die Installation von ledger muss also die Python bindings enthalten.

## Nutzung

	python ledger-afa.py -h

für eine Liste der Kommandozeilen-Optionen.