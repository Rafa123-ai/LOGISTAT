from __future__ import annotations
from datetime import datetime

COMPANY_NAME = 'CONCRETOS CAGSA'
ADDRESS = 'Oriente 1 s/n, entre Oriente 11 y 15, Barrio de San José, CP 94350, Ixtaczoquitlán, Ver.'
MAPS_URL = 'https://www.google.com/maps/search/?api=1&query=CONCRETOS%20CAGSA%20Oriente%201%20s%2Fn%20Ixtaczoquitl%C3%A1n%20Veracruz%2094350'

LOGISTAT_VERSION = 'LOGISTAT v11'

AUTHOR_NAME = 'Mtro. en Arq. Jaime R. Hernández García'
AUTHOR_ROLE = 'Gerente del Depto. de Análisis de Datos'

def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")




