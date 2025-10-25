"""
Module d'amélioration de l'interface utilisateur pour la gestion de stock
Contient des composants visuels modernes et des fonctionnalités avancées
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

def create_modern_metric_card(title, value, delta=None, delta_color="normal", icon="📊"):
    """Crée une carte de métrique moderne avec design amélioré"""
    
    # Couleur selon le delta
    if delta_color == "positive":
        delta_style = "color: #28a745; font-weight: bold;"
        delta_icon = "↗️"
    elif delta_color == "negative":
        delta_style = "color: #dc3545; font-weight: bold;"
        delta_icon = "↘️"
    else:
        delta_style = "color: #6c757d;"
        delta_icon = "➡️"
    
    delta_html = ""
    if delta is not None:
        delta_html = f"""
        <div style="{delta_style} font-size: 14px; margin-top: 5px;">
            {delta_icon} {delta}
        </div>
        """
    
    card_html = f"""
    <div style="
        background: linear-gradient(135deg, #ffffff, #f8f9fa);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border-left: 4px solid #007bff;
        margin: 10px 0;
        transition: transform 0.2s ease;
    ">
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <span style="font-size: 24px; margin-right: 10px;">{icon}</span>
            <h4 style="margin: 0; color: #495057; font-size: 16px;">{title}</h4>
        </div>
        <div style="font-size: 32px; font-weight: bold; color: #007bff; margin: 10px 0;">
            {value}
        </div>
        {delta_html}
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)

def create_stock_alert_card(product_name, current_stock, min_stock, category=""):
    """Crée une carte d'alerte de stock avec design moderne"""
    
    # Déterminer le niveau d'alerte
    if current_stock == 0:
        alert_level = "danger"
        alert_color = "#dc3545"
        alert_icon = "🚨"
        alert_text = "RUPTURE DE STOCK"
    elif current_stock <= min_stock:
        alert_level = "warning"
        alert_color = "#ffc107"
        alert_icon = "⚠️"
        alert_text = "STOCK FAIBLE"
    else:
        alert_level = "success"
        alert_color = "#28a745"
        alert_icon = "✅"
        alert_text = "STOCK OK"
    
    category_display = f" ({category})" if category else ""
    
    card_html = f"""
    <div style="
        background: linear-gradient(135deg, #ffffff, #f8f9fa);
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        border-left: 4px solid {alert_color};
        margin: 8px 0;
        transition: transform 0.2s ease;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h5 style="margin: 0; color: #495057; font-size: 16px;">
                    {product_name}{category_display}
                </h5>
                <div style="margin-top: 5px;">
                    <span style="font-size: 18px; font-weight: bold; color: {alert_color};">
                        Stock: {current_stock}
                    </span>
                    <span style="color: #6c757d; margin-left: 10px;">
                        Min: {min_stock}
                    </span>
                </div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 24px;">{alert_icon}</div>
                <div style="font-size: 12px; color: {alert_color}; font-weight: bold;">
                    {alert_text}
                </div>
            </div>
        </div>
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)

def create_advanced_stock_chart(df_products):
    """Crée un graphique avancé de l'état du stock"""
    
    if df_products.empty:
        st.info("Aucun produit à afficher")
        return
    
    # Préparer les données
    df_chart = df_products.copy()
    df_chart['status'] = df_chart.apply(lambda row: 
        'Rupture' if row['quantite'] == 0 
        else 'Stock faible' if row['quantite'] <= row.get('stock_min', 0)
        else 'Stock OK', axis=1)
    
    df_chart['pourcentage_stock'] = df_chart.apply(lambda row:
        (row['quantite'] / max(row.get('stock_min', 1) * 2, 1)) * 100, axis=1)
    
    # Créer le graphique
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Répartition par statut', 'Stock par catégorie', 
                       'Évolution du stock', 'Top 10 produits'),
        specs=[[{"type": "pie"}, {"type": "bar"}],
               [{"type": "scatter"}, {"type": "bar"}]]
    )
    
    # Graphique en secteurs - Répartition par statut
    status_counts = df_chart['status'].value_counts()
    colors = {'Rupture': '#dc3545', 'Stock faible': '#ffc107', 'Stock OK': '#28a745'}
    
    fig.add_trace(
        go.Pie(labels=status_counts.index, values=status_counts.values,
               marker_colors=[colors.get(status, '#6c757d') for status in status_counts.index],
               name="Statut"),
        row=1, col=1
    )
    
    # Graphique en barres - Stock par catégorie
    if 'categorie' in df_chart.columns:
        cat_stock = df_chart.groupby('categorie')['quantite'].sum().reset_index()
        fig.add_trace(
            go.Bar(x=cat_stock['categorie'], y=cat_stock['quantite'],
                   marker_color='#007bff', name="Stock par catégorie"),
            row=1, col=2
        )
    
    # Simulation d'évolution du stock (derniers 30 jours)
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    stock_evolution = np.random.randint(80, 120, 30)  # Simulation
    
    fig.add_trace(
        go.Scatter(x=dates, y=stock_evolution, mode='lines+markers',
                   line=dict(color='#28a745', width=3),
                   marker=dict(size=6), name="Évolution stock"),
        row=2, col=1
    )
    
    # Top 10 produits par stock
    top_products = df_chart.nlargest(10, 'quantite')
    fig.add_trace(
        go.Bar(x=top_products['quantite'], y=top_products['nom'],
               orientation='h', marker_color='#17a2b8', name="Top produits"),
        row=2, col=2
    )
    
    # Mise à jour du layout
    fig.update_layout(
        height=800,
        showlegend=False,
        title_text="Tableau de Bord Stock - Vue d'ensemble",
        title_x=0.5,
        title_font_size=20
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_financial_overview(df_products, df_movements=None):
    """Crée un aperçu financier du stock"""
    
    if df_products.empty:
        return
    
    # Calculs financiers
    valeur_stock_achat = (df_products['quantite'] * df_products.get('prix_achat', 0)).sum()
    valeur_stock_vente = (df_products['quantite'] * df_products.get('prix_vente', 0)).sum()
    marge_potentielle = valeur_stock_vente - valeur_stock_achat
    
    # Affichage des métriques financières
    st.markdown("### 💰 Aperçu Financier")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        create_modern_metric_card(
            "Valeur Stock (Achat)",
            f"{valeur_stock_achat:,.0f} FCFA",
            icon="💵"
        )
    
    with col2:
        create_modern_metric_card(
            "Valeur Stock (Vente)",
            f"{valeur_stock_vente:,.0f} FCFA",
            icon="💰"
        )
    
    with col3:
        create_modern_metric_card(
            "Marge Potentielle",
            f"{marge_potentielle:,.0f} FCFA",
            delta=f"{((marge_potentielle/valeur_stock_achat)*100):.1f}%" if valeur_stock_achat > 0 else "N/A",
            delta_color="positive" if marge_potentielle > 0 else "negative",
            icon="📈"
        )
    
    with col4:
        nb_produits = len(df_products)
        nb_categories = df_products['categorie'].nunique() if 'categorie' in df_products.columns else 0
        create_modern_metric_card(
            "Produits / Catégories",
            f"{nb_produits} / {nb_categories}",
            icon="📦"
        )

def create_interactive_product_table(df_products):
    """Crée un tableau interactif des produits avec filtres avancés"""
    
    if df_products.empty:
        st.info("Aucun produit à afficher")
        return
    
    st.markdown("### 📋 Gestion des Produits")
    
    # Filtres
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        categories = ['Toutes'] + list(df_products['categorie'].unique()) if 'categorie' in df_products.columns else ['Toutes']
        selected_category = st.selectbox("Filtrer par catégorie", categories)
    
    with col_filter2:
        stock_filter = st.selectbox("Filtrer par stock", 
                                   ['Tous', 'Stock OK', 'Stock faible', 'Rupture de stock'])
    
    with col_filter3:
        search_term = st.text_input("Rechercher un produit", placeholder="Nom du produit...")
    
    # Appliquer les filtres
    df_filtered = df_products.copy()
    
    if selected_category != 'Toutes' and 'categorie' in df_products.columns:
        df_filtered = df_filtered[df_filtered['categorie'] == selected_category]
    
    if search_term:
        df_filtered = df_filtered[df_filtered['nom'].str.contains(search_term, case=False, na=False)]
    
    if stock_filter != 'Tous':
        if stock_filter == 'Rupture de stock':
            df_filtered = df_filtered[df_filtered['quantite'] == 0]
        elif stock_filter == 'Stock faible':
            df_filtered = df_filtered[
                (df_filtered['quantite'] > 0) & 
                (df_filtered['quantite'] <= df_filtered.get('stock_min', 0))
            ]
        elif stock_filter == 'Stock OK':
            df_filtered = df_filtered[df_filtered['quantite'] > df_filtered.get('stock_min', 0)]
    
    # Affichage du tableau avec style
    if not df_filtered.empty:
        st.markdown(f"**{len(df_filtered)} produit(s) trouvé(s)**")
        
        # Ajouter des colonnes de statut visuelles
        df_display = df_filtered.copy()
        df_display['Statut'] = df_display.apply(lambda row:
            '🚨 Rupture' if row['quantite'] == 0
            else '⚠️ Faible' if row['quantite'] <= row.get('stock_min', 0)
            else '✅ OK', axis=1)
        
        # Réorganiser les colonnes pour l'affichage
        columns_order = ['nom', 'categorie', 'quantite', 'stock_min', 'Statut']
        if 'prix_vente' in df_display.columns:
            columns_order.append('prix_vente')
        
        df_display = df_display[[col for col in columns_order if col in df_display.columns]]
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "nom": st.column_config.TextColumn("Nom du produit", width="medium"),
                "categorie": st.column_config.TextColumn("Catégorie", width="small"),
                "quantite": st.column_config.NumberColumn("Stock actuel", width="small"),
                "stock_min": st.column_config.NumberColumn("Stock min", width="small"),
                "Statut": st.column_config.TextColumn("Statut", width="small"),
                "prix_vente": st.column_config.NumberColumn("Prix vente (FCFA)", width="medium")
            }
        )
    else:
        st.warning("Aucun produit ne correspond aux critères de filtrage")

def create_movement_timeline(df_movements):
    """Crée une timeline des mouvements de stock"""
    
    if df_movements is None or df_movements.empty:
        st.info("Aucun mouvement de stock à afficher")
        return
    
    st.markdown("### 📈 Historique des Mouvements")
    
    # Préparer les données pour la timeline
    df_timeline = df_movements.copy()
    df_timeline['date'] = pd.to_datetime(df_timeline['date'])
    df_timeline = df_timeline.sort_values('date', ascending=False)
    
    # Graphique des mouvements
    fig = go.Figure()
    
    # Séparer les entrées et sorties
    entrees = df_timeline[df_timeline['type'] == 'Entrée']
    sorties = df_timeline[df_timeline['type'] == 'Sortie']
    
    if not entrees.empty:
        fig.add_trace(go.Scatter(
            x=entrees['date'],
            y=entrees['quantite'],
            mode='markers+lines',
            name='Entrées',
            marker=dict(color='#28a745', size=8),
            line=dict(color='#28a745', width=2)
        ))
    
    if not sorties.empty:
        fig.add_trace(go.Scatter(
            x=sorties['date'],
            y=sorties['quantite'].abs(),  # Valeur absolue pour l'affichage
            mode='markers+lines',
            name='Sorties',
            marker=dict(color='#dc3545', size=8),
            line=dict(color='#dc3545', width=2)
        ))
    
    fig.update_layout(
        title="Évolution des Mouvements de Stock",
        xaxis_title="Date",
        yaxis_title="Quantité",
        hovermode='x unified',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Tableau des derniers mouvements
    st.markdown("#### Derniers mouvements")
    recent_movements = df_timeline.head(10)
    
    if not recent_movements.empty:
        st.dataframe(
            recent_movements[['date', 'produit_nom', 'type', 'quantite', 'reference']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "date": st.column_config.DatetimeColumn("Date", width="medium"),
                "produit_nom": st.column_config.TextColumn("Produit", width="medium"),
                "type": st.column_config.TextColumn("Type", width="small"),
                "quantite": st.column_config.NumberColumn("Quantité", width="small"),
                "reference": st.column_config.TextColumn("Référence", width="medium")
            }
        )

def show_stock_alerts_sidebar():
    """Affiche les alertes de stock dans la sidebar"""
    
    with st.sidebar:
        st.markdown("### 🚨 Alertes Stock")
        
        try:
            # Importer la fonction pour récupérer les produits depuis Firebase
            from firebase_config import get_all_products_from_firebase
            
            # Récupérer les vrais produits depuis Firebase
            products = get_all_products_from_firebase()
            alerts = []
            
            if products:
                for product_id, product in products.items():
                    stock_actuel = product.get('stock_actuel', 0)
                    stock_min = product.get('stock_minimum', product.get('stock_min', 0))
                    nom = product.get('nom', 'Produit sans nom')
                    
                    # Vérifier les conditions d'alerte
                    if stock_actuel == 0:
                        alerts.append({
                            "nom": nom,
                            "stock": stock_actuel,
                            "min": stock_min,
                            "type": "rupture"
                        })
                    elif stock_actuel <= stock_min and stock_min > 0:
                        alerts.append({
                            "nom": nom,
                            "stock": stock_actuel,
                            "min": stock_min,
                            "type": "faible"
                        })
            
            # Afficher les alertes
            for alert in alerts:
                if alert["type"] == "rupture":
                    st.error(f"🚨 {alert['nom']}: Rupture de stock")
                else:
                    st.warning(f"⚠️ {alert['nom']}: Stock faible ({alert['stock']}/{alert['min']})")
            
            if not alerts:
                st.success("✅ Aucune alerte de stock")
                
        except Exception as e:
            st.error(f"Erreur lors du chargement des alertes: {e}")
            # Fallback en cas d'erreur
            st.info("Impossible de charger les alertes de stock")
