# Jyotish Kundli Final

A deploy-ready Flask + Swiss Ephemeris Vedic astrology application using Lahiri sidereal calculations.

## Included
- Birth place geocoding + timezone
- Ascendant/Lagna and Moon Rashi
- D1 Rashi and D9 Navamsa data
- Planet longitude, sign, degree, house, nakshatra, pada, nakshatra lord, retrograde/status
- House lords
- Graha drishti screening
- Exaltation/debilitation/own-sign screening
- Vimshottari Mahadasha with calendar dates and Antardasha dates
- Traditional marriage/career/finance interpretation framework
- Named yoga screening and Mangal Dosha screening
- Print/Save PDF from browser
- JSON export
- Mobile-friendly UI

## Run
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
Open http://127.0.0.1:5000

Note: Geocoding uses Nominatim/OpenStreetMap. For production, respect its usage policy or use a commercial geocoder. Jyotish interpretations are traditional and not scientifically validated.
