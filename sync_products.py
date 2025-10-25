"""
Module de synchronisation des produits entre l'outil de dimensionnement et la gestion de stock
"""

import streamlit as st
from firebase_config import (
    save_product_to_firebase, 
    get_all_products_from_firebase,
    update_product_in_firebase
)

def extract_products_from_dimensioning():
    """
    Extrait tous les produits de PRIX_EQUIPEMENTS pour les convertir en format stock
    """
    # Import local pour éviter les dépendances circulaires
    from sun import PRIX_EQUIPEMENTS
    
    products = []
    
    # Traitement des panneaux solaires
    for nom, details in PRIX_EQUIPEMENTS.get("panneaux", {}).items():
        product = {
            "nom": nom,
            "categorie": "Panneaux Solaires",
            "prix_achat": details["prix"] * 0.7,  # Prix d'achat estimé à 70% du prix de vente
            "prix_vente": details["prix"],
            "stock_initial": 0,
            "stock_actuel": 0,
            "stock_minimum": 5,
            "unite": "pièce",
            "specifications": {
                "puissance": details.get("puissance", 0),
                "type": details.get("type", ""),
                "voltage": "12V/24V"
            },
            "source": "dimensionnement"
        }
        products.append(product)
    
    # Traitement des batteries
    for nom, details in PRIX_EQUIPEMENTS.get("batteries", {}).items():
        product = {
            "nom": nom,
            "categorie": "Batteries",
            "prix_achat": details["prix"] * 0.7,
            "prix_vente": details["prix"],
            "stock_initial": 0,
            "stock_actuel": 0,
            "stock_minimum": 3,
            "unite": "pièce",
            "specifications": {
                "capacite": details.get("capacite", 0),
                "voltage": details.get("voltage", 12),
                "type": details.get("type", ""),
                "cycles": details.get("cycles", 0),
                "decharge_max": details.get("decharge_max", 0),
                "kwh": details.get("kwh", 0)
            },
            "source": "dimensionnement"
        }
        products.append(product)
    
    # Traitement des onduleurs
    for nom, details in PRIX_EQUIPEMENTS.get("onduleurs", {}).items():
        product = {
            "nom": nom,
            "categorie": "Onduleurs",
            "prix_achat": details["prix"] * 0.7,
            "prix_vente": details["prix"],
            "stock_initial": 0,
            "stock_actuel": 0,
            "stock_minimum": 2,
            "unite": "pièce",
            "specifications": {
                "puissance": details.get("puissance", 0),
                "voltage": details.get("voltage", 12),
                "type": details.get("type", ""),
                "phase": details.get("phase", "monophase"),
                "mppt": details.get("mppt", "")
            },
            "source": "dimensionnement"
        }
        products.append(product)
    
    # Traitement des régulateurs
    for nom, details in PRIX_EQUIPEMENTS.get("regulateurs", {}).items():
        product = {
            "nom": nom,
            "categorie": "Régulateurs",
            "prix_achat": details["prix"] * 0.7,
            "prix_vente": details["prix"],
            "stock_initial": 0,
            "stock_actuel": 0,
            "stock_minimum": 3,
            "unite": "pièce",
            "specifications": {
                "amperage": details.get("amperage", 0),
                "type": details.get("type", ""),
                "voltage_max": details.get("voltage_max", 0)
            },
            "source": "dimensionnement"
        }
        products.append(product)
    
    return products

def sync_dimensioning_to_stock():
    """
    Synchronise les produits du dimensionnement vers le stock
    """
    try:
        # Récupérer les produits existants dans le stock
        existing_products = get_all_products_from_firebase()
        if not existing_products or not isinstance(existing_products, dict):
            existing_products = {}
        
        # Construire l'ensemble des noms existants à partir des valeurs du dict
        existing_names = {p.get("nom", "") for p in existing_products.values() if isinstance(p, dict)}
        
        # Extraire les produits du dimensionnement
        dimensioning_products = extract_products_from_dimensioning()
        
        new_products = 0
        updated_products = 0
        
        for product in dimensioning_products:
            if product["nom"] in existing_names:
                # Produit existe déjà, on peut mettre à jour les prix si nécessaire
                existing_item = next(((pid, pdata) for pid, pdata in existing_products.items() 
                                       if isinstance(pdata, dict) and pdata.get("nom") == product["nom"]), None)
                if existing_item:
                    prod_id, existing_product = existing_item
                    # Mettre à jour seulement les prix si ils ont changé
                    if (existing_product.get("prix_vente") != product["prix_vente"] or 
                        existing_product.get("prix_achat") != product["prix_achat"]):
                        
                        existing_product["prix_vente"] = product["prix_vente"]
                        existing_product["prix_achat"] = product["prix_achat"]
                        existing_product["specifications"] = product["specifications"]
                        
                        if update_product_in_firebase(prod_id, existing_product):
                            updated_products += 1
            else:
                # Nouveau produit, l'ajouter
                if save_product_to_firebase(product):
                    new_products += 1
        
        return {
            "success": True,
            "new_products": new_products,
            "updated_products": updated_products,
            "total_products": len(dimensioning_products)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def get_stock_for_dimensioning_product(product_name):
    """
    Récupère le stock actuel d'un produit pour l'affichage dans le dimensionnement
    """
    try:
        products = get_all_products_from_firebase()
        if not products or not isinstance(products, dict):
            return None
            
        # Itérer sur les valeurs du dictionnaire en évitant toute opération sur des types non-dict
        product = None
        for p in products.values():
            if isinstance(p, dict):
                nom = p.get("nom", None)
                if nom == product_name:
                    product = p
                    break
        
        if isinstance(product, dict):
            stock_actuel = product.get("stock_actuel")
            if stock_actuel is None:
                stock_actuel = product.get("quantite", product.get("stock_initial", 0))
            stock_min = product.get("stock_minimum", product.get("stock_min", 0))
            return {
                "stock_actuel": stock_actuel if isinstance(stock_actuel, (int, float)) else 0,
                "stock_minimum": stock_min if isinstance(stock_min, (int, float)) else 0,
                "disponible": (stock_actuel or 0) > 0
            }
        return None
        
    except Exception as e:
        st.error(f"Erreur lors de la récupération du stock: {e}")
        return None

def update_stock_after_quote(products_used):
    """
    Met à jour le stock après la création d'un devis
    
    Args:
        products_used: Liste des produits utilisés avec leurs quantités
                      Format: [{"nom": "produit", "quantite": 2}, ...]
    """
    try:
        existing_products = get_all_products_from_firebase()
        if not existing_products or not isinstance(existing_products, dict):
            existing_products = {}
        
        for used_product in products_used:
            product_name = used_product["nom"]
            quantity_used = used_product["quantite"]
            
            # Trouver le produit dans le stock de manière sûre
            existing_item = None
            for pid, pdata in existing_products.items():
                if isinstance(pdata, dict):
                    nom = pdata.get("nom", None)
                    if nom == product_name:
                        existing_item = (pid, pdata)
                        break
            
            if existing_item:
                prod_id, stock_product = existing_item
                if isinstance(stock_product, dict) and stock_product.get("stock_actuel", 0) >= quantity_used:
                    # Décrémenter le stock
                    new_stock = stock_product.get("stock_actuel", 0) - quantity_used
                    stock_product["stock_actuel"] = new_stock
                    
                    # Mettre à jour dans Firebase
                    update_product_in_firebase(prod_id, stock_product)
                    
                    # Enregistrer le mouvement de stock
                    from firebase_config import save_stock_movement_to_firebase
                    movement = {
                        "produit_id": prod_id,
                        "produit_nom": product_name,
                        "type": "sortie",
                        "quantite": quantity_used,
                        "motif": "Utilisation dans devis",
                        "date": st.session_state.get("current_date", ""),
                        "utilisateur": st.session_state.get("user_email", "système")
                    }
                    save_stock_movement_to_firebase(movement)
        
        return True
        
    except Exception as e:
        st.error(f"Erreur lors de la mise à jour du stock: {e}")
        return False

def check_stock_availability(products_needed):
    """
    Vérifie la disponibilité en stock des produits nécessaires
    
    Args:
        products_needed: Liste des produits nécessaires avec leurs quantités
                        Format: [{"nom": "produit", "quantite": 2}, ...]
    
    Returns:
        dict: Résultat de la vérification avec les produits manquants
    """
    try:
        existing_products = get_all_products_from_firebase()
        if not existing_products or not isinstance(existing_products, dict):
            existing_products = {}
            
        missing_products = []
        low_stock_products = []
        
        for needed_product in products_needed:
            product_name = needed_product["nom"]
            quantity_needed = needed_product["quantite"]
            
            # Itérer sur les valeurs du dictionnaire en évitant .get sur des types non-dict
            stock_product = None
            for p in existing_products.values():
                if isinstance(p, dict):
                    nom = p.get("nom", None)
                    if nom == product_name:
                        stock_product = p
                        break
            
            if not isinstance(stock_product, dict):
                missing_products.append({
                    "nom": product_name,
                    "quantite_demandee": quantity_needed,
                    "stock_actuel": 0
                })
            elif stock_product.get("stock_actuel", 0) < quantity_needed:
                missing_products.append({
                    "nom": product_name,
                    "quantite_demandee": quantity_needed,
                    "stock_actuel": stock_product.get("stock_actuel", 0)
                })
            elif stock_product.get("stock_actuel", 0) <= stock_product.get("stock_minimum", 0):
                low_stock_products.append({
                    "nom": product_name,
                    "stock_actuel": stock_product.get("stock_actuel", 0),
                    "stock_minimum": stock_product.get("stock_minimum", 0)
                })
        
        return {
            "available": len(missing_products) == 0,
            "missing_products": missing_products,
            "low_stock_products": low_stock_products
        }
        
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
            "missing_products": [],
            "low_stock_products": []
        }
