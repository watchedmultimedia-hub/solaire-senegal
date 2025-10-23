import firebase_admin
from firebase_admin import credentials, firestore, auth
import pyrebase
import streamlit as st
import json

# Initialisation Firebase Admin SDK
@st.cache_resource
def init_firebase_admin():
    """Initialise Firebase Admin SDK avec les secrets Streamlit"""
    try:
        if not firebase_admin._apps:
            # Utiliser les secrets Streamlit pour la configuration de Firebase Admin
            cred_dict = {
                "type": st.secrets["firebase_admin"]["type"],
                "project_id": st.secrets["firebase_admin"]["project_id"],
                "private_key_id": st.secrets["firebase_admin"]["private_key_id"],
                "private_key": st.secrets["firebase_admin"]["private_key"].replace('\\n', '\n'),
                "client_email": st.secrets["firebase_admin"]["client_email"],
                "client_id": st.secrets["firebase_admin"]["client_id"],
                "auth_uri": st.secrets["firebase_admin"]["auth_uri"],
                "token_uri": st.secrets["firebase_admin"]["token_uri"],
                "auth_provider_x509_cert_url": st.secrets["firebase_admin"]["auth_provider_x509_cert_url"],
                "client_x509_cert_url": st.secrets["firebase_admin"]["client_x509_cert_url"]
            }
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.error(f"Erreur d'initialisation Firebase Admin: {e}")
        return None

# Initialisation Pyrebase pour l'authentification
@st.cache_resource
def init_pyrebase():
    """Initialise Pyrebase pour l'authentification côté client"""
    try:
        firebase = pyrebase.initialize_app(st.secrets["pyrebase"])
        return firebase.auth()
    except Exception as e:
        st.error(f"Erreur d'initialisation Pyrebase: {e}")
        return None

# Fonctions d'authentification
def login_user(email, password):
    """Connecte un utilisateur avec email/mot de passe"""
    try:
        auth_client = init_pyrebase()
        if auth_client is None:
            print("Erreur: Impossible d'initialiser Pyrebase")
            return None
        
        user = auth_client.sign_in_with_email_and_password(email, password)
        print(f"Connexion réussie pour: {email}")
        return user
    except Exception as e:
        print(f"Erreur de connexion pour {email}: {str(e)}")
        # Afficher plus de détails sur l'erreur
        if "INVALID_EMAIL" in str(e):
            print("Erreur: Format d'email invalide")
        elif "EMAIL_NOT_FOUND" in str(e):
            print("Erreur: Email non trouvé")
        elif "INVALID_PASSWORD" in str(e):
            print("Erreur: Mot de passe incorrect")
        elif "USER_DISABLED" in str(e):
            print("Erreur: Compte utilisateur désactivé")
        return None

def logout_user():
    """Déconnecte l'utilisateur"""
    if 'user_token' in st.session_state:
        del st.session_state['user_token']
    if 'user_email' in st.session_state:
        del st.session_state['user_email']
    if 'is_admin' in st.session_state:
        del st.session_state['is_admin']

def is_user_authenticated():
    return 'user_token' in st.session_state

def is_admin_user():
    return st.session_state.get('is_admin', False)


def _get_secret_list(name: str):
    try:
        val = st.secrets.get(name)
        if val is None:
            return []
        if isinstance(val, list):
            return [str(x).strip().lower() for x in val if str(x).strip()]
        if isinstance(val, str):
            return [x.strip().lower() for x in val.split(',') if x.strip()]
    except Exception:
        pass
    return []


def is_admin_email(email: str) -> bool:
    """Retourne True si l'email est admin via allowlist des domaines/emails.
    - Peut être paramétré via st.secrets['ADMIN_DOMAINS'] et st.secrets['ADMIN_EMAILS'].
    - Par défaut autorise les domaines 'energiesolairesenegal.com' et 'orange-sonatel.com'.
    - Et autorise explicitement l'email 'energiesolairesenegal@gmail.com'.
    """
    try:
        if not email or '@' not in email:
            return False
        email_lower = email.strip().lower()
        domain = email_lower.split('@')[-1]
        allowed_domains = set(_get_secret_list('ADMIN_DOMAINS') or ['energiesolairesenegal.com', 'orange-sonatel.com'])
        allowed_emails = set(_get_secret_list('ADMIN_EMAILS') or ['energiesolairesenegal@gmail.com'])
        return (email_lower in allowed_emails) or (domain in allowed_domains)
    except Exception:
        return False

def save_quote_to_firebase(quote_data):
    """Sauvegarde un devis dans Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            doc_ref = db.collection('devis').add(quote_data)
            return doc_ref[1].id
    except Exception as e:
        st.error(f"Erreur sauvegarde devis: {e}")
        return None

@st.cache_data(ttl=120)
def get_all_quotes():
    """Récupère tous les devis depuis Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            quotes = db.collection('devis').stream()
            return [{'id': doc.id, **doc.to_dict()} for doc in quotes]
    except Exception as e:
        st.error(f"Erreur récupération devis: {e}")
        return []

def save_equipment_prices(prices_data):
    """Sauvegarde les prix des équipements dans Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            db.collection('config').document('equipment_prices').set(prices_data)
            return True
    except Exception as e:
        st.error(f"Erreur sauvegarde prix: {e}")
        return False

@st.cache_data(ttl=3600)
def get_equipment_prices():
    """Récupère les prix des équipements depuis Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            doc = db.collection('config').document('equipment_prices').get()
            if doc.exists:
                return doc.to_dict()
    except Exception as e:
        st.error(f"Erreur récupération prix: {e}")
    return None

def save_client_request(request_data):
    """Sauvegarde une demande client dans Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            # Ajouter timestamp et statut par défaut
            request_data['timestamp'] = firestore.SERVER_TIMESTAMP
            request_data['status'] = 'nouveau'  # nouveau, en_cours, traite, ferme
            request_data['admin_notes'] = ''
            
            doc_ref = db.collection('demandes_clients').add(request_data)
            return doc_ref[1].id
    except Exception as e:
        st.error(f"Erreur sauvegarde demande: {e}")
        return None

@st.cache_data(ttl=120)
def get_all_client_requests():
    """Récupère toutes les demandes clients depuis Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            requests = db.collection('demandes_clients').order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
            return [{'id': doc.id, **doc.to_dict()} for doc in requests]
    except Exception as e:
        st.error(f"Erreur récupération demandes: {e}")
        return []

def update_client_request_status(request_id, status, admin_notes=""):
    """Met à jour le statut d'une demande client"""
    try:
        db = init_firebase_admin()
        if db:
            db.collection('demandes_clients').document(request_id).update({
                'status': status,
                'admin_notes': admin_notes,
                'last_updated': firestore.SERVER_TIMESTAMP
            })
            return True
    except Exception as e:
        st.error(f"Erreur mise à jour demande: {e}")
        return False

def initialize_equipment_prices_in_firebase(prices_data):
    """Initialise les prix des équipements dans Firebase (première fois)"""
    try:
        db = init_firebase_admin()
        if db:
            # Vérifier si les prix existent déjà
            doc = db.collection('config').document('equipment_prices').get()
            if not doc.exists:
                # Ajouter timestamp d'initialisation
                prices_data['_initialized_at'] = firestore.SERVER_TIMESTAMP
                prices_data['_version'] = '1.0'
                db.collection('config').document('equipment_prices').set(prices_data)
                return True, "Prices initialized successfully"
            else:
                return False, "Prices already exist in database"
    except Exception as e:
        st.error(f"Erreur initialisation prix: {e}")
        return False, f"Error: {e}"

def delete_quote(quote_id: str) -> bool:
    """Supprime un devis à partir de son ID Firestore"""
    try:
        db = init_firebase_admin()
        if db and quote_id:
            db.collection('devis').document(quote_id).delete()
            return True
    except Exception as e:
        st.error(f"Erreur suppression devis: {e}")
    return False

def delete_client_request(request_id: str) -> bool:
    """Supprime une demande client à partir de son ID Firestore"""
    try:
        db = init_firebase_admin()
        if db and request_id:
            db.collection('demandes_clients').document(request_id).delete()
            return True
    except Exception as e:
        st.error(f"Erreur suppression demande: {e}")
    return False