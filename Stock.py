import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Configuration de la page gérée dans sun.py

# Initialisation de la base de données
def init_db():
    conn = sqlite3.connect('energie_solaire.db')
    c = conn.cursor()
    
    # Table Produits
    c.execute('''CREATE TABLE IF NOT EXISTS produits
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nom TEXT NOT NULL,
                  categorie TEXT,
                  prix_achat REAL,
                  prix_vente REAL,
                  stock_actuel INTEGER,
                  stock_min INTEGER,
                  unite TEXT)''')
    
    # Table Clients
    c.execute('''CREATE TABLE IF NOT EXISTS clients
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nom TEXT NOT NULL,
                  telephone TEXT,
                  adresse TEXT,
                  email TEXT)''')
    
    # Table Factures
    c.execute('''CREATE TABLE IF NOT EXISTS factures
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  numero TEXT UNIQUE,
                  date TEXT,
                  client_id INTEGER,
                  client_nom TEXT,
                  montant_total REAL,
                  type TEXT,
                  statut TEXT)''')
    
    # Table Lignes de facture
    c.execute('''CREATE TABLE IF NOT EXISTS lignes_facture
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  facture_id INTEGER,
                  produit_nom TEXT,
                  quantite INTEGER,
                  prix_unitaire REAL,
                  montant REAL)''')
    
    # Table Mouvements de stock
    c.execute('''CREATE TABLE IF NOT EXISTS mouvements_stock
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT,
                  produit_id INTEGER,
                  produit_nom TEXT,
                  type TEXT,
                  quantite INTEGER,
                  reference TEXT)''')
    
    conn.commit()
    conn.close()

# Fonctions pour les produits
def ajouter_produit(nom, categorie, prix_achat, prix_vente, stock, stock_min, unite):
    conn = sqlite3.connect('energie_solaire.db')
    c = conn.cursor()
    c.execute('''INSERT INTO produits (nom, categorie, prix_achat, prix_vente, stock_actuel, stock_min, unite)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (nom, categorie, prix_achat, prix_vente, stock, stock_min, unite))
    conn.commit()
    conn.close()

def obtenir_produits():
    conn = sqlite3.connect('energie_solaire.db')
    df = pd.read_sql_query("SELECT * FROM produits ORDER BY nom", conn)
    conn.close()
    return df

def modifier_produit(produit_id, nom, categorie, prix_achat, prix_vente, stock_actuel, stock_min, unite):
    conn = sqlite3.connect('energie_solaire.db')
    c = conn.cursor()
    c.execute('''UPDATE produits SET nom=?, categorie=?, prix_achat=?, prix_vente=?, 
                 stock_actuel=?, stock_min=?, unite=? WHERE id=?''',
              (nom, categorie, prix_achat, prix_vente, stock_actuel, stock_min, unite, produit_id))
    conn.commit()
    conn.close()

def obtenir_produit_par_id(produit_id):
    conn = sqlite3.connect('energie_solaire.db')
    c = conn.cursor()
    c.execute("SELECT * FROM produits WHERE id=?", (produit_id,))
    produit = c.fetchone()
    conn.close()
    return produit

def modifier_stock(produit_id, quantite, type_mouvement, reference=""):
    conn = sqlite3.connect('energie_solaire.db')
    c = conn.cursor()
    
    # Récupérer le produit
    c.execute("SELECT nom, stock_actuel FROM produits WHERE id=?", (produit_id,))
    produit = c.fetchone()
    
    if produit:
        nouveau_stock = produit[1] + quantite if type_mouvement == "Entrée" else produit[1] - quantite
        
        # Mettre à jour le stock
        c.execute("UPDATE produits SET stock_actuel=? WHERE id=?", (nouveau_stock, produit_id))
        
        # Enregistrer le mouvement
        c.execute('''INSERT INTO mouvements_stock (date, produit_id, produit_nom, type, quantite, reference)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (datetime.now().strftime("%Y-%m-%d %H:%M"), produit_id, produit[0], 
                   type_mouvement, quantite, reference))
        
        conn.commit()
    conn.close()

# Fonctions pour les clients
def ajouter_client(nom, telephone, adresse, email):
    conn = sqlite3.connect('energie_solaire.db')
    c = conn.cursor()
    c.execute('''INSERT INTO clients (nom, telephone, adresse, email)
                 VALUES (?, ?, ?, ?)''', (nom, telephone, adresse, email))
    conn.commit()
    conn.close()

def obtenir_clients():
    conn = sqlite3.connect('energie_solaire.db')
    df = pd.read_sql_query("SELECT * FROM clients ORDER BY nom", conn)
    conn.close()
    return df

# Fonctions pour les factures
def creer_facture(client_id, client_nom, lignes, type_doc="Facture"):
    conn = sqlite3.connect('energie_solaire.db')
    c = conn.cursor()
    
    # Générer numéro de facture
    date_now = datetime.now()
    numero = f"{type_doc[0]}{date_now.strftime('%Y%m%d%H%M%S')}"
    
    montant_total = sum(ligne['montant'] for ligne in lignes)
    
    # Créer la facture
    c.execute('''INSERT INTO factures (numero, date, client_id, client_nom, montant_total, type, statut)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (numero, date_now.strftime("%Y-%m-%d"), client_id, client_nom, 
               montant_total, type_doc, "Payée" if type_doc == "Facture" else "En attente"))
    
    facture_id = c.lastrowid
    
    # Ajouter les lignes
    for ligne in lignes:
        c.execute('''INSERT INTO lignes_facture (facture_id, produit_nom, quantite, prix_unitaire, montant)
                     VALUES (?, ?, ?, ?, ?)''',
                  (facture_id, ligne['produit'], ligne['quantite'], 
                   ligne['prix_unitaire'], ligne['montant']))
        
        # Mettre à jour le stock si c'est une facture
        if type_doc == "Facture":
            c.execute("SELECT id FROM produits WHERE nom=?", (ligne['produit'],))
            produit = c.fetchone()
            if produit:
                modifier_stock(produit[0], ligne['quantite'], "Sortie", numero)
    
    conn.commit()
    conn.close()
    return numero

def obtenir_factures():
    conn = sqlite3.connect('energie_solaire.db')
    df = pd.read_sql_query("SELECT * FROM factures ORDER BY date DESC", conn)
    conn.close()
    return df

# Interface principale
def main():
    init_db()
    
    st.title("☀️ Energie Solaire Sénégal")
    st.subheader("Système de Gestion Complet")
    
    # Menu latéral
    menu = st.sidebar.selectbox(
        "Menu Principal",
        ["🏠 Tableau de Bord", "📦 Gestion des Produits", "👥 Gestion des Clients", 
         "📄 Factures & Devis", "📊 Stocks", "📈 Rapports"]
    )
    
    # TABLEAU DE BORD
    if menu == "🏠 Tableau de Bord":
        st.header("Tableau de Bord")
        
        col1, col2, col3, col4 = st.columns(4)
        
        produits_df = obtenir_produits()
        factures_df = obtenir_factures()
        clients_df = obtenir_clients()
        
        with col1:
            st.metric("Produits en stock", len(produits_df))
        with col2:
            st.metric("Clients", len(clients_df))
        with col3:
            factures_mois = factures_df[factures_df['date'].str.startswith(datetime.now().strftime("%Y-%m"))]
            st.metric("Factures ce mois", len(factures_mois))
        with col4:
            ca_mois = factures_mois[factures_mois['type'] == 'Facture']['montant_total'].sum()
            st.metric("CA ce mois", f"{ca_mois:,.0f} FCFA")
        
        st.markdown("---")
        
        # Alertes stock
        st.subheader("⚠️ Alertes Stock")
        if not produits_df.empty:
            alertes = produits_df[produits_df['stock_actuel'] <= produits_df['stock_min']]
            if not alertes.empty:
                st.warning(f"**{len(alertes)} produit(s) en rupture ou stock faible**")
                st.dataframe(alertes[['nom', 'stock_actuel', 'stock_min']], use_container_width=True)
            else:
                st.success("Tous les stocks sont à niveau ✓")
        
        # Graphiques
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Ventes par Catégorie")
            if not produits_df.empty:
                cat_counts = produits_df['categorie'].value_counts()
                fig = px.pie(values=cat_counts.values, names=cat_counts.index)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Évolution CA (7 derniers jours)")
            if not factures_df.empty and len(factures_df) > 0:
                factures_df['date'] = pd.to_datetime(factures_df['date'])
                ventes_jour = factures_df.groupby('date')['montant_total'].sum().reset_index()
                fig = px.line(ventes_jour, x='date', y='montant_total')
                st.plotly_chart(fig, use_container_width=True)
    
    # GESTION DES PRODUITS
    elif menu == "📦 Gestion des Produits":
        st.header("Gestion des Produits")
        
        tab1, tab2, tab3 = st.tabs(["Liste des Produits", "Ajouter un Produit", "Modifier un Produit"])
        
        with tab1:
            produits_df = obtenir_produits()
            if not produits_df.empty:
                st.dataframe(produits_df, use_container_width=True)
            else:
                st.info("Aucun produit enregistré. Ajoutez votre premier produit!")
        
        with tab2:
            with st.form("form_produit"):
                col1, col2 = st.columns(2)
                
                with col1:
                    nom = st.text_input("Nom du produit *")
                    categorie = st.selectbox("Catégorie", 
                        ["Panneau Solaire", "Batterie", "Onduleur", "Régulateur", 
                         "Câbles", "Accessoires", "Autre"])
                    prix_achat = st.number_input("Prix d'achat (FCFA)", min_value=0.0, step=1000.0)
                    prix_vente = st.number_input("Prix de vente (FCFA)", min_value=0.0, step=1000.0)
                
                with col2:
                    stock = st.number_input("Stock initial", min_value=0, value=0, step=1)
                    stock_min = st.number_input("Stock minimum (alerte)", min_value=0, value=5, step=1)
                    unite = st.selectbox("Unité", ["Pièce", "Mètre", "Lot", "Kit"])
                
                submitted = st.form_submit_button("➕ Ajouter le produit")
                
                if submitted:
                    if nom:
                        ajouter_produit(nom, categorie, prix_achat, prix_vente, stock, stock_min, unite)
                        st.success(f"✅ Produit '{nom}' ajouté avec succès!")
                        st.rerun()
                    else:
                        st.error("Le nom du produit est obligatoire")
        
        with tab3:
            st.subheader("Modifier un Produit")
            
            produits_df = obtenir_produits()
            if not produits_df.empty:
                # Étape 1: Sélection de la catégorie
                categories_disponibles = sorted(produits_df['categorie'].unique().tolist())
                categorie_selectionnee = st.selectbox(
                    "🏷️ Étape 1: Choisissez une catégorie", 
                    [""] + categories_disponibles,
                    help="Sélectionnez d'abord la catégorie pour filtrer les produits"
                )
                
                if categorie_selectionnee:
                    # Étape 2: Sélection du produit dans la catégorie
                    produits_filtres = produits_df[produits_df['categorie'] == categorie_selectionnee]
                    produits_noms = produits_filtres['nom'].tolist()
                    
                    produit_choisi = st.selectbox(
                        f"📦 Étape 2: Choisissez un produit dans '{categorie_selectionnee}'",
                        [""] + produits_noms,
                        help=f"{len(produits_noms)} produit(s) disponible(s) dans cette catégorie"
                    )
                    
                    if produit_choisi:
                        # Étape 3: Modification du produit sélectionné
                        st.markdown(f"### ✏️ Étape 3: Modifier '{produit_choisi}'")
                        
                        # Récupérer les informations du produit sélectionné
                        produit_info = produits_df[produits_df['nom'] == produit_choisi].iloc[0]
                        
                        # Afficher les informations actuelles
                        with st.expander("📋 Informations actuelles", expanded=False):
                            col_info1, col_info2 = st.columns(2)
                            with col_info1:
                                st.write(f"**Nom:** {produit_info['nom']}")
                                st.write(f"**Catégorie:** {produit_info['categorie']}")
                                st.write(f"**Prix d'achat:** {produit_info['prix_achat']:,.0f} FCFA")
                            with col_info2:
                                st.write(f"**Prix de vente:** {produit_info['prix_vente']:,.0f} FCFA")
                                st.write(f"**Stock actuel:** {produit_info['stock_actuel']}")
                                st.write(f"**Stock minimum:** {produit_info['stock_min']}")
                        
                        # Formulaire de modification
                        with st.form("form_modifier_produit"):
                            st.markdown("#### 🔧 Modifier les informations")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                nom_modif = st.text_input("Nom du produit *", value=produit_info['nom'])
                                categorie_modif = st.selectbox("Catégorie", 
                                    ["Panneau Solaire", "Batterie", "Onduleur", "Régulateur", 
                                     "Câbles", "Accessoires", "Autre"],
                                    index=["Panneau Solaire", "Batterie", "Onduleur", "Régulateur", 
                                           "Câbles", "Accessoires", "Autre"].index(produit_info['categorie']) 
                                          if produit_info['categorie'] in ["Panneau Solaire", "Batterie", "Onduleur", "Régulateur", 
                                                                            "Câbles", "Accessoires", "Autre"] else 0)
                                prix_achat_modif = st.number_input("Prix d'achat (FCFA)", min_value=0.0, step=1000.0, 
                                                                 value=float(produit_info['prix_achat'] or 0))
                                prix_vente_modif = st.number_input("Prix de vente (FCFA)", min_value=0.0, step=1000.0, 
                                                                 value=float(produit_info['prix_vente'] or 0))
                            
                            with col2:
                                stock_modif = st.number_input("Stock actuel", min_value=0, step=1, 
                                                            value=int(produit_info['stock_actuel'] or 0))
                                stock_min_modif = st.number_input("Stock minimum (alerte)", min_value=0, step=1, 
                                                                value=int(produit_info['stock_min'] or 0))
                                unite_modif = st.selectbox("Unité", ["Pièce", "Mètre", "Lot", "Kit"],
                                                         index=["Pièce", "Mètre", "Lot", "Kit"].index(produit_info['unite']) 
                                                               if produit_info['unite'] in ["Pièce", "Mètre", "Lot", "Kit"] else 0)
                            
                            # Calcul automatique de la marge
                            if prix_achat_modif > 0 and prix_vente_modif > 0:
                                marge = ((prix_vente_modif - prix_achat_modif) / prix_achat_modif) * 100
                                st.info(f"💰 Marge bénéficiaire: {marge:.1f}%")
                            
                            submitted_modif = st.form_submit_button("💾 Modifier le produit", type="primary")
                            
                            if submitted_modif:
                                if nom_modif:
                                    modifier_produit(produit_info['id'], nom_modif, categorie_modif, 
                                                   prix_achat_modif, prix_vente_modif, stock_modif, 
                                                   stock_min_modif, unite_modif)
                                    st.success(f"✅ Produit '{nom_modif}' modifié avec succès!")
                                    st.rerun()
                                else:
                                    st.error("Le nom du produit est obligatoire")
                    else:
                        st.info("👆 Sélectionnez un produit pour le modifier")
                else:
                    st.info("👆 Commencez par sélectionner une catégorie")
            else:
                st.info("Aucun produit disponible pour modification. Ajoutez d'abord des produits!")
    
    # GESTION DES CLIENTS
    elif menu == "👥 Gestion des Clients":
        st.header("Gestion des Clients")
        
        tab1, tab2 = st.tabs(["Liste des Clients", "Ajouter un Client"])
        
        with tab1:
            clients_df = obtenir_clients()
            if not clients_df.empty:
                st.dataframe(clients_df, use_container_width=True)
            else:
                st.info("Aucun client enregistré.")
        
        with tab2:
            with st.form("form_client"):
                nom = st.text_input("Nom du client *")
                telephone = st.text_input("Téléphone")
                adresse = st.text_area("Adresse")
                email = st.text_input("Email")
                
                submitted = st.form_submit_button("➕ Ajouter le client")
                
                if submitted:
                    if nom:
                        ajouter_client(nom, telephone, adresse, email)
                        st.success(f"✅ Client '{nom}' ajouté avec succès!")
                        st.rerun()
                    else:
                        st.error("Le nom du client est obligatoire")
    
    # FACTURES & DEVIS
    elif menu == "📄 Factures & Devis":
        st.header("Factures & Devis")
        
        tab1, tab2 = st.tabs(["Créer Facture/Devis", "Historique"])
        
        with tab1:
            type_doc = st.radio("Type de document", ["Facture", "Devis"], horizontal=True)
            
            # Sélection client
            clients_df = obtenir_clients()
            if clients_df.empty:
                st.warning("⚠️ Vous devez d'abord ajouter des clients")
            else:
                client_choix = st.selectbox("Sélectionner un client", 
                    clients_df['nom'].tolist())
                client_id = clients_df[clients_df['nom'] == client_choix]['id'].values[0]
                
                st.markdown("---")
                st.subheader("Articles")
                
                # Initialiser le panier dans session_state
                if 'panier' not in st.session_state:
                    st.session_state.panier = []
                
                # Ajouter un article
                produits_df = obtenir_produits()
                if not produits_df.empty:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        produit_choix = st.selectbox("Produit", produits_df['nom'].tolist(), key="sel_prod")
                    with col2:
                        quantite = st.number_input("Qté", min_value=1, value=1, key="qte_prod")
                    with col3:
                        st.write("")
                        st.write("")
                        if st.button("➕ Ajouter"):
                            produit_info = produits_df[produits_df['nom'] == produit_choix].iloc[0]
                            prix_unit = produit_info['prix_vente']
                            
                            st.session_state.panier.append({
                                'produit': produit_choix,
                                'quantite': quantite,
                                'prix_unitaire': prix_unit,
                                'montant': quantite * prix_unit
                            })
                            st.rerun()
                
                # Afficher le panier
                if st.session_state.panier:
                    st.markdown("### Panier")
                    panier_df = pd.DataFrame(st.session_state.panier)
                    st.dataframe(panier_df, use_container_width=True)
                    
                    total = panier_df['montant'].sum()
                    st.markdown(f"### **Total: {total:,.0f} FCFA**")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"✅ Créer {type_doc}", type="primary", use_container_width=True):
                            numero = creer_facture(client_id, client_choix, 
                                                 st.session_state.panier, type_doc)
                            st.success(f"✅ {type_doc} N° {numero} créé(e) avec succès!")
                            st.session_state.panier = []
                            st.rerun()
                    
                    with col2:
                        if st.button("🗑️ Vider le panier", use_container_width=True):
                            st.session_state.panier = []
                            st.rerun()
        
        with tab2:
            factures_df = obtenir_factures()
            if not factures_df.empty:
                # Filtres
                col1, col2 = st.columns(2)
                with col1:
                    filtre_type = st.multiselect("Type", ["Facture", "Devis"], default=["Facture", "Devis"])
                with col2:
                    filtre_statut = st.multiselect("Statut", ["Payée", "En attente"], 
                                                   default=["Payée", "En attente"])
                
                factures_filtrees = factures_df[
                    (factures_df['type'].isin(filtre_type)) &
                    (factures_df['statut'].isin(filtre_statut))
                ]
                
                st.dataframe(factures_filtrees, use_container_width=True)
                
                # Statistiques
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                with col1:
                    total_factures = factures_filtrees[factures_filtrees['type']=='Facture']['montant_total'].sum()
                    st.metric("Total Factures", f"{total_factures:,.0f} FCFA")
                with col2:
                    total_devis = factures_filtrees[factures_filtrees['type']=='Devis']['montant_total'].sum()
                    st.metric("Total Devis", f"{total_devis:,.0f} FCFA")
                with col3:
                    nb_docs = len(factures_filtrees)
                    st.metric("Nombre de documents", nb_docs)
            else:
                st.info("Aucune facture ou devis enregistré(e).")
    
    # GESTION DES STOCKS
    elif menu == "📊 Stocks":
        st.header("Gestion des Stocks")
        
        tab1, tab2 = st.tabs(["Mouvement de Stock", "Historique des Mouvements"])
        
        with tab1:
            produits_df = obtenir_produits()
            if not produits_df.empty:
                st.subheader("Enregistrer un mouvement")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    produit_choix = st.selectbox("Produit", produits_df['nom'].tolist())
                    produit_id = produits_df[produits_df['nom'] == produit_choix]['id'].values[0]
                    stock_actuel = produits_df[produits_df['nom'] == produit_choix]['stock_actuel'].values[0]
                    st.info(f"Stock actuel: **{stock_actuel}**")
                
                with col2:
                    type_mouv = st.selectbox("Type de mouvement", ["Entrée", "Sortie"])
                    quantite = st.number_input("Quantité", min_value=1, value=1)
                    reference = st.text_input("Référence (bon de livraison, etc.)")
                
                if st.button("✅ Enregistrer le mouvement", type="primary"):
                    if type_mouv == "Sortie" and quantite > stock_actuel:
                        st.error("❌ Stock insuffisant!")
                    else:
                        modifier_stock(produit_id, quantite, type_mouv, reference)
                        st.success(f"✅ Mouvement enregistré!")
                        st.rerun()
            else:
                st.warning("Aucun produit disponible. Ajoutez d'abord des produits.")
        
        with tab2:
            conn = sqlite3.connect('energie_solaire.db')
            mouvements_df = pd.read_sql_query(
                "SELECT * FROM mouvements_stock ORDER BY date DESC LIMIT 100", conn)
            conn.close()
            
            if not mouvements_df.empty:
                st.dataframe(mouvements_df, use_container_width=True)
            else:
                st.info("Aucun mouvement de stock enregistré.")
    
    # RAPPORTS
    elif menu == "📈 Rapports":
        st.header("Rapports et Statistiques")
        
        factures_df = obtenir_factures()
        produits_df = obtenir_produits()
        
        if not factures_df.empty:
            # CA par mois
            st.subheader("Chiffre d'Affaires par Mois")
            factures_df['date'] = pd.to_datetime(factures_df['date'])
            factures_df['mois'] = factures_df['date'].dt.to_period('M').astype(str)
            ca_mois = factures_df[factures_df['type']=='Facture'].groupby('mois')['montant_total'].sum()
            
            fig = px.bar(x=ca_mois.index, y=ca_mois.values, 
                        labels={'x': 'Mois', 'y': 'CA (FCFA)'})
            st.plotly_chart(fig, use_container_width=True)
            
            # Top clients
            st.subheader("Top 10 Clients")
            top_clients = factures_df[factures_df['type']=='Facture'].groupby('client_nom')['montant_total'].sum().sort_values(ascending=False).head(10)
            st.bar_chart(top_clients)
            
            # Valeur du stock
            st.subheader("Valeur du Stock")
            if not produits_df.empty:
                produits_df['valeur_stock'] = produits_df['stock_actuel'] * produits_df['prix_achat']
                valeur_totale = produits_df['valeur_stock'].sum()
                st.metric("Valeur totale du stock", f"{valeur_totale:,.0f} FCFA")
                
                fig = px.bar(produits_df.nlargest(10, 'valeur_stock'), 
                           x='nom', y='valeur_stock',
                           title="Top 10 Produits par Valeur")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Pas encore de données pour générer des rapports.")
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.info("💡 **Energie Solaire Sénégal**\n\nSystème de gestion v1.0")

if __name__ == "__main__":
    main()
