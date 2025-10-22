import streamlit as st
import requests
import json
import re
from urllib.parse import quote
import pandas as pd
import math

# Configuration de la page
st.set_page_config(
    page_title="Dimensionnement Solaire Sénégal",
    page_icon="☀️",
    layout="wide"
)

# Valeurs par défaut pour éviter les erreurs si l’utilisateur n’a pas encore configuré tab1
if 'consommation' not in st.session_state:
    st.session_state.consommation = 10.0  # kWh/jour par défaut
if 'choix' not in st.session_state:
    st.session_state.choix = {
        'type_batterie': 'Lithium',
        'type_onduleur': 'Hybride',
        'voltage': 48
    }

# Base de données complète des prix (en FCFA) - basée sur energiesolairesenegal.com
PRIX_EQUIPEMENTS = {
    "panneaux": {
        "50W Polycristallin": {"prix": 45000, "puissance": 50, "type": "Polycristallin"},
        "100W Polycristallin": {"prix": 75000, "puissance": 100, "type": "Polycristallin"},
        "150W Polycristallin": {"prix": 95000, "puissance": 150, "type": "Polycristallin"},
        "200W Polycristallin": {"prix": 115000, "puissance": 200, "type": "Polycristallin"},
        "250W Polycristallin": {"prix": 140000, "puissance": 250, "type": "Polycristallin"},
        "260W Polycristallin": {"prix": 145000, "puissance": 260, "type": "Polycristallin"},
        "270W Polycristallin": {"prix": 150000, "puissance": 270, "type": "Polycristallin"},
        "280W Polycristallin": {"prix": 155000, "puissance": 280, "type": "Polycristallin"},
        "320W Polycristallin": {"prix": 180000, "puissance": 320, "type": "Polycristallin"},
        "335W Polycristallin": {"prix": 195000, "puissance": 335, "type": "Polycristallin"},
        
        # Ajouts alignés sur energiesolairesenegal.com (prix promo)
        "375W Monocristallin": {"prix": 49174, "puissance": 375, "type": "Monocristallin"},
        "450W Monocristallin": {"prix": 56199, "puissance": 450, "type": "Monocristallin"},
        "550W Monocristallin": {"prix": 65233, "puissance": 550, "type": "Monocristallin"},
    },
    "batteries": {
        # Batteries Plomb-Acide (traditionnelles) — prix promo alignés
        "Plomb 100Ah 12V": {"prix": 110395, "capacite": 100, "voltage": 12, "type": "Plomb", "cycles": 500, "decharge_max": 50},
        "Plomb 150Ah 12V": {"prix": 160574, "capacite": 150, "voltage": 12, "type": "Plomb", "cycles": 500, "decharge_max": 50},
        "Plomb 200Ah 12V": {"prix": 210759, "capacite": 200, "voltage": 12, "type": "Plomb", "cycles": 500, "decharge_max": 50},
        
        # Batteries AGM (Absorbed Glass Mat) — prix promo alignés
        "AGM 100Ah 12V": {"prix": 110395, "capacite": 100, "voltage": 12, "type": "AGM", "cycles": 800, "decharge_max": 70},
        "AGM 150Ah 12V": {"prix": 160574, "capacite": 150, "voltage": 12, "type": "AGM", "cycles": 800, "decharge_max": 70},
        "AGM 200Ah 12V": {"prix": 210759, "capacite": 200, "voltage": 12, "type": "AGM", "cycles": 800, "decharge_max": 70},
        "AGM 250Ah 12V": {"prix": 350000, "capacite": 250, "voltage": 12, "type": "AGM", "cycles": 800, "decharge_max": 70},
        
        # Batteries GEL — ajustement 200Ah
        "GEL 100Ah 12V": {"prix": 180000, "capacite": 100, "voltage": 12, "type": "GEL", "cycles": 1200, "decharge_max": 80},
        "GEL 150Ah 12V": {"prix": 270000, "capacite": 150, "voltage": 12, "type": "GEL", "cycles": 1200, "decharge_max": 80},
        "GEL 200Ah 12V": {"prix": 210759, "capacite": 200, "voltage": 12, "type": "GEL", "cycles": 1200, "decharge_max": 80},
        "GEL 250Ah 12V": {"prix": 450000, "capacite": 250, "voltage": 12, "type": "GEL", "cycles": 1200, "decharge_max": 80},
        
        # Batteries Lithium LiFePO4 — prix promo alignés
        "Lithium 100Ah 12V": {"prix": 450000, "capacite": 100, "voltage": 12, "type": "Lithium", "cycles": 3000, "decharge_max": 90},
        "Lithium 150Ah 12V": {"prix": 650000, "capacite": 150, "voltage": 12, "type": "Lithium", "cycles": 3000, "decharge_max": 90},
        "Lithium 200Ah 12V": {"prix": 850000, "capacite": 200, "voltage": 12, "type": "Lithium", "cycles": 3000, "decharge_max": 90},
        "Lithium 150Ah 48V": {"prix": 1345883, "capacite": 150, "voltage": 48, "type": "Lithium", "cycles": 3000, "decharge_max": 90},
        "Lithium 200Ah 48V": {"prix": 1103959, "capacite": 200, "voltage": 48, "type": "Lithium", "cycles": 3000, "decharge_max": 90},
    },
    "onduleurs": {
        # Onduleurs Standard (Off-Grid)
        "1000W 12V Pur Sinus": {"prix": 150000, "puissance": 1000, "voltage": 12, "type": "Off-Grid"},
        "1500W 24V Pur Sinus": {"prix": 240000, "puissance": 1500, "voltage": 24, "type": "Off-Grid"},
        "2000W 24V Pur Sinus": {"prix": 350000, "puissance": 2000, "voltage": 24, "type": "Off-Grid"},
        
        # Onduleurs Hybrides (avec MPPT intégré) — prix promo
        "Hybride 1KVA 12V MPPT": {"prix": 151002, "puissance": 1000, "voltage": 12, "type": "Hybride", "mppt": "30A"},
        "Hybride 3KVA 24V MPPT": {"prix": 400482, "puissance": 3000, "voltage": 24, "type": "Hybride", "mppt": "60A"},
        "Hybride 3KVA 48V MPPT": {"prix": 538000, "puissance": 3000, "voltage": 48, "type": "Hybride", "mppt": "80A"},
        "Hybride 5KVA 48V MPPT": {"prix": 750000, "puissance": 5000, "voltage": 48, "type": "Hybride", "mppt": "100A"},
        
        # Onduleurs Online (haute qualité) — prix promo
        "Online 2KVA": {"prix": 263137, "puissance": 2000, "voltage": 24, "type": "Online"},
        "Online 3KVA": {"prix": 558049, "puissance": 3000, "voltage": 48, "type": "Online"},
        "Online 6KVA": {"prix": 1220487, "puissance": 6000, "voltage": 48, "type": "Online"},
        "Online 10KVA Mono": {"prix": 1750962, "puissance": 10000, "voltage": 48, "type": "Online"},
        "Online 10KVA 3/3 HF": {"prix": 3157902, "puissance": 10000, "voltage": 48, "type": "Online Tri"},
        "Online 20KVA 3/3 HF": {"prix": 4565499, "puissance": 20000, "voltage": 48, "type": "Online Tri"},
        "Online 30KVA 3/3 HF": {"prix": 5974410, "puissance": 30000, "voltage": 48, "type": "Online Tri"},
    },
    "regulateurs": {
        # Régulateurs PWM
        "PWM 10A 12/24V": {"prix": 15000, "amperage": 10, "type": "PWM", "voltage_max": 50},
        "PWM 20A 12/24V": {"prix": 25000, "amperage": 20, "type": "PWM", "voltage_max": 50},
        "PWM 30A 12/24V": {"prix": 35000, "amperage": 30, "type": "PWM", "voltage_max": 50},
        "PWM 40A 12/24V": {"prix": 45000, "amperage": 40, "type": "PWM", "voltage_max": 50},
        
        # Régulateurs MPPT (30% plus efficaces)
        "MPPT 20A 12/24V": {"prix": 45000, "amperage": 20, "type": "MPPT", "voltage_max": 100},
        "MPPT 30A 12/24/48V": {"prix": 65000, "amperage": 30, "type": "MPPT", "voltage_max": 100},
        "MPPT 40A 12/24/48V": {"prix": 85000, "amperage": 40, "type": "MPPT", "voltage_max": 150},
        "MPPT 60A 12/24/48V": {"prix": 120000, "amperage": 60, "type": "MPPT", "voltage_max": 150},
        "MPPT 80A 12/24/48V": {"prix": 160000, "amperage": 80, "type": "MPPT", "voltage_max": 150},
        "MPPT 100A 12/24/48V": {"prix": 200000, "amperage": 100, "type": "MPPT", "voltage_max": 150},
    }
}

PRIX_INSTALLATION = {
    "petit": 50000,  # < 1kW
    "moyen": 100000,  # 1-3kW
    "grand": 200000,  # 3-10kW
    "tres_grand": 400000,  # > 10kW
}

# Informations sur les types de batteries
INFO_BATTERIES = {
    "Plomb": {
        "avantages": "✓ Prix bas\n✓ Technologie éprouvée\n✓ Facilement disponible",
        "inconvenients": "✗ Nécessite entretien (ajout d'eau)\n✗ Durée de vie courte (2-3 ans)\n✗ Décharge limitée à 50%",
        "usage": "Petit budget, usage occasionnel"
    },
    "AGM": {
        "avantages": "✓ Sans entretien\n✓ Bonne résistance aux chocs\n✓ Supporte bien la chaleur\n✓ Charge rapide",
        "inconvenients": "✗ Plus cher que le plomb\n✗ Décharge limitée à 70%",
        "usage": "Bon compromis prix/performance, idéal pour le Sénégal"
    },
    "GEL": {
        "avantages": "✓ Sans entretien\n✓ Excellente durée de vie (5-7 ans)\n✓ Décharge profonde possible (80%)\n✓ Supporte bien les températures élevées",
        "inconvenients": "✗ Plus cher que AGM\n✗ Charge plus lente",
        "usage": "Usage intensif, meilleur rapport qualité/durée"
    },
    "Lithium": {
        "avantages": "✓ Durée de vie exceptionnelle (10-12 ans)\n✓ Décharge profonde 90%\n✓ Très léger et compact\n✓ Sans entretien\n✓ Charge ultra-rapide",
        "inconvenients": "✗ Prix élevé (3-4x plus cher)\n✗ Nécessite BMS pour sécurité",
        "usage": "Meilleur investissement long terme, installations modernes"
    }
}

# Catalogue d'appareils par familles (puissances typiques)
APPAREILS_FAMILLES = {
    "Éclairage": [
        {"nom": "LED 7W", "puissance": 7},
        {"nom": "LED 10W", "puissance": 10},
        {"nom": "Lampe tube 18W", "puissance": 18},
        {"nom": "Néon 36W", "puissance": 36},
        {"nom": "Néon 58W", "puissance": 58},
        {"nom": "Fluocompacte 15W", "puissance": 15},
        {"nom": "Plafonnier LED 24W", "puissance": 24}
    ],
    "Ventilation": [
        {"nom": "Ventilateur 50W", "puissance": 50},
        {"nom": "Ventilateur 75W", "puissance": 75},
        {"nom": "Ventilateur 100W", "puissance": 100}
    ],
    "Électroménager": [
        {"nom": "TV 100W", "puissance": 100},
        {"nom": "Réfrigérateur 150W", "puissance": 150},
        {"nom": "Congélateur 200W", "puissance": 200},
        {"nom": "Machine à laver 500W", "puissance": 500},
        {"nom": "Micro-ondes 1000W", "puissance": 1000}
    ],
    "Informatique": [
        {"nom": "Ordinateur 200W", "puissance": 200},
        {"nom": "Laptop 60W", "puissance": 60},
        {"nom": "Routeur 10W", "puissance": 10},
        {"nom": "Chargeur téléphone 10W", "puissance": 10}
    ],
    "Cuisine": [
        {"nom": "Bouilloire 2000W", "puissance": 2000},
        {"nom": "Plaque électrique 1500W", "puissance": 1500},
        {"nom": "Mixeur 500W", "puissance": 500}
    ],
    "Pompage": [
        {"nom": "Pompe 500W", "puissance": 500},
        {"nom": "Pompe 1000W", "puissance": 1000}
    ],
    "Atelier": [
        {"nom": "Perceuse 600W", "puissance": 600}
    ],
    "Climatisation": [
        {"nom": "Climatiseur 1CV 900W", "puissance": 900},
        {"nom": "Climatiseur 1.5CV 1100W", "puissance": 1100}
    ],
    "Eau chaude": [
        {"nom": "Chauffe-eau instantané 3000W", "puissance": 3000},
        {"nom": "Chauffe-eau instantané 5000W", "puissance": 5000},
        {"nom": "Cumulus 50L 1500W", "puissance": 1500},
        {"nom": "Cumulus 100L 2000W", "puissance": 2000}
    ]
}

# Mots-clés simples pour suggestions IA → appareils
APPAREILS_KEYWORDS = {
    "tv": ("Électroménager", "TV 100W"),
    "télé": ("Électroménager", "TV 100W"),
    "television": ("Électroménager", "TV 100W"),
    "frigo": ("Électroménager", "Réfrigérateur 150W"),
    "réfrigérateur": ("Électroménager", "Réfrigérateur 150W"),
    "congelateur": ("Électroménager", "Congélateur 200W"),
    "ventilateur": ("Ventilation", "Ventilateur 75W"),
    "ordi": ("Informatique", "Ordinateur 200W"),
    "ordinateur": ("Informatique", "Ordinateur 200W"),
    "pc": ("Informatique", "Ordinateur 200W"),
    "laptop": ("Informatique", "Laptop 60W"),
    "routeur": ("Informatique", "Routeur 10W"),
    "wifi": ("Informatique", "Routeur 10W"),
    "chargeur": ("Informatique", "Chargeur téléphone 10W"),
    "pompe": ("Pompage", "Pompe 500W"),
    "machine": ("Électroménager", "Machine à laver 500W"),
    "micro": ("Électroménager", "Micro-ondes 1000W"),
    "bouilloire": ("Cuisine", "Bouilloire 2000W"),
    "neon": ("Éclairage", "Néon 36W"),
    "néon": ("Éclairage", "Néon 36W"),
    "fluorescent": ("Éclairage", "Néon 36W"),
    "tube": ("Éclairage", "Lampe tube 18W"),
    "chauffe": ("Eau chaude", "Chauffe-eau instantané 3000W"),
    "chauffeau": ("Eau chaude", "Chauffe-eau instantané 3000W"),
    "douche": ("Eau chaude", "Chauffe-eau instantané 3000W"),
    "cumulus": ("Eau chaude", "Cumulus 50L 1500W")
}

# Fonction pour appeler l'API DeepSeek
def appeler_assistant_ia(question, contexte=""):
    # Priorité aux secrets, fallback à la session
    api_key = None
    try:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
    except Exception:
        api_key = st.session_state.get('api_key', '')

    if not api_key:
        return "⚠️ Veuillez entrer votre clé API DeepSeek dans la barre latérale ou dans secrets.toml."
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""Tu es un expert en énergie solaire au Sénégal. Tu connais bien le climat local (chaleur, humidité) et les meilleures pratiques d'installation.
Contexte: {contexte}
Question: {question}
Réponds de manière claire et pratique en français, avec des conseils adaptés au Sénégal."""
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Tu es un expert en installations solaires au Sénégal. Tu aides les utilisateurs à comprendre leurs besoins en énergie solaire et à choisir les bons équipements."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"❌ Erreur API: {response.status_code}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

# Variante streaming pour réponses progressives (avec options de concision)
def appeler_assistant_ia_stream(question, contexte="", max_tokens=None, limite_caracteres=None, concis=False):
    api_key = None
    try:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
    except Exception:
        api_key = st.session_state.get('api_key', '')
    if not api_key:
        yield "⚠️ Veuillez entrer votre clé API DeepSeek dans la barre latérale ou dans secrets.toml."
        return
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        consigne_concise = ("Réponds de façon concise en 5–7 phrases max, "
                             "avec des points clés si utile, sans longs détails.") if concis else ""
        prompt = f"""Tu es un expert en énergie solaire au Sénégal. Tu connais bien le climat local (chaleur, humidité) et les meilleures pratiques d'installation.
Contexte: {contexte}
Question: {question}
{consigne_concise}
Réponds de manière claire et pratique en français, avec des conseils adaptés au Sénégal."""
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Tu es un expert en installations solaires au Sénégal. Tu aides les utilisateurs à comprendre leurs besoins en énergie solaire et à choisir les bons équipements."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "stream": True
        }
        if max_tokens:
            data["max_tokens"] = max_tokens
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data,
            stream=True,
            timeout=60
        )
        if resp.status_code != 200:
            yield f"❌ Erreur API: {resp.status_code}"
            return
        chars_out = 0
        for raw in resp.iter_lines():
            if not raw:
                continue
            try:
                line = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
            except Exception:
                line = str(raw)
            if line.startswith("data: "):
                payload = line[6:].strip()
                if payload == "[DONE]":
                    break
                try:
                    obj = json.loads(payload)
                    choice = (obj.get("choices") or [{}])[0]
                    delta = choice.get("delta", {})
                    content = delta.get("content") or (choice.get("message", {}) or {}).get("content")
                    if content:
                        if concis and (limite_caracteres is not None):
                            restant = max(0, limite_caracteres - chars_out)
                            if restant <= 0:
                                break
                            morceau = content[:restant]
                            chars_out += len(morceau)
                            if morceau:
                                yield morceau
                            if chars_out >= (limite_caracteres or 0):
                                break
                        else:
                            yield content
                except Exception:
                    continue
    except Exception as e:
        yield f"❌ Erreur: {str(e)}"
        return

# --- Prix en ligne (energiesolairesenegal.com) ---
@st.cache_data(ttl=3600)
def _rechercher_url_produit_solairesenegal(nom: str):
    try:
        url = f"https://energiesolairesenegal.com/?s={quote(nom)}"
        r = requests.get(url, timeout=20)
        html = r.text
        m = re.search(r'href="(https?://[^"]*solairesenegal\\.com/(?:produit|product)/[^"]+)"', html, re.IGNORECASE)
        if m:
            return m.group(1)
    except Exception:
        return None
    return None


def _extraire_prix_fcfa(html: str):
    candidates = re.findall(r'([0-9]{3,9}(?:[\s.,][0-9]{3})*)\s*(?:FCFA|F\s*CFA|CFA)', html, flags=re.IGNORECASE)
    if not candidates:
        return None
    def _to_int(s):
        digits = re.sub(r'[^0-9]', '', s)
        try:
            return int(digits)
        except Exception:
            return None
    vals = [v for v in (_to_int(c) for c in candidates) if v is not None]
    plausible = [v for v in vals if 1000 <= v <= 20000000]
    return max(plausible) if plausible else (max(vals) if vals else None)

@st.cache_data(ttl=3600)
def obtenir_prix_depuis_site(nom_item: str):
    url_prod = _rechercher_url_produit_solairesenegal(nom_item)
    if not url_prod:
        return None, None
    try:
        r = requests.get(url_prod, timeout=20)
        prix = _extraire_prix_fcfa(r.text)
        return prix, url_prod
    except Exception:
        return None, url_prod

# Fonction de dimensionnement améliorée
def calculer_dimensionnement(consommation_journaliere, autonomie_jours=1, voltage=12, type_batterie="AGM", part_nuit=0.5):
    # Paramètres selon le type de batterie
    decharge_max = {
        "Plomb": 0.5,
        "AGM": 0.7,
        "GEL": 0.8,
        "Lithium": 0.9
    }
    
    # Calcul de la puissance panneau nécessaire (avec perte de 25%)
    # 5h d'ensoleillement moyen au Sénégal
    # Sortie en Watts-crête (Wc)
    puissance_panneaux = ((consommation_journaliere * 1.25) / 5) * 1000
    
    # Hypothèse réaliste: charge le jour, décharge la nuit
    # On dimensionne la batterie sur la fraction nocturne de la consommation
    profondeur_decharge = decharge_max.get(type_batterie, 0.7)
    consommation_nocturne = consommation_journaliere * max(0.1, min(part_nuit, 1.0))
    capacite_batterie = (consommation_nocturne * autonomie_jours * 1000) / (voltage * profondeur_decharge)
    
    # Puissance onduleur (pic de consommation estimé à 30% de la conso journalière)
    puissance_onduleur = consommation_journaliere / 3 * 1000  # en W
    
    return {
        "puissance_panneaux": puissance_panneaux,
        "capacite_batterie": capacite_batterie,
        "puissance_onduleur": puissance_onduleur,
        "type_batterie": type_batterie,
        "profondeur_decharge": profondeur_decharge * 100
    }

# Fonction pour sélectionner les équipements
def selectionner_equipements(dimensionnement, choix_utilisateur):
    type_batterie = choix_utilisateur["type_batterie"]
    type_onduleur = choix_utilisateur["type_onduleur"]
    # Supporte l’absence de type_regulateur (ex: onduleur Hybride)
    type_regulateur = choix_utilisateur.get("type_regulateur", "MPPT")
    voltage_systeme = choix_utilisateur["voltage"]
    
    # Sélection panneaux — choisir le module qui minimise le nombre de panneaux
    puissance_panneau_select = None
    nb_panneaux = 0
    puissance_min = dimensionnement["puissance_panneaux"]

    candidats = []
    for nom, specs in PRIX_EQUIPEMENTS["panneaux"].items():
        p = specs["puissance"]
        if p <= 0:
            continue
        nb = math.ceil(puissance_min / p)
        prix_unitaire = specs.get("prix", 0)
        prix_par_watt = prix_unitaire / p if p else float("inf")
        candidats.append((nom, nb, prix_par_watt, -p))  # tie-break par prix/W puis par puissance plus élevée

    if candidats:
        # Trier: moins de panneaux, meilleur prix/W, puissance plus élevée
        candidats.sort(key=lambda x: (x[1], x[2], x[3]))
        puissance_panneau_select, nb_panneaux, _, _ = candidats[0]

    
    # Sélection batterie selon le type choisi
    batterie_select = None
    nb_batteries = 0
    batteries_filtrees = {k: v for k, v in PRIX_EQUIPEMENTS["batteries"].items() 
                         if v["type"] == type_batterie and v["voltage"] == voltage_systeme}
    
    if batteries_filtrees:
        for nom, specs in sorted(batteries_filtrees.items(), key=lambda x: x[1]["capacite"]):
            if specs["capacite"] >= dimensionnement["capacite_batterie"]:
                batterie_select = nom
                nb_batteries = 1
                break
        
        # Si aucune batterie assez grande, prendre plusieurs petites
        if not batterie_select:
            nom_batterie = max(batteries_filtrees.keys(), key=lambda x: batteries_filtrees[x]["capacite"])
            specs = batteries_filtrees[nom_batterie]
            nb_batteries = int(dimensionnement["capacite_batterie"] / specs["capacite"]) + 1
            batterie_select = nom_batterie
    
    # Sélection onduleur selon le type choisi
    onduleur_select = None
    onduleurs_filtres = {k: v for k, v in PRIX_EQUIPEMENTS["onduleurs"].items() 
                        if type_onduleur in v["type"] and v["voltage"] == voltage_systeme}
    
    if onduleurs_filtres:
        for nom, specs in sorted(onduleurs_filtres.items(), key=lambda x: x[1]["puissance"]):
            if specs["puissance"] >= dimensionnement["puissance_onduleur"]:
                onduleur_select = nom
                break
    
    # Sélection régulateur (seulement si onduleur pas hybride)
    regulateur_select = None
    if type_onduleur != "Hybride" and puissance_panneau_select and batterie_select:
        puissance_panneaux_totale = nb_panneaux * PRIX_EQUIPEMENTS["panneaux"][puissance_panneau_select]["puissance"]
        amperage_requis = (puissance_panneaux_totale / voltage_systeme) * 1.25
        
        regulateurs_filtres = {k: v for k, v in PRIX_EQUIPEMENTS["regulateurs"].items() 
                              if v["type"] == type_regulateur}
        
        for nom, specs in sorted(regulateurs_filtres.items(), key=lambda x: x[1]["amperage"]):
            if specs["amperage"] >= amperage_requis:
                regulateur_select = nom
                break
    
    return {
        "panneau": (puissance_panneau_select, nb_panneaux),
        "batterie": (batterie_select, nb_batteries),
        "onduleur": onduleur_select,
        "regulateur": regulateur_select,
    }

# Estimation kWh mensuels à partir d'une facture Senelec
# Note: approximation des paliers, hors frais fixes/abonnement/taxes.
def estimer_kwh_depuis_facture(montant_fcfa: float, type_compteur: str = "mensuel") -> float:
    try:
        m = float(montant_fcfa)
    except Exception:
        return 0.0
    if m <= 0:
        return 0.0
    # Paliers selon type de compteur
    if type_compteur.lower().startswith("bimes"):
        p1_kwh, p2_kwh = 300.0, 200.0  # 2 mois
    else:
        p1_kwh, p2_kwh = 150.0, 100.0  # 1 mois
    cout_p1 = p1_kwh * 124.17
    cout_p2 = p2_kwh * 136.49
    if m <= cout_p1:
        return m / 124.17
    elif m <= cout_p1 + cout_p2:
        return p1_kwh + (m - cout_p1) / 136.49
    else:
        return p1_kwh + p2_kwh + (m - cout_p1 - cout_p2) / 159.36

# Fonction pour calculer le devis
def calculer_devis(equipements, use_online=False, accessoires_rate=0.15):
    total = 0
    details = []
    
    # Panneaux
    panneau_nom, nb_panneaux = equipements["panneau"]
    if panneau_nom:
        prix_unitaire = PRIX_EQUIPEMENTS["panneaux"][panneau_nom]["prix"]
        source_prix = "local"
        url_source = None
        if use_online:
            prix_site, url_site = obtenir_prix_depuis_site(panneau_nom)
            if prix_site:
                prix_unitaire = prix_site
                source_prix = "site"
                url_source = url_site
        sous_total = prix_unitaire * nb_panneaux
        total += sous_total
        details.append({
            "item": f"Panneau solaire {panneau_nom}",
            "quantite": nb_panneaux,
            "prix_unitaire": prix_unitaire,
            "sous_total": sous_total,
            "source_prix": source_prix,
            "url_source": url_source
        })
    
    # Batteries
    batterie_nom, nb_batteries = equipements["batterie"]
    if batterie_nom:
        prix_unitaire = PRIX_EQUIPEMENTS["batteries"][batterie_nom]["prix"]
        source_prix = "local"
        url_source = None
        if use_online:
            prix_site, url_site = obtenir_prix_depuis_site(batterie_nom)
            if prix_site:
                prix_unitaire = prix_site
                source_prix = "site"
                url_source = url_site
        sous_total = prix_unitaire * nb_batteries
        total += sous_total
        details.append({
            "item": f"Batterie {batterie_nom}",
            "quantite": nb_batteries,
            "prix_unitaire": prix_unitaire,
            "sous_total": sous_total,
            "source_prix": source_prix,
            "url_source": url_source
        })
    
    # Onduleur
    onduleur_nom = equipements["onduleur"]
    if onduleur_nom:
        prix_unitaire = PRIX_EQUIPEMENTS["onduleurs"][onduleur_nom]["prix"]
        source_prix = "local"
        url_source = None
        if use_online:
            prix_site, url_site = obtenir_prix_depuis_site(onduleur_nom)
            if prix_site:
                prix_unitaire = prix_site
                source_prix = "site"
                url_source = url_site
        total += prix_unitaire
        details.append({
            "item": f"Onduleur {onduleur_nom}",
            "quantite": 1,
            "prix_unitaire": prix_unitaire,
            "sous_total": prix_unitaire,
            "source_prix": source_prix,
            "url_source": url_source
        })
    
    # Régulateur (si nécessaire)
    regulateur_nom = equipements["regulateur"]
    if regulateur_nom:
        prix_unitaire = PRIX_EQUIPEMENTS["regulateurs"][regulateur_nom]["prix"]
        source_prix = "local"
        url_source = None
        if use_online:
            prix_site, url_site = obtenir_prix_depuis_site(regulateur_nom)
            if prix_site:
                prix_unitaire = prix_site
                source_prix = "site"
                url_source = url_site
        total += prix_unitaire
        details.append({
            "item": f"Régulateur {regulateur_nom}",
            "quantite": 1,
            "prix_unitaire": prix_unitaire,
            "sous_total": prix_unitaire,
            "source_prix": source_prix,
            "url_source": url_source
        })
    
    # Accessoires (câbles, connecteurs, protections, structure)
    accessoires = int(total * accessoires_rate)
    total += accessoires
    details.append({
        "item": "Accessoires (câbles, connecteurs, protections, structure)",
        "quantite": 1,
        "prix_unitaire": accessoires,
        "sous_total": accessoires,
        "source_prix": f"taux {int(accessoires_rate*100)}%",
        "url_source": None
    })
    
    # Installation
    puissance_totale = 0
    if panneau_nom:
        puissance_totale = nb_panneaux * PRIX_EQUIPEMENTS["panneaux"][panneau_nom]["puissance"] / 1000
    
    # Installation (forfait fixe demandé)
    installation = 200000
    
    total += installation
    details.append({
        "item": "Installation et mise en service",
        "quantite": 1,
        "prix_unitaire": installation,
        "sous_total": installation,
        "source_prix": "forfait",
        "url_source": None
    })
    
    return {"details": details, "total": total, "puissance_totale": puissance_totale}

# Interface principale
st.title("☀️ Dimensionnement d'Installation Solaire - Sénégal")
st.markdown("### Calculez votre installation solaire complète et obtenez un devis estimatif détaillé")

# Barre latérale pour la configuration
with st.sidebar:
    st.header("🔧 Configuration")
    
    # Clé API gérée via st.secrets (pas de configuration dans la sidebar)
    
    st.markdown("---")
    st.markdown("### ☀️ Conseiller solaire (chat rapide)")
    
    # Callback: déclenché à l'appui sur Entrée
    def _trigger_sidebar_chat():
        st.session_state.sidebar_chat_go = True
    
    q_sidebar = st.text_input(
        "Votre question au conseiller",
        placeholder="Ex: Décrivez vos appareils ou votre besoin",
        key="sidebar_chat_q",
        on_change=_trigger_sidebar_chat
    )
    
    # Soumission automatique sur Entrée
    if st.session_state.get("sidebar_chat_go"):
        if q_sidebar and len(q_sidebar.strip()) > 5:
            # Construit un contexte synthétique depuis l'état courant
            contexte_sb = ""
            if 'dimensionnement' in st.session_state:
                dim = st.session_state.dimensionnement
                choix = st.session_state.choix
                equip_actifs_ctx = st.session_state.get('equip_choisi', st.session_state.get('equipements', None))
                prod_kwh_j_ctx = 0.0
                auto_reelle_ctx = (st.session_state.autonomie_reelle_pct if 'autonomie_reelle_pct' in st.session_state else None)
                if not auto_reelle_ctx and equip_actifs_ctx and equip_actifs_ctx.get('panneau'):
                    pn_ctx, nb_ctx = equip_actifs_ctx['panneau']
                    if pn_ctx and nb_ctx > 0:
                        p_unit_ctx = PRIX_EQUIPEMENTS['panneaux'][pn_ctx]['puissance']
                        p_tot_ctx = p_unit_ctx * nb_ctx
                        prod_kwh_j_ctx = (p_tot_ctx / 1000.0) * 5.0 * 0.75
                conso_totale_ctx = st.session_state.consommation if 'consommation' in st.session_state else 10.0
                conso_couverte_ctx = st.session_state.get('consommation_couverte', None)
                autonomie_voulue_ctx = choix.get('autonomie_h', None)
                pack_info = f"{choix.get('type_batterie','?')} / {choix.get('type_onduleur','?')} / {('MPPT' if choix.get('type_regulateur')=='MPPT' else 'PWM' if choix.get('type_regulateur')=='PWM' else 'auto')} @ {choix.get('voltage', 12)}V"
                contexte_sb = f"Conso quotidienne: {conso_totale_ctx} kWh/j ; Couverture cible: {conso_couverte_ctx or 'N/A'} kWh/j ; Prod estimée: {round(prod_kwh_j_ctx,2)} kWh/j ; Autonomie cible: {autonomie_voulue_ctx or 'N/A'} h ; Pack choisi: {pack_info}"
            with st.spinner("🤔 Le conseiller répond en streaming (réponse courte)..."):
                st.write_stream(appeler_assistant_ia_stream(q_sidebar, contexte_sb, concis=True, max_tokens=220, limite_caracteres=700))
            st.session_state.sidebar_chat_go = False
            st.caption("Réponse abrégée. Pour plus de détails, utilisez l’onglet Conseiller solaire.")
        else:
            st.session_state.sidebar_chat_go = False
            st.warning("⚠️ Veuillez entrer une question (minimum 6 caractères)")
    
    st.markdown("---")
    st.markdown("### À propos")
    st.info("Application complète de dimensionnement solaire avec tous les types d'équipements disponibles sur le marché sénégalais.")

# Onglets principaux
tab1, tab2, tab3 = st.tabs(["📊 Dimensionnement", "💰 Devis", "☀️ Conseiller solaire"])

with tab1:
    st.header("Calculez vos besoins en énergie solaire")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1️⃣ Consommation")
        mode_calcul = st.radio("Méthode de calcul", ["Simple", "Détaillée"], horizontal=True)
        
        if mode_calcul == "Simple":
            consommation_simple = st.number_input(
                "Consommation électrique journalière (kWh/jour)",
                min_value=0.5,
                max_value=100.0,
                value=st.session_state.get("conso_journaliere_input", 10.0),
                step=0.5,
                help="Estimez votre consommation quotidienne moyenne",
                key="conso_journaliere_input"
            )
            with st.expander("🧮 Estimer depuis facture Senelec", expanded=False):
                type_compteur = st.selectbox(
                    "Type de compteur",
                    ["Normal (bimestriel)", "Woyofal (mensuel)"],
                    index=1,
                    key="type_compteur_select"
                )
                def _update_conso_from_montant():
                    montant_val = st.session_state.get("montant_fcfa_input", 0)
                    periodicite = "bimestriel" if "bimestriel" in st.session_state.get("type_compteur_select", "").lower() else "mensuel"
                    kwh_mensuel_estime = estimer_kwh_depuis_facture(montant_val, periodicite)
                    jours_cycle = 60 if periodicite == "bimestriel" else 30
                    conso_jour_estimee = kwh_mensuel_estime / jours_cycle if kwh_mensuel_estime > 0 else 0.0
                    # On écrit directement dans le champ principal
                    st.session_state.use_estimation = False
                    st.session_state.consommation_estimee = None
                    st.session_state["conso_journaliere_input"] = round(conso_jour_estimee, 2)
                montant_fcfa = st.number_input(
                    "Montant facture/achat (FCFA)",
                    min_value=0,
                    max_value=10000000,
                    value=st.session_state.get("montant_fcfa_input", 0),
                    step=1000,
                    help="Estimation approximative hors frais fixes/abonnements",
                    key="montant_fcfa_input",
                    on_change=_update_conso_from_montant
                )
                kwh_mensuel_estime = estimer_kwh_depuis_facture(
                    montant_fcfa,
                    "bimestriel" if "bimestriel" in type_compteur.lower() else "mensuel"
                )
                jours_cycle = 60 if "bimestriel" in type_compteur.lower() else 30
                conso_jour_estimee = kwh_mensuel_estime / jours_cycle if kwh_mensuel_estime > 0 else 0.0
                st.info(f"Estimation: {kwh_mensuel_estime:.0f} kWh/mois • {conso_jour_estimee:.2f} kWh/jour")
                col_est1, col_est2 = st.columns(2)
                with col_est1:
                    use_est = st.button("Utiliser cette estimation", key="use_estimation_btn")
                with col_est2:
                    reset_est = st.button("Revenir à la saisie manuelle", key="reset_estimation_btn")
                if use_est:
                    st.session_state.use_estimation = True
                    st.session_state.consommation_estimee = conso_jour_estimee
                if reset_est:
                    st.session_state.use_estimation = False
                    st.session_state.consommation_estimee = None
            if st.session_state.get("use_estimation", False) and st.session_state.get("consommation_estimee"):
                consommation_finale = float(st.session_state.consommation_estimee)
                st.success(f"✅ Estimation utilisée: {consommation_finale:.2f} kWh/jour")
            else:
                consommation_finale = consommation_simple
        else:
            with st.expander("📱 Calculer par appareils", expanded=True):
                st.markdown("Sélectionnez une famille d’appareils, choisissez un appareil et ajoutez-le.")
                
                # Initialisation de la liste sélectionnée
                if 'appareils_selectionnes' not in st.session_state:
                    st.session_state.appareils_selectionnes = []
                consommation_rapide = 0.0
                
                tab_cat, tab_rapide = st.tabs(["Catalogue par familles", "Liste rapide"])
                
                with tab_cat:
                    col_sel1, col_sel2 = st.columns(2)
                    famille = col_sel1.selectbox("Famille d'appareils", sorted(APPAREILS_FAMILLES.keys()))
                    appareils_list = APPAREILS_FAMILLES.get(famille, [])
                    noms_list = [a['nom'] for a in appareils_list]
                    appareil_nom = col_sel2.selectbox("Appareil", noms_list, index=0)
                    app_sel = next((a for a in appareils_list if a['nom'] == appareil_nom), None)
                    p_typ = app_sel['puissance'] if app_sel else 10
                    col_in1, col_in2, col_in3 = st.columns([1, 1, 1])
                    quant = col_in1.number_input("Nombre", min_value=0, max_value=50, value=1, step=1)
                    heures = col_in2.number_input("Heures/jour", min_value=0.0, max_value=24.0, value=6.0, step=0.5)
                    puissance_w = col_in3.number_input("Puissance (W)", min_value=1, max_value=5000, value=int(p_typ), step=10)
                    add_btn = st.button("➕ Ajouter cet appareil", use_container_width=True)
                    if add_btn:
                        if quant > 0 and heures > 0 and puissance_w > 0:
                            st.session_state.appareils_selectionnes.append({
                                "famille": famille,
                                "nom": appareil_nom,
                                "puissance": puissance_w,
                                "quantite": int(quant),
                                "heures": float(heures),
                                "kwh_j": (int(quant) * puissance_w * float(heures)) / 1000.0
                            })
                            st.success(f"Ajouté: {appareil_nom} • {quant} × {puissance_w}W • {heures} h/j")
                
                    # Ajouter via Conseiller solaire (sans expander)
                    show_ai = st.checkbox("Ajouter via Conseiller solaire (mots-clés simples)", value=False, key="ai_show_checkbox")
                    if show_ai:
                        phrase = st.text_input("Décrivez vos appareils (ex: 2 tv, 1 frigo, routeur wifi)", key="ai_phrase_input")
                        if st.button("Proposer et ajouter", key="ai_proposer_btn"):
                            tokens = re.findall(r"\w+", phrase.lower())
                            last_num = 1
                            for tk in tokens:
                                if tk.isdigit():
                                    try:
                                        last_num = int(tk)
                                    except Exception:
                                        last_num = 1
                                    continue
                                if tk in APPAREILS_KEYWORDS:
                                    fam, nom = APPAREILS_KEYWORDS[tk]
                                    appareils_fam = APPAREILS_FAMILLES.get(fam, [])
                                    app_def = next((a for a in appareils_fam if a['nom'] == nom), None)
                                    p = app_def['puissance'] if app_def else 10
                                    st.session_state.appareils_selectionnes.append({
                                        "famille": fam,
                                        "nom": nom,
                                        "puissance": p,
                                        "quantite": last_num,
                                        "heures": 6.0,
                                        "kwh_j": (last_num * p * 6.0) / 1000.0
                                    })
                                    last_num = 1
                            st.success("Suggestions ajoutées. Ajustez les heures ou puissances au besoin.")
                        st.caption("Mots-clés: tv, frigo, ventilateur, ordi, laptop, routeur, pompe, micro, bouilloire")
                
                with tab_rapide:
                    st.markdown("*Liste rapide (optionnelle) pour quelques appareils courants*")
                    col_a, col_b, col_c = st.columns([2, 1, 1])
                    with col_a:
                        st.markdown("**Appareil**")
                    with col_b:
                        st.markdown("**Nombre**")
                    with col_c:
                        st.markdown("**Heures/jour**")
                    
                    appareils_conso = {}
                    
                    st.markdown("🔦 **Éclairage**")
                    col_a, col_b, col_c = st.columns([2, 1, 1])
                    with col_b:
                        nb_led = st.number_input("", 0, 50, 0, key="led", label_visibility="collapsed")
                    with col_c:
                        h_led = st.number_input("", 1, 24, 6, key="h_led", label_visibility="collapsed")
                    appareils_conso["LED 10W"] = nb_led * 10 * h_led / 1000
                    
                    st.markdown("💨 **Ventilation**")
                    col_a, col_b, col_c = st.columns([2, 1, 1])
                    with col_b:
                        nb_vent = st.number_input("", 0, 20, 0, key="vent", label_visibility="collapsed")
                    with col_c:
                        h_vent = st.number_input("", 1, 24, 10, key="h_vent", label_visibility="collapsed")
                    appareils_conso["Ventilateur 75W"] = nb_vent * 75 * h_vent / 1000
                    
                    st.markdown("📺 **Électroménager**")
                    col_a, col_b, col_c = st.columns([2, 1, 1])
                    with col_b:
                        nb_tv = st.number_input("TV", 0, 10, 0, key="tv", label_visibility="collapsed")
                    with col_c:
                        h_tv = st.number_input("", 1, 24, 6, key="h_tv", label_visibility="collapsed")
                    appareils_conso["TV 100W"] = nb_tv * 100 * h_tv / 1000
                    
                    col_a, col_b, col_c = st.columns([2, 1, 1])
                    with col_b:
                        nb_frigo = st.number_input("Frigo", 0, 5, 0, key="frigo", label_visibility="collapsed")
                    with col_c:
                        h_frigo = st.number_input("", 8, 24, 12, key="h_frigo", label_visibility="collapsed")
                    appareils_conso["Réfrigérateur 150W"] = nb_frigo * 150 * h_frigo / 1000
                    
                    st.markdown("💻 **Informatique**")
                    col_a, col_b, col_c = st.columns([2, 1, 1])
                    with col_b:
                        nb_pc = st.number_input("Ordi", 0, 10, 0, key="pc", label_visibility="collapsed")
                    with col_c:
                        h_pc = st.number_input("", 1, 24, 8, key="h_pc", label_visibility="collapsed")
                    appareils_conso["Ordinateur 200W"] = nb_pc * 200 * h_pc / 1000
                    
                    consommation_rapide = sum(appareils_conso.values())
                
                # Tableau et total
                if st.session_state.appareils_selectionnes:
                    st.markdown("### Appareils sélectionnés")
                    for i, it in enumerate(st.session_state.appareils_selectionnes):
                        col_a, col_b, col_c, col_d, col_e, col_f = st.columns([3, 1, 1, 1, 1, 1])
                        col_a.write(f"{it['famille']} • {it['nom']}")
                        col_b.write(f"{it['quantite']}")
                        col_c.write(f"{it['puissance']} W")
                        col_d.write(f"{it['heures']} h/j")
                        col_e.write(f"{it['kwh_j']:.2f} kWh/j")
                        if col_f.button("🗑️", key=f"rm_{i}"):
                            st.session_state.appareils_selectionnes.pop(i)
                            st.rerun()
                    conso_familles = sum([x['kwh_j'] for x in st.session_state.appareils_selectionnes])
                else:
                    conso_familles = 0.0
                
                consommation_finale = conso_familles + consommation_rapide
                st.success(f"**Consommation totale: {consommation_finale:.2f} kWh/jour**")
        
        # Répartition jour/nuit et week-end
        with st.expander("🌙 Répartition jour/nuit et week-end", expanded=False):
            part_jour = st.slider("Part jour (%)", 0, 100, 45, step=1, help="Pour ménages: nuit souvent plus élevée")
            part_nuit = 100 - part_jour
            facteur_weekend = st.slider("Facteur week-end (%)", 80, 150, 110, step=5, help="Ex: 110% = +10% de conso le week-end")
            # Moyenne jour/nuit en tenant compte du week-end (5 jours semaine + 2 jours weekend)
            conso_jour_semaine = consommation_finale * (part_jour/100) * 5
            conso_nuit_semaine = consommation_finale * (part_nuit/100) * 5
            conso_jour_weekend = consommation_finale * (part_jour/100) * (facteur_weekend/100) * 2
            conso_nuit_weekend = consommation_finale * (part_nuit/100) * (facteur_weekend/100) * 2
            conso_jour_moy = (conso_jour_semaine + conso_jour_weekend) / 7
            conso_nuit_moy = (conso_nuit_semaine + conso_nuit_weekend) / 7
            col_rep1, col_rep2, col_rep3 = st.columns(3)
            with col_rep1:
                st.metric("Jour moyen", f"{conso_jour_moy:.2f} kWh/jour")
            with col_rep2:
                st.metric("Nuit moyenne", f"{conso_nuit_moy:.2f} kWh/jour")
            with col_rep3:
                st.metric("Total", f"{(conso_jour_moy+conso_nuit_moy):.2f} kWh/jour")
            # Sauvegarde profil dans session
            st.session_state.usage_profile = {
                "part_jour": part_jour,
                "part_nuit": part_nuit,
                "facteur_weekend": facteur_weekend,
                "jour_moy": conso_jour_moy,
                "nuit_moy": conso_nuit_moy
            }
    
    with col2:
        st.subheader("2️⃣ Configuration du Système")
        
        # Type de batterie
        type_batterie = st.selectbox(
            "🔋 Type de batterie",
            ["Plomb", "AGM", "GEL", "Lithium"],
            index=3,
            help="AGM recommandé pour le climat sénégalais"
        )
        
        # Affichage des caractéristiques de la batterie choisie
        with st.expander(f"ℹ️ Pourquoi {type_batterie} ?"):
            info = INFO_BATTERIES[type_batterie]
            st.markdown(info["avantages"])
            st.markdown(info["inconvenients"])
            st.info(f"💡 **Recommandé pour:** {info['usage']}")
        
        # Type d'onduleur
        type_onduleur = st.selectbox(
            "⚡ Type d'onduleur",
            ["Off-Grid", "Hybride", "Online"],
            index=1,
            help="Hybride = avec régulateur MPPT intégré"
        )
        
        
        # Type de régulateur (si nécessaire)
        type_regulateur = "MPPT"
        if type_onduleur != "Hybride":
            type_regulateur = st.selectbox(
                "🎛️ Type de régulateur",
                ["PWM", "MPPT"],
                index=1,
                help="MPPT 30% plus efficace que PWM"
            )
            if type_regulateur == "MPPT":
                st.success("✅ MPPT = 30% de rendement en plus")
            else:
                st.warning("⚠️ PWM = moins cher mais moins efficace")
        
        # Voltage du système
        voltage = st.selectbox(
            "⚡ Voltage du système",
            [12, 24, 48],
            index=2,
            help="24V recommandé pour usage domestique"
        )
        
        # Niveau d'autonomie (pourcentage de besoins couverts)
        autonomie_pct = st.slider(
            "🔄 Niveau d’autonomie (%)",
            min_value=0,
            max_value=100,
            value=100,
            step=5,
            help="Objectif de couverture souhaitée par le solaire (cible)"
        )
    
    # Bouton de calcul
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        calculer_btn = st.button("🔍 CALCULER LE DIMENSIONNEMENT", type="primary", use_container_width=True)
    
    if calculer_btn:
        if consommation_finale > 0:
            with st.spinner("⚙️ Calcul en cours..."):
                # Calcul du dimensionnement avec niveau d’autonomie appliqué
                consommation_couverte = consommation_finale * autonomie_pct / 100.0
                dim = calculer_dimensionnement(consommation_couverte, voltage=voltage, type_batterie=type_batterie)
                
                # Choix utilisateur
                choix_utilisateur = {
                    "type_batterie": type_batterie,
                    "type_onduleur": type_onduleur,
                    "type_regulateur": type_regulateur,
                    "voltage": voltage
                }
                
                # Sélection des équipements
                equip = selectionner_equipements(dim, choix_utilisateur)
                
                # Sauvegarde dans session
                st.session_state.dimensionnement = dim
                st.session_state.equipements = equip
                st.session_state.consommation = consommation_finale  # totale
                st.session_state.consommation_couverte = consommation_couverte
                st.session_state.autonomie_pct = autonomie_pct
                st.session_state.choix = choix_utilisateur
                
                st.success("✅ Dimensionnement effectué avec succès !")
                
                # Affichage des résultats
                st.markdown("---")
                st.markdown("## 📊 Résultats du Dimensionnement")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "🌞 Panneaux Solaires",
                        f"{dim['puissance_panneaux']:.0f} Wc",
                        help="Puissance crête totale nécessaire"
                    )
                    panneau_nom, nb = equip["panneau"]
                    if panneau_nom:
                        st.info(f"**{nb} x {panneau_nom}**")
                
                with col2:
                    st.metric(
                        "🔋 Batteries",
                        f"{dim['capacite_batterie']:.0f} Ah",
                        help=f"Capacité à {voltage}V avec décharge max {dim['profondeur_decharge']:.0f}%"
                    )
                    batterie_nom, nb = equip["batterie"]
                    if batterie_nom:
                        st.info(f"**{nb} x {batterie_nom}**")
                
                with col3:
                    st.metric(
                        "⚡ Onduleur",
                        f"{dim['puissance_onduleur']:.0f} W",
                        help="Puissance de l'onduleur"
                    )
                    if equip["onduleur"]:
                        st.info(f"**{equip['onduleur']}**")
                
                                # 📅 Simulateur de production mensuelle (Sénégal)
                kWc = dim['puissance_panneaux'] / 1000.0
                heures_par_jour = {
                    'Jan': 6.2, 'Fév': 6.5, 'Mar': 6.7, 'Avr': 6.6, 'Mai': 6.5, 'Juin': 6.0,
                    'Juil': 5.5, 'Août': 5.4, 'Sep': 5.8, 'Oct': 6.0, 'Nov': 6.2, 'Déc': 6.1
                }
                jours_mois = {'Jan':31,'Fév':28,'Mar':31,'Avr':30,'Mai':31,'Juin':30,'Juil':31,'Août':31,'Sep':30,'Oct':31,'Nov':30,'Déc':31}
                PR = 0.80

                data = []
                for m in heures_par_jour:
                    prod = kWc * heures_par_jour[m] * PR * jours_mois[m]
                    data.append({'Mois': m, 'Production (kWh)': round(prod, 2)})

                df_prod = pd.DataFrame(data)

                st.subheader("📅 Simulateur de production mensuelle")
                st.bar_chart(df_prod.set_index('Mois'))

                st.caption("Estimation basée sur l'ensoleillement moyen au Sénégal; impact saison des pluies intégré.")

                # Régulateur si nécessaire
                if equip["regulateur"]:
                    st.markdown("### 🎛️ Régulateur de charge")
                    st.info(f"**{equip['regulateur']}**")
                
                # Avertissements et recommandations
                st.markdown("---")
                st.markdown("### 💡 Recommandations")
                
                col_rec1, col_rec2 = st.columns(2)
                
                with col_rec1:
                    if type_batterie == "Lithium":
                        st.success("✅ Excellent choix ! Les batteries Lithium durent 3x plus longtemps")
                    elif type_batterie == "GEL":
                        st.success("✅ Très bon choix pour le climat sénégalais")
                    elif type_batterie == "AGM":
                        st.info("👍 Bon compromis qualité/prix pour le Sénégal")
                    else:
                        st.warning("⚠️ Batteries plomb nécessitent un entretien régulier (eau distillée)")
                
                with col_rec2:
                    if type_regulateur == "MPPT" or type_onduleur == "Hybride":
                        st.success("✅ MPPT recommandé : +30% de rendement")
                    else:
                        st.info("💡 Conseil : MPPT serait 30% plus efficace")
        else:
            st.error("❌ Veuillez entrer une consommation supérieure à 0")

with tab2:
    st.header("💰 Devis Estimatif Détaillé")
    
    if 'equipements' not in st.session_state:
        st.warning("⚠️ Veuillez d'abord effectuer un dimensionnement dans l'onglet 'Dimensionnement'")
    else:
        st.markdown("### ⚙️ Options du devis")
        use_online = st.checkbox(
            "Utiliser les prix en ligne (energiesolairesenegal.com)",
            help="Recherche automatique des prix par référence sur energiesolairesenegal.com"
        )
        accessoires_pct = st.slider("Taux accessoires (%)", 5, 20, 15, step=1, help="Inclut câbles, connecteurs, protections, structure, etc.", key="accessoires_pct_devis")
        devis = calculer_devis(st.session_state.equipements, use_online=use_online, accessoires_rate=accessoires_pct/100.0)
        
        # Résumé du système
        st.markdown("### 📋 Résumé de votre installation")
        col_info1, col_info2, col_info3 = st.columns(3)
        
        with col_info1:
            st.metric("Consommation", f"{st.session_state.consommation:.1f} kWh/jour")
        with col_info2:
            st.metric("Puissance totale", f"{devis['puissance_totale']:.2f} kWc")
        with col_info3:
            st.metric("Type système", f"{st.session_state.choix['voltage']}V {st.session_state.choix['type_batterie']}")
        
        st.caption(f"🎯 Autonomie souhaitée: {(st.session_state.autonomie_pct if 'autonomie_pct' in st.session_state else 100)}% • Estimée: {(st.session_state.autonomie_reelle_pct if 'autonomie_reelle_pct' in st.session_state else (st.session_state.autonomie_pct if 'autonomie_pct' in st.session_state else 100)):.0f}%")
        
        st.markdown("---")
        st.markdown("### 📦 Détails du devis")
        
        # En-tête du tableau
        col_header1, col_header2, col_header3, col_header4 = st.columns([3, 1, 2, 2])
        with col_header1:
            st.markdown("**Équipement**")
        with col_header2:
            st.markdown("**Qté**")
        with col_header3:
            st.markdown("**Prix unitaire**")
        with col_header4:
            st.markdown("**Sous-total**")
        
        st.divider()
        
        # Lignes du devis
        for item in devis["details"]:
            col1, col2, col3, col4 = st.columns([3, 1, 2, 2])
            with col1:
                st.write(f"{item['item']}")
                if item.get('source_prix') == 'site':
                    url = item.get('url_source') or 'https://energiesolairesenegal.com/'
                    st.markdown(f"<span style='font-size:0.85em;color:#1f77b4'>Source: <a href='{url}' target='_blank'>energiesolairesenegal.com</a></span>", unsafe_allow_html=True)
                elif item.get('source_prix'):
                    st.caption(f"Source: {item.get('source_prix')}")
            with col2:
                st.write(f"x{item['quantite']}")
            with col3:
                st.write(f"{item['prix_unitaire']:,} FCFA")
            with col4:
                st.write(f"**{item['sous_total']:,} FCFA**")
            st.divider()
        
        # Total avec mise en forme
        st.markdown("---")
        col_total1, col_total2 = st.columns([3, 1])
        with col_total1:
            st.markdown("## 💰 **TOTAL ESTIMATIF**")
        with col_total2:
            st.markdown(f"## **{devis['total']:,} FCFA**")
        
        # Estimation facture électricité (Senelec)
        st.markdown("---")
        st.markdown("### ⚡ Estimation facture électricité (Senelec)")
        kwh_mensuel_total = (st.session_state.consommation if 'consommation' in st.session_state else 10.0) * 30

        # Production solaire estimée à partir des équipements actifs (option choisie ou dimensionnement)
        equip_actifs = st.session_state.get('equip_choisi', st.session_state.get('equipements', None))
        prod_kwh_j = 0.0
        autonomie_reelle_pct = 0.0
        if equip_actifs and equip_actifs.get('panneau'):
            panneau_nom, nb = equip_actifs['panneau']
            if panneau_nom and nb > 0:
                puissance_unitaire = PRIX_EQUIPEMENTS['panneaux'][panneau_nom]['puissance']
                puissance_totale_w = puissance_unitaire * nb
                # 5h d'ensoleillement/jour avec pertes ~25%
                prod_kwh_j = (puissance_totale_w / 1000.0) * 5.0 * 0.75
                conso_totale = st.session_state.consommation if 'consommation' in st.session_state else 10.0
                autonomie_reelle_pct = min(100.0, (prod_kwh_j / conso_totale) * 100.0)

        kwh_mensuel_solaire = prod_kwh_j * 30.0
        kwh_mensuel_apres = max(kwh_mensuel_total - kwh_mensuel_solaire, 0.0)

        # Sauvegarde pour autres sections
        st.session_state.production_solaire_kwh_j = prod_kwh_j
        st.session_state.autonomie_reelle_pct = autonomie_reelle_pct

        # Calcul coût Senelec après solaire
        palier1 = min(150.0, kwh_mensuel_apres)
        palier2 = min(max(kwh_mensuel_apres - 150.0, 0.0), 100.0)
        palier3 = max(kwh_mensuel_apres - 250.0, 0.0)
        cout_mensuel_senelec = palier1 * 124.17 + palier2 * 136.49 + palier3 * 159.36

        # Affichage en montants (FCFA/mois)
        palier1_av = min(150.0, kwh_mensuel_total)
        palier2_av = min(max(kwh_mensuel_total - 150.0, 0.0), 100.0)
        palier3_av = max(kwh_mensuel_total - 250.0, 0.0)
        cout_mensuel_avant = palier1_av * 124.17 + palier2_av * 136.49 + palier3_av * 159.36
        economie_mensuelle = max(cout_mensuel_avant - cout_mensuel_senelec, 0.0)

        col_sen1, col_sen2, col_sen3 = st.columns(3)
        with col_sen1:
            st.metric("Avant solaire", f"{cout_mensuel_avant:,.0f} FCFA/mois")
        with col_sen2:
            st.metric("Après solaire estimé", f"{cout_mensuel_senelec:,.0f} FCFA/mois")
        with col_sen3:
            st.metric("Économie estimée", f"{economie_mensuelle:,.0f} FCFA/mois")
        st.caption(f"Couverture réelle estimée: {autonomie_reelle_pct:.0f}%")
        
        # Informations de paiement
        st.markdown("---")
        st.markdown("### 💳 Options de paiement")
        col_pay1, col_pay2, col_pay3 = st.columns(3)
        
        with col_pay1:
            st.info(f"**Comptant**\n\n{devis['total']:,} FCFA")
        
        with col_pay2:
            mensualite_12 = devis['total'] / 12 * 1.1  # +10% d'intérêt
            st.info(f"**12 mois**\n\n{mensualite_12:,.0f} FCFA/mois")
        
        with col_pay3:
            mensualite_24 = devis['total'] / 24 * 1.15  # +15% d'intérêt
            st.info(f"**24 mois**\n\n{mensualite_24:,.0f} FCFA/mois")
        
        # Notes importantes
        st.markdown("---")
        st.markdown("### 📝 Notes importantes")
        st.warning("""
        **Ce devis est une estimation basée sur :**
        - Les prix moyens du marché sénégalais
        - Les équipements disponibles chez les fournisseurs locaux
        - Une installation standard
        
        **Le prix final peut varier selon :**
        - La complexité de l'installation
        - L'accessibilité du site
        - Les promotions en cours
        - Le fournisseur choisi
        """)
        
        # Économies sur 10 ans
        st.markdown("---")
        st.markdown("### 💡 Analyse financière")
        
        # Calcul des économies basées sur la couverture réelle
        cout_electricite_kwh = 100  # FCFA par kWh (Senelec)
        conso_couverte_reelle = st.session_state.production_solaire_kwh_j if 'production_solaire_kwh_j' in st.session_state else (st.session_state.consommation_couverte if 'consommation_couverte' in st.session_state else st.session_state.consommation)
        conso_totale = st.session_state.consommation if 'consommation' in st.session_state else conso_couverte_reelle
        conso_couverte_reelle = min(conso_couverte_reelle, conso_totale)
        economie_annuelle = conso_couverte_reelle * 365 * cout_electricite_kwh
        economie_10ans = economie_annuelle * 10
        retour_investissement = devis['total'] / economie_annuelle if economie_annuelle > 0 else float('inf')
        
        col_eco1, col_eco2, col_eco3 = st.columns(3)
        
        with col_eco1:
            st.metric("💰 Économie annuelle", f"{economie_annuelle:,.0f} FCFA")
        with col_eco2:
            st.metric("📈 Économie sur 10 ans", f"{economie_10ans:,.0f} FCFA")
        with col_eco3:
            st.metric("⏱️ Retour sur investissement", f"{retour_investissement:.1f} ans")
        
        if retour_investissement < 5:
            st.success(f"✅ Excellent investissement ! Rentabilisé en {retour_investissement:.1f} ans")
        elif retour_investissement < 8:
            st.info(f"👍 Bon investissement ! Rentabilisé en {retour_investissement:.1f} ans")
        else:
            st.warning(f"⚠️ Investissement long terme : {retour_investissement:.1f} ans")
        
        # Boutons de téléchargement
        st.markdown("---")
        col_dl1, col_dl2 = st.columns(2)
        
        with col_dl1:
            # Génération du devis texte
            devis_text = f"""
╔════════════════════════════════════════════════════════════════╗
║        DEVIS ESTIMATIF - INSTALLATION SOLAIRE SÉNÉGAL         ║
╚════════════════════════════════════════════════════════════════╝

📊 RÉSUMÉ DU SYSTÈME
{'─' * 64}
Consommation totale     : {st.session_state.consommation:.1f} kWh/jour
Autonomie souhaitée     : {(st.session_state.autonomie_pct if 'autonomie_pct' in st.session_state else 100)} %
Autonomie estimée       : {(st.session_state.autonomie_reelle_pct if 'autonomie_reelle_pct' in st.session_state else (st.session_state.autonomie_pct if 'autonomie_pct' in st.session_state else 100)):.0f} %
Couverte estimée        : {(st.session_state.production_solaire_kwh_j if 'production_solaire_kwh_j' in st.session_state else (st.session_state.consommation_couverte if 'consommation_couverte' in st.session_state else st.session_state.consommation)):.1f} kWh/jour
Puissance installée     : {devis['puissance_totale']:.2f} kWc
Type de batterie        : {st.session_state.choix['type_batterie']}
Voltage système         : {st.session_state.choix['voltage']}V
Type onduleur           : {st.session_state.choix['type_onduleur']}

📦 DÉTAILS DES ÉQUIPEMENTS
{'─' * 64}
"""
            for item in devis["details"]:
                devis_text += f"""
{item['item']}
  Quantité        : {item['quantite']}
  Prix unitaire   : {item['prix_unitaire']:,} FCFA
  Sous-total      : {item['sous_total']:,} FCFA
"""
            
            devis_text += f"""
{'═' * 64}
💰 TOTAL ESTIMATIF : {devis['total']:,} FCFA
{'═' * 64}

💳 OPTIONS DE PAIEMENT
{'─' * 64}
Comptant    : {devis['total']:,} FCFA
12 mois     : {mensualite_12:,.0f} FCFA/mois (+10%)
24 mois     : {mensualite_24:,.0f} FCFA/mois (+15%)

💡 ANALYSE FINANCIÈRE
{'─' * 64}
Économie annuelle estimée      : {economie_annuelle:,.0f} FCFA
Économie sur 10 ans            : {economie_10ans:,.0f} FCFA
Retour sur investissement      : {retour_investissement:.1f} ans

📝 NOTES IMPORTANTES
{'─' * 64}
- Prix indicatifs basés sur le marché sénégalais
- Installation standard incluse
- Garantie selon fabricant (panneaux: 25 ans, batteries: variable)
- Maintenance recommandée tous les 6 mois

{'═' * 64}
Document généré automatiquement
Pour plus d'informations : energiesolairesenegal.com
{'═' * 64}
"""
            
            # Génération du devis Word (RTF)
            def _to_rtf(text: str) -> str:
                safe = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
                safe = safe.replace("\n", "\\line\n")
                return "{\\rtf1\\ansi\n" + safe + "\n}"
            rtf_text = _to_rtf(devis_text)
            st.download_button(
                "📥 Télécharger le devis (Word)",
                rtf_text,
                file_name=f"devis_solaire_{st.session_state.choix['voltage']}V.rtf",
                mime="application/rtf",
                use_container_width=True
            )
        
        with col_dl2:
            # Génération Excel (HTML compatible .xls)
            rows_html = "".join([
                f"<tr><td>{item['item']}</td><td>{item['quantite']}</td><td>{item['prix_unitaire']}</td><td>{item['sous_total']}</td></tr>" for item in devis["details"]
            ])
            excel_html = f"""
            <html><head><meta charset='utf-8'></head><body>
            <table border='1'>
            <tr><th>Équipement</th><th>Quantité</th><th>Prix unitaire (FCFA)</th><th>Sous-total (FCFA)</th></tr>
            {rows_html}
            <tr><td><b>TOTAL</b></td><td></td><td></td><td><b>{devis['total']}</b></td></tr>
            </table>
            </body></html>
            """
            st.download_button(
                "📊 Télécharger (Excel)",
                excel_html,
                file_name=f"devis_solaire_{st.session_state.choix['voltage']}V.xls",
                mime="application/vnd.ms-excel",
                use_container_width=True
            )

with tab3:
    st.header("☀️ Conseiller solaire")
    
    api_ready = ('DEEPSEEK_API_KEY' in st.secrets) and bool(st.secrets.get('DEEPSEEK_API_KEY', ''))
    if not api_ready:
        st.warning("⚠️ Clé API DeepSeek manquante. Ajoutez-la au fichier '.streamlit/secrets.toml' sous 'DEEPSEEK_API_KEY'.")
        st.info("👉 La configuration se fait uniquement via le fichier de secrets.")
    else:
        # Contexte du dimensionnement
        contexte = ""
        if 'dimensionnement' in st.session_state:
            dim = st.session_state.dimensionnement
            choix = st.session_state.choix

            # Estimation de la couverture réelle à partir des équipements actifs
            equip_actifs_ctx = st.session_state.get('equip_choisi', st.session_state.get('equipements', None))
            prod_kwh_j_ctx = 0.0
            auto_reelle_ctx = (st.session_state.autonomie_reelle_pct if 'autonomie_reelle_pct' in st.session_state else None)
            if not auto_reelle_ctx and equip_actifs_ctx and equip_actifs_ctx.get('panneau'):
                pn_ctx, nb_ctx = equip_actifs_ctx['panneau']
                if pn_ctx and nb_ctx > 0:
                    p_unit_ctx = PRIX_EQUIPEMENTS['panneaux'][pn_ctx]['puissance']
                    p_tot_ctx = p_unit_ctx * nb_ctx
                    prod_kwh_j_ctx = (p_tot_ctx / 1000.0) * 5.0 * 0.75
                    conso_totale_ctx = st.session_state.consommation if 'consommation' in st.session_state else 10.0
                    auto_reelle_ctx = min(100.0, (prod_kwh_j_ctx / conso_totale_ctx) * 100.0)
            prod_kwh_j_ctx = prod_kwh_j_ctx if prod_kwh_j_ctx > 0 else (st.session_state.production_solaire_kwh_j if 'production_solaire_kwh_j' in st.session_state else 0.0)
            auto_reelle_ctx = auto_reelle_ctx if auto_reelle_ctx is not None else (st.session_state.autonomie_reelle_pct if 'autonomie_reelle_pct' in st.session_state else (st.session_state.autonomie_pct if 'autonomie_pct' in st.session_state else 100))

            contexte = f"""
L'utilisateur a dimensionné une installation avec:
- Consommation totale: {st.session_state.consommation:.1f} kWh/jour
- Couverture souhaitée: {(st.session_state.autonomie_pct if 'autonomie_pct' in st.session_state else 100)}% ({(st.session_state.consommation_couverte if 'consommation_couverte' in st.session_state else st.session_state.consommation):.1f} kWh/j)
- Couverture estimée: {auto_reelle_ctx:.0f}% ({prod_kwh_j_ctx:.1f} kWh/j)
- Puissance panneaux: {dim['puissance_panneaux']:.0f} Wc
- Capacité batteries: {dim['capacite_batterie']:.0f} Ah ({choix['type_batterie']})
- Puissance onduleur: {dim['puissance_onduleur']:.0f} W ({choix['type_onduleur']})
- Voltage système: {choix['voltage']}V
- Climat: Sénégal (chaleur, humidité, 5h ensoleillement moyen)
"""
        
        st.subheader("🎛️ Options d’équipements avec totaux")
        options_use_online = st.checkbox("Utiliser les prix en ligne (energiesolairesenegal.com)", value=True)
        options_accessoires_pct = st.slider("Taux accessoires (%)", 5, 20, 15, step=1, help="Inclut câbles, connecteurs, protections, structure, etc.", key="accessoires_pct_options")
        base_voltage = st.session_state.choix['voltage'] if 'choix' in st.session_state else 48

        options_spec = [
            {'nom':'Option Économique','type_batterie':'AGM','type_onduleur':'Off-Grid','type_regulateur':'PWM','voltage':12},
            {'nom':'Option Équilibrée','type_batterie':'GEL','type_onduleur':'Hybride','type_regulateur':None,'voltage':12},
            {'nom':'Option Premium','type_batterie':'Lithium','type_onduleur':'Online','type_regulateur':'MPPT','voltage':48},
        ]

        for opt in options_spec:
            # Consommation couverte (si disponible), sinon consommation totale
            consommation_opt = (st.session_state.consommation_couverte if 'consommation_couverte' in st.session_state else (st.session_state.consommation if 'consommation' in st.session_state else 10.0))
            # Dimensionnement pour l’option
            dim_opt = calculer_dimensionnement(
                consommation_opt,
                voltage=opt.get('voltage', base_voltage),
                type_batterie=opt['type_batterie']
            )
            choix_opt = {
                'type_batterie': opt['type_batterie'],
                'type_onduleur': opt['type_onduleur'],
                'voltage': opt.get('voltage', base_voltage)
            }
            if opt['type_onduleur'] != 'Hybride':
                choix_opt['type_regulateur'] = opt['type_regulateur']

            equip_opt = selectionner_equipements(dim_opt, choix_opt)
            devis_opt = calculer_devis(equip_opt, use_online=options_use_online, accessoires_rate=options_accessoires_pct/100.0)
            with st.expander(f"{opt['nom']} – Total: {devis_opt['total']:,} FCFA", expanded=False):
                st.markdown(f"• Batterie: {opt['type_batterie']}")
                st.markdown(f"• Onduleur: {opt['type_onduleur']}")
                if equip_opt['regulateur']:
                    st.markdown(f"• Régulateur: {equip_opt['regulateur']}")
                st.markdown(f"• Panneaux: {equip_opt['panneau'][1]} x {equip_opt['panneau'][0]}")
                
                # Autonomie estimée pour cette option
                try:
                    pn = equip_opt['panneau'][0]
                    nbp = equip_opt['panneau'][1]
                    punit = PRIX_EQUIPEMENTS['panneaux'].get(pn, {}).get('puissance', 0)
                    prod_opt_kwh_j = (punit * nbp / 1000.0) * 5.0 * 0.75 if (pn and nbp > 0 and punit > 0) else 0.0
                    conso_tot = st.session_state.consommation if 'consommation' in st.session_state else 10.0
                    auto_opt_pct = min(100.0, (prod_opt_kwh_j / conso_tot) * 100.0) if conso_tot > 0 else 0.0
                    st.markdown(f"• Autonomie estimée: {auto_opt_pct:.0f}% ({prod_opt_kwh_j:.1f} kWh/j)")
                except Exception:
                    pass
                
                st.markdown("—")
                for item in devis_opt['details']:
                    tag = "site" if item['source_prix']=='site' else ("local" if item['source_prix']=='local' else "estimé")
                    line = f"{item['item']}: {item['quantite']} × {item['prix_unitaire']:,} FCFA ({tag})"
                    if item.get('url_source'):
                        st.markdown(f"{line}  • [Lien]({item['url_source']})")
                    else:
                        st.markdown(line)

                if st.button(f"Appliquer {opt['nom']}", key=f"apply_{opt['nom']}"):
                    st.session_state.option_choisie = opt['nom']
                    st.session_state.equip_choisi = equip_opt
                    st.session_state.devis_choisi = devis_opt
                    st.session_state.use_online_options = options_use_online
                    st.success("Option appliquée. Allez à l’onglet Devis pour exporter.")

        st.markdown("---")

        st.subheader("💬 Questions fréquentes")
        
        col_q1, col_q2, col_q3 = st.columns(3)
        
        with col_q1:
            if st.button("🔧 Entretien des panneaux", use_container_width=True):
                question = "Comment entretenir mes panneaux solaires au Sénégal avec la poussière et le sable ?"
                with st.spinner("🤔 L'expert répond en streaming..."):
                    st.markdown("**Question:**")
                    st.info(question)
                    st.markdown("**Réponse de l'expert (streaming):**")
                    st.write_stream(appeler_assistant_ia_stream(question, contexte))
        
        with col_q2:
            if st.button("⚡ Durée de vie", use_container_width=True):
                question = "Quelle est la durée de vie de mon installation et quand faut-il remplacer les équipements ?"
                with st.spinner("🤔 L'expert répond en streaming..."):
                    st.markdown("**Question:**")
                    st.info(question)
                    st.markdown("**Réponse de l'expert (streaming):**")
                    st.write_stream(appeler_assistant_ia_stream(question, contexte))
        
        with col_q3:
            if st.button("🌧️ Saison des pluies", use_container_width=True):
                question = "Comment optimiser ma production pendant la saison des pluies au Sénégal ?"
                with st.spinner("🤔 L'expert répond en streaming..."):
                    st.markdown("**Question:**")
                    st.info(question)
                    st.markdown("**Réponse de l'expert (streaming):**")
                    st.write_stream(appeler_assistant_ia_stream(question, contexte))
        
        st.markdown("---")
        
        col_q4, col_q5, col_q6 = st.columns(3)
        
        with col_q4:
            if st.button("🔋 Batterie Lithium vs AGM", use_container_width=True):
                question = "Pour le climat du Sénégal, quelle est la meilleure batterie : Lithium ou AGM ? Explique les avantages et inconvénients."
                with st.spinner("🤔 L'expert répond en streaming..."):
                    st.markdown("**Question:**")
                    st.info(question)
                    st.markdown("**Réponse de l'expert (streaming):**")
                    st.write_stream(appeler_assistant_ia_stream(question, contexte))
        
        with col_q5:
            if st.button("🔌 Onduleur hybride", use_container_width=True):
                question = "Pourquoi choisir un onduleur hybride plutôt qu'un onduleur standard ?"
                with st.spinner("🤔 L'expert répond en streaming..."):
                    st.markdown("**Question:**")
                    st.info(question)
                    st.markdown("**Réponse de l'expert (streaming):**")
                    st.write_stream(appeler_assistant_ia_stream(question, contexte))
        
        with col_q6:
            if st.button("💰 Rentabilité", use_container_width=True):
                question = "Mon installation est-elle rentable ? Comment calculer le retour sur investissement ?"
                with st.spinner("🤔 L'expert répond en streaming..."):
                    st.markdown("**Question:**")
                    st.info(question)
                    st.markdown("**Réponse de l'expert (streaming):**")
                    st.write_stream(appeler_assistant_ia_stream(question, contexte))
        
        st.markdown("---")
        st.subheader("✍️ Posez votre question personnalisée")
        
        # Question personnalisée
        question_utilisateur = st.text_area(
            "Votre question sur l'énergie solaire :",
            placeholder="Ex: Comment protéger mon installation contre la foudre pendant l'hivernage ?",
            height=100
        )
        
        col_send, col_clear = st.columns([3, 1])
        
        with col_send:
            envoyer_btn = st.button("📤 Envoyer la question", type="primary", use_container_width=True)
        
        with col_clear:
            if st.button("🗑️ Effacer", use_container_width=True):
                st.rerun()
        
        if envoyer_btn:
            if question_utilisateur and len(question_utilisateur.strip()) > 5:
                with st.spinner("🤔 Le conseiller solaire répond en streaming..."):
                    st.markdown("---")
                    st.markdown("**Votre question:**")
                    st.info(question_utilisateur)
                    st.markdown("**Réponse détaillée de l'expert (streaming):**")
                    st.write_stream(appeler_assistant_ia_stream(question_utilisateur, contexte))
            else:
                st.warning("⚠️ Veuillez entrer une question (minimum 5 caractères)")

if False:  # Guide désactivé
    st.header("📖 Guide Complet - Énergie Solaire au Sénégal")
    
    guide_section = st.selectbox(
        "Choisissez une section du guide",
        [
            "🌍 Pourquoi le solaire au Sénégal ?",
            "🔋 Types de batteries expliqués",
            "⚡ Types d'onduleurs",
            "🎛️ Régulateurs PWM vs MPPT",
            "🔧 Installation et mise en service",
            "🛠️ Maintenance et entretien",
            "⚠️ Problèmes courants et solutions",
            "💵 Prix indicatifs des équipements",
            "💡 Conseils d'optimisation"
        ]
    )
    
    if guide_section == "🌍 Pourquoi le solaire au Sénégal ?":
        st.markdown("""
        ### Avantages de l'énergie solaire au Sénégal
        
        #### ☀️ Ensoleillement exceptionnel
        - **5 à 6 heures** d'ensoleillement optimal par jour
        - **300+ jours** de soleil par an
        - Position géographique idéale proche de l'équateur
        
        #### 💰 Économies substantielles
        - Facture Senelec réduite de **70 à 100%**
        - Prix du kWh Senelec : ~100 FCFA
        - Retour sur investissement : **3 à 7 ans**
        
        #### 🔌 Indépendance énergétique
        - Protection contre les délestages
        - Autonomie totale possible
        - Électricité stable et continue
        
        #### 🌱 Impact environnemental
        - Énergie propre et renouvelable
        - Réduction de l'empreinte carbone
        - Contribue au développement durable
        """)
    
    elif guide_section == "🔋 Types de batteries expliqués":
        st.markdown("""
        ### Comparaison détaillée des batteries
        """)
        
        for type_bat, info in INFO_BATTERIES.items():
            with st.expander(f"**{type_bat}** - Cliquez pour détails"):
                col_av, col_inc = st.columns(2)
                
                with col_av:
                    st.markdown("**✅ Avantages**")
                    st.markdown(info["avantages"])
                
                with col_inc:
                    st.markdown("**❌ Inconvénients**")
                    st.markdown(info["inconvenients"])
                
                st.info(f"💡 **Recommandé pour:** {info['usage']}")
                
                # Caractéristiques techniques
                st.markdown("**📊 Caractéristiques**")
                if type_bat == "Plomb":
                    st.markdown("""
                    - Cycles de vie: **500-800 cycles**
                    - Profondeur de décharge: **50%**
                    - Durée de vie: **2-3 ans**
                    - Entretien: **Mensuel (eau distillée)**
                    - Prix: **Le moins cher**
                    """)
                elif type_bat == "AGM":
                    st.markdown("""
                    - Cycles de vie: **800-1000 cycles**
                    - Profondeur de décharge: **70%**
                    - Durée de vie: **4-5 ans**
                    - Entretien: **Aucun**
                    - Prix: **Moyen** (+25% vs Plomb)
                    """)
                elif type_bat == "GEL":
                    st.markdown("""
                    - Cycles de vie: **1200-1500 cycles**
                    - Profondeur de décharge: **80%**
                    - Durée de vie: **5-7 ans**
                    - Entretien: **Aucun**
                    - Prix: **Élevé** (+50% vs Plomb)
                    """)
                else:  # Lithium
                    st.markdown("""
                    - Cycles de vie: **3000-5000 cycles**
                    - Profondeur de décharge: **90%**
                    - Durée de vie: **10-12 ans**
                    - Entretien: **Aucun**
                    - Prix: **Très élevé** (+300% vs Plomb)
                    - **MEILLEUR investissement long terme !**
                    """)
        
        st.markdown("---")
        st.markdown("### 🎯 Quelle batterie choisir ?")
        
        col_usage1, col_usage2 = st.columns(2)
        
        with col_usage1:
            st.info("""
            **Budget limité / Usage occasionnel**
            ➡️ **AGM** (meilleur rapport qualité/prix)
            
            **Usage domestique régulier**
            ➡️ **AGM ou GEL**
            """)
        
        with col_usage2:
            st.success("""
            **Installation professionnelle**
            ➡️ **GEL ou Lithium**
            
            **Investissement long terme**
            ➡️ **Lithium** (rentable sur 10 ans)
            """)
    
    elif guide_section == "⚡ Types d'onduleurs":
        st.markdown("""
        ### Types d'onduleurs
        
        - Off-Grid: convertit le DC des batteries en AC
        - Hybride: intègre régulateur MPPT, bascule réseau/batteries
        - Online: double conversion, protection maximale
        """)
    
    elif guide_section == "🎛️ Régulateurs PWM vs MPPT":
        st.markdown("""
        ### PWM vs MPPT : Comprendre la différence
        
        #### 🔵 Régulateur PWM (Pulse Width Modulation)
        
        **Comment ça marche ?**
        - Technologie simple : connecte directement les panneaux aux batteries
        - Comme un interrupteur qui s'allume/s'éteint rapidement
        
        **✅ Avantages:**
        - Prix accessible (15,000 - 45,000 FCFA)
        - Simple et fiable
        - Adapté aux petites installations
        
        **❌ Inconvénients:**
        - Perte de 20-30% d'énergie
        - Panneaux et batteries doivent avoir même voltage
        - Moins efficace par temps chaud
        
        **🎯 Recommandé pour:**
        - Petites installations (< 500W)
        - Budget très limité
        - Systèmes simples 12V
        
        ---
        
        #### 🟢 Régulateur MPPT (Maximum Power Point Tracking)
        
        **Comment ça marche ?**
        - Technologie intelligente : trouve le point optimal de production
        - Convertit l'excès de voltage en ampérage
        - S'adapte aux conditions en temps réel
        
        **✅ Avantages:**
        - **30% plus efficace** que PWM
        - Fonctionne mieux par temps chaud
        - Peut connecter panneaux haute tension
        - Production maximale même par temps nuageux
        - Charge plus rapide
        
        **❌ Inconvénients:**
        - Prix plus élevé (45,000 - 200,000 FCFA)
        - Configuration plus complexe
        
        **🎯 Recommandé pour:**
        - Toute installation > 500W
        - Climat chaud du Sénégal
        - Installations sérieuses
        - Rentable dès 1000W
        
        ---
        
        ### 📊 Comparaison directe
        """)
        
        col_comp1, col_comp2 = st.columns(2)
        
        with col_comp1:
            st.info("""
            **PWM**
            
            💰 Prix: 15,000 - 45,000 FCFA
            ⚡ Efficacité: 70-75%
            🌡️ Chaleur: Performance réduite
            📉 Perte: 20-30%
            🔧 Installation: Simple
            """)
        
        with col_comp2:
            st.success("""
            **MPPT ⭐**
            
            💰 Prix: 45,000 - 200,000 FCFA
            ⚡ Efficacité: 94-98%
            🌡️ Chaleur: Performance maintenue
            📈 Gain: +30%
            🔧 Installation: Moyenne
            """)
        
        st.warning("""
        ### 🎯 Conseil pour le Sénégal
        
        Le **MPPT est fortement recommandé** car :
        1. La chaleur réduit l'efficacité des panneaux → MPPT compense
        2. Gain de 30% = plus de panneaux économisés
        3. Rentabilisé en 2-3 ans sur la production
        4. Les onduleurs hybrides ont déjà du MPPT intégré !
        """)
        # Rappel dynamique des prix actuels PWM vs MPPT depuis la base
        pwm_prices = [spec['prix'] for spec in PRIX_EQUIPEMENTS['regulateurs'].values() if spec['type'] == 'PWM']
        mppt_prices = [spec['prix'] for spec in PRIX_EQUIPEMENTS['regulateurs'].values() if spec['type'] == 'MPPT']
        if pwm_prices and mppt_prices:
            st.info(f"Prix actuels (base locale): PWM {min(pwm_prices):,}–{max(pwm_prices):,} FCFA | MPPT {min(mppt_prices):,}–{max(mppt_prices):,} FCFA")
    
    elif guide_section == "🔧 Installation et mise en service":
        st.markdown("""
        ### Guide d'installation étape par étape
        
        #### 1️⃣ Préparation du site
        
        **Choix de l'emplacement panneaux:**
        - ☀️ Orientation plein SUD (hémisphère nord)
        - 📐 Inclinaison : 13-15° (latitude du Sénégal)
        - 🌳 Aucune ombre (arbres, bâtiments)
        - 🏠 Toiture solide ou structure au sol
        
        **Emplacement batteries et onduleur:**
        - 🏠 Local sec et ventilé
        - 🌡️ À l'abri de la chaleur directe
        - 🔒 Sécurisé (cadenas, grillage)
        - ⚡ Proche du tableau électrique
        
        ---
        
        #### 2️⃣ Installation des panneaux
        
        **Étapes:**
        1. Monter la structure (aluminium ou acier galvanisé)
        2. Fixer solidement au toit ou au sol
        3. Installer les panneaux avec pinces
        4. Câbler en série ou parallèle selon voltage
        5. Protéger les câbles (gaine UV)
        
        **⚠️ Sécurité:**
        - Travailler par temps sec
        - Harnais si en hauteur
        - Gants isolants
        - Ne jamais court-circuiter
        
        ---
        
        #### 3️⃣ Installation électrique
        
        **Ordre de connexion:**
        1. **D'abord** connecter les batteries à l'onduleur
        2. Vérifier la polarité (+ et -)
        3. Connecter le régulateur/onduleur
        4. **En dernier** connecter les panneaux
        
        **Protection obligatoire:**
        - ⚡ Disjoncteurs sur chaque ligne
        - 🔥 Fusibles batteries
        - ⛈️ Parafoudre (recommandé en saison des pluies)
        - 🌍 Mise à terre
        
        ---
        
        #### 4️⃣ Configuration et tests
        
        **Paramètres à configurer:**
        - Voltage batteries (12V/24V/48V)
        - Type de batterie (GEL/AGM/Lithium)
        - Seuils de charge/décharge
        - Priorité solaire ou réseau
        
        **Tests à effectuer:**
        - ✅ Vérifier tous les voltages
        - ✅ Test de charge solaire
        - ✅ Test de décharge batterie
        - ✅ Test de basculement Senelec (si hybride)
        - ✅ Test des protections
        
        ---
        
        #### 5️⃣ Mise en service
        
        **Check-list finale:**
        - [ ] Toutes les connexions serrées
        - [ ] Polarités vérifiées
        - [ ] Protections en place
        - [ ] Batteries chargées à 100%
        - [ ] Paramètres configurés
        - [ ] Manuel utilisateur remis
        - [ ] Formation utilisateur faite
        
        ---
        
        ### ⚠️ IMPORTANT - Normes et réglementations
        
        **Au Sénégal:**
        - Installation par professionnel certifié recommandée
        - Déclaration à la Senelec si connexion réseau
        - Respect des normes électriques
        - Assurance habitation à jour
        
        **💡 Conseil:** Faire appel à un installateur certifié pour :
        - Garantie de 2-5 ans
        - Installation aux normes
        - Service après-vente
        - Aide aux démarches administratives
        """)
    
    elif guide_section == "🛠️ Maintenance et entretien":
        st.markdown("""
        ### Guide de maintenance complet
        
        #### 🌞 Panneaux solaires
        
        **Nettoyage (IMPORTANT au Sénégal !)**
        
        La poussière et le sable réduisent la production de **20-40%** !
        
        **Fréquence:**
        - **Saison sèche:** Toutes les 2-3 semaines
        - **Saison des pluies:** Une fois par mois
        - Après tempête de sable: Immédiatement
        
        **Comment nettoyer:**
        1. ☀️ Le matin tôt ou le soir (panneaux froids)
        2. 💧 Eau + savon doux (pas de produits abrasifs)
        3. 🧽 Éponge douce ou raclette
        4. 💦 Rincer abondamment à l'eau claire
        5. ⚠️ Ne JAMAIS nettoyer à sec (rayures)
        
        **Inspection visuelle (mensuelle):**
        - Fissures ou cassures
        - Connexions desserrées
        - Câbles endommagés
        - Corrosion sur la structure
        
        ---
        
        #### 🔋 Batteries
        
        **Batteries PLOMB (entretien requis):**
        
        **Tous les mois:**
        - Vérifier niveau d'eau distillée
        - Ajouter si nécessaire (jamais d'eau du robinet !)
        - Nettoyer les bornes (bicarbonate + eau)
        - Vérifier voltage de chaque batterie
        
        **Tous les 3 mois:**
        - Égalisation des batteries (charge complète)
        - Resserrer les connexions
        - Vérifier densité électrolyte (densimètre)
        
        **Batteries AGM/GEL/Lithium (sans entretien):**
        
        **Tous les 3 mois:**
        - Vérifier voltage
        - Nettoyer les bornes
        - Vérifier température (ne doit pas dépasser 45°C)
        
        **⚠️ Signes de batterie fatiguée:**
        - Se décharge trop vite
        - Ne charge pas complètement
        - Gonflement ou fuite
        - Température excessive
        
        → **Remplacer immédiatement !**
        
        ---
        
        #### ⚡ Onduleur et régulateur
        
        **Tous les mois:**
        - Nettoyer ventilation (air comprimé)
        - Vérifier écran/voyants
        - Noter les statistiques
        - Écouter bruits anormaux
        
        **Tous les 6 mois:**
        - Vérifier toutes connexions
        - Nettoyer l'intérieur (poussière)
        - Mettre à jour firmware si disponible
        - Test complet du système
        
        ---
        
        #### 🔌 Installation électrique
        
        **Tous les 6 mois:**
        - Resserrer toutes connexions
        - Vérifier état des câbles
        - Tester les protections (disjoncteurs)
        - Vérifier mise à terre
        - Inspection parafoudre
        
        ---
        
        ### 📋 Calendrier de maintenance annuel
        """)
        
        st.info("""
        **JANVIER - FÉVRIER - MARS (Saison sèche)**
        - Nettoyage panneaux toutes les 2 semaines
        - Attention à la poussière saharienne
        
        **AVRIL - MAI - JUIN (Avant hivernage)**
        - Révision complète du système
        - Vérifier parafoudres
        - Resserrer structure panneaux
        
        **JUILLET - AOÛT - SEPTEMBRE (Hivernage)**
        - Surveillance accrue
        - Vérifier étanchéité
        - Nettoyage après grosses pluies
        
        **OCTOBRE - NOVEMBRE - DÉCEMBRE**
        - Bilan annuel
        - Remplacement pièces usées
        - Préparation saison sèche
        """)
        
        st.success("""
        ### 💡 Conseils pour prolonger la durée de vie
        
        **Batteries:**
        - Ne jamais décharger complètement
        - Éviter les températures > 40°C
        - Recharger immédiatement après usage
        
        **Panneaux:**
        - Nettoyage régulier = +30% production
        - Protection contre grêle (rare mais possible)
        
        **Onduleur:**
        - Ventilation suffisante
        - Ne pas surcharger
        - Éteindre si problème
        """)
    
    elif guide_section == "⚠️ Problèmes courants et solutions":
        st.markdown("""
        ### Diagnostic et résolution des problèmes
        
        #### 🔋 Batteries se déchargent trop vite
        
        **Causes possibles:**
        - 🔴 Batteries vieilles ou fatiguées
        - 🔴 Trop de consommation
        - 🔴 Panneaux sales ou défaillants
        - 🔴 Régulateur défectueux
        
        **Solutions:**
        1. Vérifier âge des batteries
        2. Mesurer voltage au repos (> 12.6V pour batterie 12V chargée)
        3. Nettoyer les panneaux
        4. Réduire consommation temporairement
        5. Vérifier connections
        
        ---
        
        #### ☀️ Production solaire faible
        
        **Causes possibles:**
        - 🔴 Panneaux sales (poussière/sable)
        - 🔴 Ombre sur panneaux
        - 🔴 Mauvaise orientation
        - 🔴 Câbles endommagés
        - 🔴 Régulateur mal configuré
        
        **Solutions:**
        1. **Nettoyer immédiatement** (gain de 30% instantané)
        2. Vérifier absence d'ombre (matin et après-midi)
        3. Vérifier voltage panneaux au soleil
        4. Inspecter câbles et connexions
        5. Reconfigurer régulateur
        
        ---
        
        #### ⚡ Onduleur fait du bruit ou s'arrête
        
        **Bips répétés:**
        - 🔴 Batteries faibles → Recharger ou réduire charge
        - 🔴 Surcharge → Éteindre appareils non essentiels
        - 🔴 Surchauffe → Améliorer ventilation
        
        **Arrêt complet:**
        - 🔴 Protection activée → Vérifier cause (surcharge, court-circuit)
        - 🔴 Batteries trop faibles → Recharger avec Senelec
        - 🔴 Défaut interne → Contacter technicien
        
        **Solutions:**
        1. Consulter manuel (codes d'erreur)
        2. Réduire charge immédiatement
        3. Laisser refroidir si surchauffe
        4. Redémarrer après résolution
        
        ---
        
        #### 🌡️ Surchauffe des équipements
        
        **Batteries chaudes (> 45°C):**
        - ⚠️ DANGER : Risque d'explosion
        - Améliorer ventilation
        - Réduire charge immédiate
        - Vérifier surcharge du régulateur
        
        **Onduleur chaud:**
        - Normal sous charge, mais doit rester < 60°C
        - Nettoyer ventilateur
        - Ajouter ventilation externe
        - Ne pas enfermer dans meuble
        
        ---
        
        #### 🔌 Appareils ne fonctionnent pas
        
        **Vérifications:**
        1. ✅ Onduleur allumé ?
        2. ✅ Batteries chargées ?
        3. ✅ Disjoncteur activé ?
        4. ✅ Appareil compatible ?
        5. ✅ Surcharge ?
        
        **Appareils sensibles:**
        - Certains appareils nécessitent onde pure sinus
        - Moteurs nécessitent 3x leur puissance au démarrage
        - Appareils électroniques peuvent ne pas fonctionner avec onde modifiée
        
        ---
        
        #### 💧 Problèmes après la pluie
        
        **Infiltration d'eau:**
        - Sécher immédiatement
        - Vérifier étanchéité boîtiers
        - Remplacer si corrosion
        
        **Baisse de production:**
        - Normal si temps nuageux
        - Nettoyer panneaux (pluie = boue)
        
        ---
        
        ### 🆘 Quand appeler un technicien ?
        
        **Appelez immédiatement si:**
        - ⚠️ Fumée ou odeur de brûlé
        - ⚠️ Étincelles ou arcs électriques
        - ⚠️ Batteries gonflées ou qui fuient
        - ⚠️ Choc électrique
        - ⚠️ Chute de panneau
        
        **Appelez rapidement si:**
        - Problème non résolu après vérifications basiques
        - Équipement endommagé
        - Performances très dégradées
        - Doute sur la sécurité
        
        ---
        
        ### 📞 Contacts utiles
        
        """)
        
        st.info("""
        **Fournisseurs au Sénégal:**
        - Solaire Sénégal: energiesolairesenegal.com
        - ANER (Agence Nationale pour les Énergies Renouvelables)
        
        **Urgences électriques:**
        - Senelec: 800 00 00 93
        
        **Ayez toujours:**
        - Numéro de votre installateur
        - Garanties et factures
        - Manuel d'utilisation
        """)
    
    elif guide_section == "💵 Prix indicatifs des équipements":
        st.markdown("### Prix indicatifs des équipements (base locale)")
        colp, colb = st.columns([1,1])
        with colp:
            st.subheader("Panneaux")
            data_p = []
            for nom, specs in PRIX_EQUIPEMENTS['panneaux'].items():
                p = specs.get('puissance', 0)
                price = specs.get('prix', 0)
                ppw = (price / p) if p else None
                data_p.append({"Référence": nom, "Puissance (W)": p, "Prix (FCFA)": price, "Prix/W": round(ppw, 2) if ppw else None})
            df_p = pd.DataFrame(data_p).sort_values(by=["Puissance (W)"], ascending=False)
            st.dataframe(df_p, use_container_width=True)
        with colb:
            st.subheader("Batteries")
            data_b = []
            for nom, specs in PRIX_EQUIPEMENTS['batteries'].items():
                data_b.append({"Référence": nom, "Type": specs.get('type'), "Capacité (Ah)": specs.get('capacite'), "Tension (V)": specs.get('voltage'), "Prix (FCFA)": specs.get('prix')})
            df_b = pd.DataFrame(data_b).sort_values(by=["Type","Capacité (Ah)"])
            st.dataframe(df_b, use_container_width=True)
        col1, col2 = st.columns([1,1])
        with col1:
            st.subheader("Onduleurs")
            data_o = []
            for nom, specs in PRIX_EQUIPEMENTS['onduleurs'].items():
                data_o.append({"Référence": nom, "Type": specs.get('type'), "Puissance (W)": specs.get('puissance'), "Tension (V)": specs.get('voltage'), "Prix (FCFA)": specs.get('prix')})
            df_o = pd.DataFrame(data_o).sort_values(by=["Type","Puissance (W)"])
            st.dataframe(df_o, use_container_width=True)
        with col2:
            st.subheader("Régulateurs")
            data_r = []
            for nom, specs in PRIX_EQUIPEMENTS['regulateurs'].items():
                data_r.append({"Référence": nom, "Type": specs.get('type'), "Intensité (A)": specs.get('amperage'), "Tension max (V)": specs.get('voltage_max'), "Prix (FCFA)": specs.get('prix')})
            df_r = pd.DataFrame(data_r).sort_values(by=["Type","Intensité (A)"])
            st.dataframe(df_r, use_container_width=True)
        st.markdown("---")
        st.subheader("Installation et accessoires")
        accessoires_pct_def = 15
        st.markdown(f"Accessoires: environ {accessoires_pct_def}% du matériel (câbles, protections, structure)")
        inst_table = pd.DataFrame([{"Catégorie": k, "Forfait (FCFA)": v} for k, v in PRIX_INSTALLATION.items()])
        st.dataframe(inst_table, use_container_width=True)
        def _min_max(items, key="prix"):
            vals = [v.get(key, 0) for v in items.values() if v.get(key, 0)]
            return (min(vals) if vals else None, max(vals) if vals else None)
        pmin, pmax = _min_max(PRIX_EQUIPEMENTS['panneaux'])
        bmin, bmax = _min_max(PRIX_EQUIPEMENTS['batteries'])
        omin, omax = _min_max(PRIX_EQUIPEMENTS['onduleurs'])
        rpm, rpx = _min_max(PRIX_EQUIPEMENTS['regulateurs'])
        st.info(f"Repères de prix: Panneaux {pmin:,}–{pmax:,} FCFA | Batteries {bmin:,}–{bmax:,} FCFA | Onduleurs {omin:,}–{omax:,} FCFA | Régulateurs {rpm:,}–{rpx:,} FCFA")
    
    elif guide_section == "💡 Conseils d'optimisation":
        st.markdown("""
        ### Maximisez votre production et économies
        
        #### 🌞 Optimiser la production solaire
        
        **1. Orientation et inclinaison parfaites**
        - Orientation: Plein SUD (hémisphère nord)
        - Inclinaison: 13-15° pour le Sénégal
        - Révision 2x/an: mars et septembre
        
        **2. Éliminer les ombres**
        - Même une petite ombre réduit production de 30%
        - Élaguer arbres régulièrement
        - Attention aux nouvelles constructions
        
        **3. Nettoyage optimal**
        - **Saison sèche:** Tous les 15 jours minimum
        - Tôt le matin (6h-8h) ou soir (18h-19h)
        - Gain immédiat: +20 à 40%
        
        **4. Câblage adapté**
        - Câbles courts = moins de perte
        - Section suffisante (4mm² minimum)
        - Connexions propres et serrées
        
        ---
        
        #### 💰 Réduire la consommation
        
        **Appareils économes recommandés:**
        
        **Éclairage:**
        - ✅ LED 10W au lieu de ampoule 60W
        - Économie: 50W x 6h = 300Wh/jour
        - = 109 kWh/an économisés
        
        **Réfrigération:**
        - ✅ Frigo classe A+++ (100W) au lieu de classe B (200W)
        - Économie: 100W x 12h = 1,2 kWh/jour
        - = 438 kWh/an économisés
        
        **Ventilation:**
        - ✅ Ventilateur DC 12V (25W) au lieu de AC (75W)
        - Économie: 50W x 10h = 500Wh/jour
        - = 182 kWh/an économisés
        
        **Habitudes intelligentes:**
        - ❌ Éteindre veilles (TV, chargeurs)
        - ❌ Débrancher ce qui ne sert pas
        - ✅ Utiliser appareils aux heures ensoleillées
        - ✅ Charger téléphones en journée
        
        ---
        
        #### 🔋 Prolonger vie des batteries
        
        **Règle d'or: Ne jamais décharger complètement**
        
        **Profondeurs de décharge recommandées:**
        - Plomb: 50% maximum
        - AGM/GEL: 70% maximum
        - Lithium: 80-90% maximum
        
        **Conseils pratiques:**
        1. Configurer arrêt automatique onduleur à 50-60%
        2. Éviter décharges profondes répétées
        3. Recharger immédiatement après usage intensif
        4. Maintenir température < 40°C
        5. Égaliser batteries plomb tous les 3 mois
        
        **Impact température:**
        - 25°C = durée de vie normale
        - 35°C = -20% durée de vie
        - 45°C = -50% durée de vie
        → **Ventiler le local batteries !**
        
        ---
        
        #### ⚡ Gérer les pics de consommation
        
        **Appareils à forte consommation:**
        - Fer à repasser: 1000-2000W
        - Bouilloire: 2000W
        - Four micro-ondes: 800-1200W
        - Machine à laver: 2000W
        
        **Stratégies:**
        1. **Utiliser en journée** (soleil + batterie)
        2. **Un à la fois** (pas de cumul)
        3. **Version économe** (bouilloire gaz, fer léger)
        4. **Planifier** les lessives
        
        ---
        
        #### 🌐 Monitoring et suivi
        
        **Surveiller ces indicateurs:**
        - Production solaire journalière (kWh)
        - État de charge batteries (%)
        - Consommation journalière (kWh)
        - Température équipements
        
        **Applications disponibles:**
        - Certains onduleurs ont WiFi/Bluetooth
        - Monitoring en temps réel
        - Alertes sur smartphone
        - Historiques et statistiques
        
        ---
        
        #### 💡 Astuces spéciales Sénégal
        
        **Saison sèche (Nov-Mai):**
        - Production maximale
        - Nettoyages fréquents (poussière)
        - Profiter pour gros appareils
        
        **Hivernage (Juin-Oct):**
        - Production réduite (nuages)
        - Économiser batterie
        - Utiliser Senelec si hybride
        - Vérifier parafoudres
        
        **Harmattan (déc-fév):**
        - Poussière saharienne intense
        - Nettoyage tous les 10 jours !
        - Perte jusqu'à 40% si sale
        
        ---
        
        ### 🎯 Plan d'action: Première année
        """)
        
        st.success("""
        **Mois 1-3: Rodage**
        - Observer et noter consommation
        - Ajuster habitudes
        - Apprendre système
        
        **Mois 3-6: Optimisation**
        - Identifier gaspillages
        - Remplacer appareils énergivores
        - Automatiser charge batteries
        
        **Mois 6-12: Maîtrise**
        - Routine établie
        - Maintenance préventive
        - Économies maximales
        
        **Objectif:**
        - Facture Senelec: -70 à 100%
        - Autonomie: 90-100%
        - ROI: 5-7 ans
        """)
        
        st.info("""
        ### 📊 Checklist mensuelle d'optimisation
        
        - [ ] Panneaux propres
        - [ ] Batteries niveau OK
        - [ ] Connexions serrées
        - [ ] Ventilation efficace
        - [ ] Pas d'ombres nouvelles
        - [ ] Consommation stable
        - [ ] Production optimale
        - [ ] Équipements < 45°C
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p><b>☀️ Application de Dimensionnement Solaire - Sénégal</b></p>
    <p>🌍Développé pour les Sonateliens souhaitant s'équiper de solaire.par M.T.</p>
    <p>📞 Pour acheter vos équipements : <a href='https://energiesolairesenegal.com' target='_blank'>energiesolairesenegal.com</a></p>
    <p style='font-size: 0.9em; margin-top: 10px;'>
        💡 <b>Conseil :</b> Consultez toujours un professionnel certifié pour l'installation<br>
        ⚡ Prix indicatifs - Demandez un devis personnalisé pour votre projet
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
""")