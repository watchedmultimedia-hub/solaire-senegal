"""
Module IA Matar - Assistant intelligent pour la gestion de stock
Répond aux questions sur les stocks, inventaires et produits
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import json
import re
from firebase_config import get_all_products_from_firebase, get_stock_movements_from_firebase

class MatarAI:
    def __init__(self):
        self.name = "Matar"
        self.greeting = "👋 Salut ! Je suis Matar, votre assistant IA pour la gestion de stock. Posez-moi toutes vos questions sur les stocks, inventaires et produits !"
        
        # Initialiser l'historique de conversation
        if 'matar_chat_history' not in st.session_state:
            st.session_state.matar_chat_history = []
    
    def get_stock_data(self):
        """Récupère les données de stock depuis Firebase"""
        try:
            products = get_all_products_from_firebase()
            if products:
                products_list = []
                for product_id, product in products.items():
                    products_list.append({
                        'id': product_id,
                        'nom': product.get('nom', ''),
                        'categorie': product.get('categorie', ''),
                        'prix_achat': product.get('prix_achat', 0),
                        'prix_vente': product.get('prix_vente', 0),
                        'stock_actuel': product.get('stock_actuel', product.get('quantite', 0)),
                        'stock_min': product.get('stock_minimum', product.get('stock_min', 0)),
                        'unite': product.get('unite', 'pièce')
                    })
                return pd.DataFrame(products_list)
            return pd.DataFrame()
        except Exception as e:
            st.error(f"Erreur lors du chargement des données: {e}")
            return pd.DataFrame()
    
    def analyze_question(self, question):
        """Analyse la question de l'utilisateur et génère une réponse appropriée"""
        question_lower = question.lower()
        
        # Récupérer les données de stock
        df = self.get_stock_data()
        
        if df.empty:
            return "❌ Désolé, je ne peux pas accéder aux données de stock actuellement."
        
        # Questions sur les quantités spécifiques
        if any(word in question_lower for word in ['combien', 'quantité', 'nombre', 'stock']):
            return self.handle_quantity_questions(question_lower, df)
        
        # Questions sur les catégories
        elif any(word in question_lower for word in ['catégorie', 'type', 'genre']):
            return self.handle_category_questions(question_lower, df)
        
        # Questions sur les alertes/ruptures
        elif any(word in question_lower for word in ['alerte', 'rupture', 'manque', 'faible', 'critique']):
            return self.handle_alert_questions(df)
        
        # Questions sur les prix
        elif any(word in question_lower for word in ['prix', 'coût', 'valeur', 'montant']):
            return self.handle_price_questions(question_lower, df)
        
        # Questions générales sur le stock
        elif any(word in question_lower for word in ['total', 'global', 'ensemble', 'tout']):
            return self.handle_general_questions(df)
        
        # Questions sur des produits spécifiques
        else:
            return self.handle_specific_product_questions(question_lower, df)
    
    def handle_quantity_questions(self, question, df):
        """Gère les questions sur les quantités"""
        response = "📊 **Informations sur les quantités :**\n\n"
        
        # Recherche de produits spécifiques mentionnés
        found_products = []
        for _, product in df.iterrows():
            if any(word in question for word in product['nom'].lower().split()):
                found_products.append(product)
        
        if found_products:
            for product in found_products:
                response += f"• **{product['nom']}** : {product['stock_actuel']} {product['unite']} en stock\n"
                if product['stock_actuel'] <= product['stock_min']:
                    response += f"  ⚠️ *Stock faible (minimum: {product['stock_min']})*\n"
        else:
            # Afficher un résumé par catégorie
            category_summary = df.groupby('categorie')['stock_actuel'].sum().sort_values(ascending=False)
            response += "**Résumé par catégorie :**\n"
            for category, total in category_summary.items():
                response += f"• {category}: {total} unités\n"
        
        return response
    
    def handle_category_questions(self, question, df):
        """Gère les questions sur les catégories"""
        categories = df['categorie'].value_counts()
        
        response = "📂 **Informations par catégorie :**\n\n"
        for category, count in categories.items():
            total_stock = df[df['categorie'] == category]['stock_actuel'].sum()
            response += f"• **{category}** : {count} produits différents, {total_stock} unités en stock\n"
        
        return response
    
    def handle_alert_questions(self, df):
        """Gère les questions sur les alertes de stock"""
        low_stock = df[df['stock_actuel'] <= df['stock_min']]
        out_of_stock = df[df['stock_actuel'] == 0]
        
        response = "⚠️ **État des alertes de stock :**\n\n"
        
        if not out_of_stock.empty:
            response += "🔴 **Ruptures de stock :**\n"
            for _, product in out_of_stock.iterrows():
                response += f"• {product['nom']} (catégorie: {product['categorie']})\n"
            response += "\n"
        
        if not low_stock.empty:
            response += "🟡 **Stocks faibles :**\n"
            for _, product in low_stock.iterrows():
                if product['stock_actuel'] > 0:
                    response += f"• {product['nom']}: {product['stock_actuel']}/{product['stock_min']} {product['unite']}\n"
            response += "\n"
        
        if out_of_stock.empty and low_stock.empty:
            response += "✅ **Aucune alerte de stock ! Tous les produits sont à niveau.**\n"
        
        return response
    
    def handle_price_questions(self, question, df):
        """Gère les questions sur les prix"""
        response = "💰 **Informations sur les prix :**\n\n"
        
        total_value_achat = (df['stock_actuel'] * df['prix_achat']).sum()
        total_value_vente = (df['stock_actuel'] * df['prix_vente']).sum()
        
        response += f"• **Valeur totale du stock (prix d'achat)** : {total_value_achat:,.0f} FCFA\n"
        response += f"• **Valeur totale du stock (prix de vente)** : {total_value_vente:,.0f} FCFA\n"
        response += f"• **Marge potentielle** : {total_value_vente - total_value_achat:,.0f} FCFA\n\n"
        
        # Top 5 produits par valeur
        df['valeur_stock'] = df['stock_actuel'] * df['prix_achat']
        top_products = df.nlargest(5, 'valeur_stock')
        
        response += "**Top 5 produits par valeur en stock :**\n"
        for _, product in top_products.iterrows():
            response += f"• {product['nom']}: {product['valeur_stock']:,.0f} FCFA\n"
        
        return response
    
    def handle_general_questions(self, df):
        """Gère les questions générales sur le stock"""
        total_products = len(df)
        total_categories = df['categorie'].nunique()
        total_units = df['stock_actuel'].sum()
        
        response = "📈 **Vue d'ensemble du stock :**\n\n"
        response += f"• **Nombre total de produits** : {total_products}\n"
        response += f"• **Nombre de catégories** : {total_categories}\n"
        response += f"• **Unités totales en stock** : {total_units}\n\n"
        
        # Statistiques par catégorie
        response += "**Répartition par catégorie :**\n"
        category_stats = df.groupby('categorie').agg({
            'stock_actuel': 'sum',
            'nom': 'count'
        }).round(2)
        
        for category, stats in category_stats.iterrows():
            response += f"• {category}: {stats['nom']} produits, {stats['stock_actuel']} unités\n"
        
        return response
    
    def handle_specific_product_questions(self, question, df):
        """Gère les questions sur des produits spécifiques"""
        # Recherche de produits mentionnés dans la question
        found_products = []
        
        for _, product in df.iterrows():
            product_words = product['nom'].lower().split()
            if any(word in question for word in product_words):
                found_products.append(product)
        
        if found_products:
            response = "🔍 **Produits trouvés :**\n\n"
            for product in found_products:
                response += f"**{product['nom']}**\n"
                response += f"• Catégorie: {product['categorie']}\n"
                response += f"• Stock actuel: {product['stock_actuel']} {product['unite']}\n"
                response += f"• Stock minimum: {product['stock_min']} {product['unite']}\n"
                response += f"• Prix d'achat: {product['prix_achat']:,.0f} FCFA\n"
                response += f"• Prix de vente: {product['prix_vente']:,.0f} FCFA\n"
                
                if product['stock_actuel'] <= product['stock_min']:
                    response += "⚠️ *Stock faible ou en rupture*\n"
                response += "\n"
        else:
            response = "❓ Je n'ai pas trouvé de produit correspondant à votre question. Essayez d'être plus spécifique ou demandez-moi un aperçu général du stock."
        
        return response
    
    def display_chat_interface(self):
        """Affiche l'interface de chat avec Matar"""
        st.subheader("🤖 Matar - Assistant Stock")
        st.caption("Posez-moi toutes vos questions sur le stock, les inventaires et les produits !")
        
        # Zone de chat
        chat_container = st.container()
        
        with chat_container:
            # Afficher l'historique de conversation
            if st.session_state.matar_chat_history:
                for i, message in enumerate(st.session_state.matar_chat_history):
                    if message['role'] == 'user':
                        st.chat_message("user").write(message['content'])
                    else:
                        st.chat_message("assistant").write(message['content'])
            else:
                # Message de bienvenue
                st.chat_message("assistant").write(self.greeting)
        
        # Zone de saisie
        user_question = st.chat_input("Posez votre question sur le stock...")
        
        if user_question:
            # Ajouter la question de l'utilisateur à l'historique
            st.session_state.matar_chat_history.append({
                'role': 'user',
                'content': user_question,
                'timestamp': datetime.now()
            })
            
            # Générer la réponse
            with st.spinner("Matar réfléchit..."):
                response = self.analyze_question(user_question)
            
            # Ajouter la réponse à l'historique
            st.session_state.matar_chat_history.append({
                'role': 'assistant',
                'content': response,
                'timestamp': datetime.now()
            })
            
            # Recharger la page pour afficher la nouvelle conversation
            st.rerun()
        
        # Bouton pour effacer l'historique
        if st.button("🗑️ Effacer l'historique", type="secondary"):
            st.session_state.matar_chat_history = []
            st.rerun()
        
        # Suggestions de questions
        st.markdown("---")
        st.markdown("**💡 Exemples de questions que vous pouvez me poser :**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Combien de batteries lithium reste-t-il ?"):
                st.session_state.matar_chat_history.append({
                    'role': 'user',
                    'content': "Combien de batteries lithium reste-t-il ?",
                    'timestamp': datetime.now()
                })
                response = self.analyze_question("Combien de batteries lithium reste-t-il ?")
                st.session_state.matar_chat_history.append({
                    'role': 'assistant',
                    'content': response,
                    'timestamp': datetime.now()
                })
                st.rerun()
            
            if st.button("Quels produits sont en rupture ?"):
                st.session_state.matar_chat_history.append({
                    'role': 'user',
                    'content': "Quels produits sont en rupture ?",
                    'timestamp': datetime.now()
                })
                response = self.analyze_question("Quels produits sont en rupture ?")
                st.session_state.matar_chat_history.append({
                    'role': 'assistant',
                    'content': response,
                    'timestamp': datetime.now()
                })
                st.rerun()
        
        with col2:
            if st.button("Quelle est la valeur totale du stock ?"):
                st.session_state.matar_chat_history.append({
                    'role': 'user',
                    'content': "Quelle est la valeur totale du stock ?",
                    'timestamp': datetime.now()
                })
                response = self.analyze_question("Quelle est la valeur totale du stock ?")
                st.session_state.matar_chat_history.append({
                    'role': 'assistant',
                    'content': response,
                    'timestamp': datetime.now()
                })
                st.rerun()
            
            if st.button("Résumé par catégorie"):
                st.session_state.matar_chat_history.append({
                    'role': 'user',
                    'content': "Donne-moi un résumé par catégorie",
                    'timestamp': datetime.now()
                })
                response = self.analyze_question("Donne-moi un résumé par catégorie")
                st.session_state.matar_chat_history.append({
                    'role': 'assistant',
                    'content': response,
                    'timestamp': datetime.now()
                })
                st.rerun()

# Instance globale de Matar
matar_ai = MatarAI()