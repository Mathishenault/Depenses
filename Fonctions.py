###FONCTIONS
import streamlit as st
import pandas as pd
import pdfplumber
import re
from io import BytesIO

def extraire_transactions_credit(pdf_file):
    transactions = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            for line in text.split('\n'):
                # Regex corrigée pour capturer le vrai montant
                match = re.match(
                    r"(\d{2})\s(\d{2})\s+"  # Date transaction (JJ MM)
                    r"(\d{2})\s(\d{2})\s+"  # Date inscription (JJ MM)
                    r"(.+?)\s+"  # Description
                    r"\d{1,2},\d{2}\s?%\s+"  # Skip taux remise
                    r"(\d+,\d{2})$",  # Montant réel (en fin de ligne)
                    line.strip()
                )
                
                if match:
                    transactions.append({
                        "Date": f"2025-{match.group(2)}-{match.group(1)}",
                        "Description": match.group(5).strip(),
                        "Montant": float(match.group(6).replace(',', '.')),
                        "Catégorie": classifier_depense(match.group(5))
                    })
    return pd.DataFrame(transactions)



def formater_date(date_str):
    dicDate = {
    "JAN": 1, "FEV": 2, "MAR": 3, "AVR": 4, "MAI": 5, "JUN": 6,
    "JUL": 7, "AOU": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
    }
    """Convertit '1 JAN' en '2025-01-01'"""
    jour, mois_abr = date_str.split()
    mois_num = dicDate[mois_abr]
    return f"2025-{int(mois_num):02d}-{int(jour):02d}"


def extraire_transactions_compte(pdf_file):
    transactions = []
    
    # Liste des codes correspondant à des retraits
    # Cette liste sera à compléter avec les codes Desjardins pertinents
    codes_retrait = [
        "RA",    # Retrait au comptoir/facture
        "VMW",   # Virement Interac
        "IRGA",  # Retrait au guichet automatique
        "PWW",   # Paiement facture AccèsD Internet
        "VIW"    # Virement Internet
    ]
    
    # Liste des codes à ignorer (dépôts ou transactions sans impact financier)
    codes_ignore = [
        "INT",   # Intérêt
        "IET",   # Intérêt sur compte
        "BNI",   # Boni
        "DSL"    # Dépôt ou salaire
        # À compléter avec d'autres codes de dépôt
    ]
    
    # Liste vide pour l'instant - à compléter avec les codes fournis
    # [Insérer ici les codes Desjardins complets quand ils seront disponibles]
    
    with pdfplumber.open(pdf_file) as pdf:
        lignes = []
        for page in pdf.pages:
            text = page.extract_text()
            lignes.extend(text.split('\n'))
        
        i = 0
        while i < len(lignes):
            ligne = lignes[i]
            
            # Recherche d'une ligne qui commence par une date
            date_match = re.search(r"^\s*(\d{1,2}\s+\w{3})", ligne)
            if date_match:
                date = date_match.group(1).strip()
                
                # Extraire le code après la date
                code_match = re.search(r"^\s*\d{1,2}\s+\w{3}\s+(\w+)", ligne)
                code = code_match.group(1) if code_match else ""
                
                # Si c'est un code de retrait, traiter cette transaction
                if code in codes_retrait:
                    # Extraire la description
                    desc_start = ligne.find(code) + len(code) if code else 0
                    
                    # Extraire tous les montants de la ligne
                    montants = re.findall(r"(\d+[,\.]\d{2})", ligne)
                    
                    # Vérifier si la ligne actuelle contient des montants
                    if montants:
                        # La ligne contient des montants, donc on peut extraire directement
                        description = ligne[desc_start:ligne.find(montants[0], desc_start)].strip()
                        montant = float(montants[0].replace(',', '.'))
                        
                        # Si c'est un retrait, on doit prendre l'avant-dernier montant (habituellement)
                        if len(montants) >= 2:
                            montant = float(montants[-2].replace(',', '.'))
                    else:
                        # La ligne ne contient pas de montants, il faut regarder la ligne suivante
                        if i + 1 < len(lignes):
                            description = ligne[desc_start:].strip()
                            
                            # Chercher les montants dans la ligne suivante
                            next_line = lignes[i + 1]
                            next_montants = re.findall(r"(\d+[,\.]\d{2})", next_line)
                            
                            if next_montants:
                                montant = float(next_montants[0].replace(',', '.'))
                                i += 1  # Avancer d'une ligne supplémentaire
                            else:
                                # Pas de montant trouvé, passer à la ligne suivante
                                i += 1
                                continue
                        else:
                            # Dernière ligne, impossible de trouver un montant
                            i += 1
                            continue
                    
                    # Vérifier que le montant est significatif (éviter les frais minimes)
                    if montant > 1.0:
                        transactions.append({
                            "Date": formater_date(date),
                            "Description": description,
                            "Montant": montant,
                            "Catégorie": classifier_depense(description)
                        })
            
            i += 1
    
    return pd.DataFrame(transactions)


def exporter_excel(df):
    """Version basique mais fonctionnelle"""
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    return output.getvalue()


def formater_dataframe(df):
    """Version corrigée qui conserve les catégories"""
    df_formate = pd.DataFrame({
        'Date (A/M/J)': df['Date'].str.replace('/', '-'),
        'Qté': 1,
        'Description': df['Description'],
        'Prix unitaire': 0,
        'Avant taxes': '',
        'Après taxes': df['Montant'],
        'Notes': df.get('Notes', ''),
        'Catégorie': df['Catégorie']
    })
    
    colonnes = [
        'Date (A/M/J)', 'Qté', 'Description', 'Prix unitaire',
        'Avant taxes', 'Après taxes', 'Notes', 'Catégorie'
    ]
    return df_formate[colonnes]

def classifier_depense(description):
    # Dictionnaire de règles de classification
    categories = {
        'Frais scolaire' : ["UNIVERSITE"],
        'Automobile & transports en commun' : ["RTC", "AMIGO EXPRESS", "STM"],
        'Linge, manteaux, souliers et bottes' : ["URBAN PLANET"],
        'Sport' : ["FRADETTE", "SPORTS EXPERTS", "ESCALADE", "POPEYE"],
        'Hygiène' : ["COINAMATIC", "FAMILIPRIX", "PHARMAPRIX"],
        'Soins de santé' : ["DENTISTE", "DENTAIRE", "OPTOMÉTRISTE"],
        'Épicerie' : ["MAXI", "METRO", "MARCHE INNOVATION"],
        'Restaurant' : ["RESTO", "BAR", "SUBWAY"],
        'Logement, meubles, articles ménagers' : ["LOYER", "LA PERSONNELLE"],
        'Divers' : ["VIREMENT"],
        'Électronique' : ["BEST BUY", "STEAM PURCHASE", "NINTENDO"],
        'Cellulaire' : ["FIZZ"],
        'Billets' : ["AESGUL", "ASETIN"]
    }
    
    desc_upper = description.upper()
    for categ, keywords in categories.items():
        if any(keyword in desc_upper for keyword in keywords):
            return categ
    return "Divers"

def afficher_interface_fractionnement(df):
    depenses_etendues = []
    categories = [
        "Frais scolaire", 
        "Automobile & transports en commun",
        "Linge, manteaux, souliers et bottes",
        "Sport",
        "Hygiène",
        "Soins de santé (physio, dentiste, optométriste, etc.)",
        "Épicerie",
        "Restaurant",
        "Logement, meubles, articles ménagers",
        "Divers",
        "Électronique",
        "Cellulaire",
        "Billets"
    ]
    
    for idx, row in df.iterrows():
        with st.expander(f"{row['Description']} - {row['Montant']} $ (Catégorie: {row['Catégorie']})"):
            n_parts = st.slider(
                "Nombre de sous-dépenses",
                min_value=1,
                max_value=10,
                value=1,
                key=f"nparts_{idx}"
            )
            
            sous_depenses = []
            montant_restant = row['Montant']
            
            for i in range(n_parts):
                cols = st.columns([1, 2, 3])
                
                with cols[0]:
                    valeur_proposee = round(montant_restant / (n_parts - i), 2)
                    valeur_max = round(montant_restant, 2)
                    valeur_proposee = min(valeur_proposee, valeur_max)  # sécurité

                    montant = st.number_input(
                        f"Montant {i+1}",
                        min_value=0.0,
                        max_value=valeur_max,
                        value=valeur_proposee,
                        step=0.01,
                        key=f"montant_{idx}_{i}"
                    )
                
                with cols[1]:
                    # Catégorie par défaut = catégorie parente
                    default_cat = categories.index(row['Catégorie']) if row['Catégorie'] in categories else -1
                    categorie = st.selectbox(
                        "Catégorie",
                        options=categories,
                        index=default_cat if default_cat != -1 else len(categories)-1,  # Divers par défaut
                        key=f"cat_{idx}_{i}"
                    )
                
                with cols[2]:
                    sous_desc = st.text_input(
                        "Description détaillée",
                        value=f"{row['Description']}",
                        key=f"desc_{idx}_{i}"
                    )
                
                montant_restant -= montant
                sous_depenses.append({
                    "Date": row['Date'],
                    "Description": sous_desc,
                    "Montant": montant,
                    "Catégorie": categorie,
                    "Notes": ""
                })
            
            if abs(montant_restant) > 0.01:
                st.error(f"Reste non alloué: {montant_restant:.2f} $")
            else:
                depenses_etendues.extend(sous_depenses)
    
    return pd.DataFrame(depenses_etendues)
