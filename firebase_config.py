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
            new_id = None
            try:
                new_id = doc_ref[1].id
            except Exception:
                pass
            # Journalisation de création de devis (after seulement)
            try:
                log_change(
                    event_type='quote.create',
                    item_id=new_id,
                    description='Création d\'un devis',
                    before=None,
                    after={**quote_data, 'id': new_id} if isinstance(quote_data, dict) else quote_data,
                    metadata={'collection': 'devis'}
                )
            except Exception:
                pass
            return new_id
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
            doc_ref = db.collection('config').document('equipment_prices')
            try:
                snap = doc_ref.get()
                before_doc = snap.to_dict() if snap.exists else None
            except Exception:
                before_doc = None
            doc_ref.set(prices_data)
            try:
                log_change(
                    event_type='equipment_prices.update',
                    item_id='equipment_prices',
                    description='Mise à jour des prix équipements',
                    before=before_doc,
                    after=prices_data,
                    metadata={'collection': 'config'}
                )
            except Exception:
                pass
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
            new_id = None
            try:
                new_id = doc_ref[1].id
            except Exception:
                pass
            # Journaliser création de demande (after seulement)
            try:
                log_change(
                    event_type='client_request.create',
                    item_id=new_id,
                    description='Création d\'une demande client',
                    before=None,
                    after={**request_data, 'id': new_id} if isinstance(request_data, dict) else request_data,
                    metadata={'collection': 'demandes_clients'}
                )
            except Exception:
                pass
            return new_id
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
            doc_ref = db.collection('demandes_clients').document(request_id)
            try:
                snap_before = doc_ref.get()
                before_doc = snap_before.to_dict() if snap_before.exists else None
            except Exception:
                before_doc = None
            doc_ref.update({
                'status': status,
                'admin_notes': admin_notes,
                'last_updated': firestore.SERVER_TIMESTAMP
            })
            try:
                snap_after = doc_ref.get()
                after_doc = snap_after.to_dict() if snap_after.exists else {'status': status, 'admin_notes': admin_notes}
            except Exception:
                after_doc = {'status': status, 'admin_notes': admin_notes}
            try:
                log_change(
                    event_type='client_request.update',
                    item_id=request_id,
                    description='Mise à jour de la demande client',
                    before=before_doc,
                    after=after_doc,
                    metadata={'collection': 'demandes_clients'}
                )
            except Exception:
                pass
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
            doc_ref = db.collection('config').document('equipment_prices')
            doc = doc_ref.get()
            if not doc.exists:
                # Ajouter timestamp d'initialisation
                prices_data['_initialized_at'] = firestore.SERVER_TIMESTAMP
                prices_data['_version'] = '1.0'
                doc_ref.set(prices_data)
                try:
                    log_change(
                        event_type='equipment_prices.init',
                        item_id='equipment_prices',
                        description='Initialisation des prix équipements',
                        before=None,
                        after=prices_data,
                        metadata={'collection': 'config'}
                    )
                except Exception:
                    pass
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
            doc_ref = db.collection('devis').document(quote_id)
            try:
                snap = doc_ref.get()
                before_doc = snap.to_dict() if snap.exists else None
            except Exception:
                before_doc = None
            doc_ref.delete()
            try:
                log_change(
                    event_type='quote.delete',
                    item_id=quote_id,
                    description='Suppression d\'un devis',
                    before=before_doc,
                    after=None,
                    metadata={'collection': 'devis'}
                )
            except Exception:
                pass
            return True
    except Exception as e:
        st.error(f"Erreur suppression devis: {e}")
    return False


def delete_client_request(request_id: str) -> bool:
    """Supprime une demande client à partir de son ID Firestore"""
    try:
        db = init_firebase_admin()
        if db and request_id:
            doc_ref = db.collection('demandes_clients').document(request_id)
            try:
                snap = doc_ref.get()
                before_doc = snap.to_dict() if snap.exists else None
            except Exception:
                before_doc = None
            doc_ref.delete()
            try:
                log_change(
                    event_type='client_request.delete',
                    item_id=request_id,
                    description='Suppression d\'une demande client',
                    before=before_doc,
                    after=None,
                    metadata={'collection': 'demandes_clients'}
                )
            except Exception:
                pass
            return True
    except Exception as e:
        st.error(f"Erreur suppression demande: {e}")
    return False


def save_labor_percentages(percentages_data):
    """Sauvegarde les pourcentages de main d'œuvre par région dans Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            doc_ref = db.collection('config').document('labor_percentages')
            try:
                snap = doc_ref.get()
                before_doc = snap.to_dict() if snap.exists else None
            except Exception:
                before_doc = None
            doc_ref.set(percentages_data)
            try:
                log_change(
                    event_type='labor_percentages.update',
                    item_id='labor_percentages',
                    description='Mise à jour des pourcentages main d\'œuvre',
                    before=before_doc,
                    after=percentages_data,
                    metadata={'collection': 'config'}
                )
            except Exception:
                pass
            return True
    except Exception as e:
        st.error(f"Erreur sauvegarde pourcentages main d'œuvre: {e}")
        return False

@st.cache_data(ttl=3600)
def get_labor_percentages():
    """Récupère les pourcentages de main d'œuvre depuis Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            doc = db.collection('config').document('labor_percentages').get()
            if doc.exists:
                return doc.to_dict()
    except Exception as e:
        st.error(f"Erreur récupération pourcentages main d'œuvre: {e}")
    return None


def clear_labor_percentages_cache():
    """Vide le cache des pourcentages de main d'œuvre"""
    get_labor_percentages.clear()


def save_accessories_rate(rate_data):
    """Sauvegarde le taux d'accessoires dans Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            doc_ref = db.collection('config').document('accessories_rate')
            try:
                snap = doc_ref.get()
                before_doc = snap.to_dict() if snap.exists else None
            except Exception:
                before_doc = None
            doc_ref.set(rate_data)
            try:
                log_change(
                    event_type='accessories_rate.update',
                    item_id='accessories_rate',
                    description='Mise à jour du taux accessoires',
                    before=before_doc,
                    after=rate_data,
                    metadata={'collection': 'config'}
                )
            except Exception:
                pass
            return True
    except Exception as e:
        st.error(f"Erreur sauvegarde taux accessoires: {e}")
        return False

@st.cache_data(ttl=3600)
def get_accessories_rate():
    """Récupère le taux d'accessoires depuis Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            doc = db.collection('config').document('accessories_rate').get()
            if doc.exists:
                return doc.to_dict()
    except Exception as e:
        st.error(f"Erreur récupération taux accessoires: {e}")
    return None


def clear_accessories_rate_cache():
    """Vide le cache du taux d'accessoires"""
    get_accessories_rate.clear()


def initialize_accessories_rate_in_firebase(rate_data):
    """Initialise le taux d'accessoires dans Firebase (première fois)"""
    try:
        db = init_firebase_admin()
        if db:
            # Vérifier si le taux existe déjà
            doc_ref = db.collection('config').document('accessories_rate')
            doc = doc_ref.get()
            if not doc.exists:
                # Ajouter timestamp d'initialisation
                rate_data['_initialized_at'] = firestore.SERVER_TIMESTAMP
                rate_data['_version'] = '1.0'
                doc_ref.set(rate_data)
                try:
                    log_change(
                        event_type='accessories_rate.init',
                        item_id='accessories_rate',
                        description='Initialisation du taux accessoires',
                        before=None,
                        after=rate_data,
                        metadata={'collection': 'config'}
                    )
                except Exception:
                    pass
                return True, "Accessories rate initialized successfully"
            else:
                return False, "Accessories rate already exists in database"
    except Exception as e:
        st.error(f"Erreur initialisation taux accessoires: {e}")
        return False, f"Error: {e}"


def initialize_labor_percentages_in_firebase(percentages_data):
    """Initialise les pourcentages de main d'œuvre dans Firebase (première fois)"""
    try:
        db = init_firebase_admin()
        if db:
            # Vérifier si les pourcentages existent déjà
            doc_ref = db.collection('config').document('labor_percentages')
            doc = doc_ref.get()
            if not doc.exists:
                # Ajouter timestamp d'initialisation
                percentages_data['_initialized_at'] = firestore.SERVER_TIMESTAMP
                percentages_data['_version'] = '1.0'
                doc_ref.set(percentages_data)
                try:
                    log_change(
                        event_type='labor_percentages.init',
                        item_id='labor_percentages',
                        description='Initialisation des pourcentages main d\'œuvre',
                        before=None,
                        after=percentages_data,
                        metadata={'collection': 'config'}
                    )
                except Exception:
                    pass
                return True, "Labor percentages initialized successfully"
            else:
                return False, "Labor percentages already exist in database"
    except Exception as e:
        st.error(f"Erreur initialisation pourcentages main d'œuvre: {e}")
        return False, f"Error: {e}"

# --- Utilitaires d'audit / historique des modifications ---

def _safe_json(value, max_len: int = 4000):
    """Convertit une valeur en JSON (ou str) et tronque si trop longue."""
    if value is None:
        return None
    try:
        s = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        try:
            s = str(value)
        except Exception:
            s = None
    if s is None:
        return None
    if len(s) > max_len:
        return s[:max_len] + "… (tronqué)"
    return s


def log_change(event_type: str, item_id: str | None = None, description: str | None = None,
               before=None, after=None, metadata: dict | None = None, user_email: str | None = None) -> bool:
    """Enregistre un évènement d'audit dans Firestore (collection 'change_logs')."""
    try:
        db = init_firebase_admin()
        if not db:
            return False
        doc = {
            'event_type': event_type,
            'item_id': item_id or 'global',
            'description': description or '',
            'before': _safe_json(before),
            'after': _safe_json(after),
            'metadata': metadata or {},
            'user_email': user_email or st.session_state.get('user_email'),
            'timestamp': firestore.SERVER_TIMESTAMP,
        }
        db.collection('change_logs').add(doc)
        return True
    except Exception as e:
        st.error(f"Erreur log_change: {e}")
        return False


def get_change_history(limit: int = 100, event_type: str | None = None, user_email: str | None = None):
    """Récupère l'historique des modifications, trié par date décroissante.
    Peut filtrer par type d'évènement et/ou email utilisateur.
    """
    try:
        db = init_firebase_admin()
        if not db:
            return []
        q = db.collection('change_logs')
        # Filtres optionnels
        if event_type:
            q = q.where('event_type', '==', event_type)
        if user_email:
            q = q.where('user_email', '==', user_email)
        # Tri par timestamp desc (fallback si index manquant)
        try:
            q = q.order_by('timestamp', direction=firestore.Query.DESCENDING)
            docs = q.limit(max(1, int(limit))).stream()
            return [{'id': d.id, **d.to_dict()} for d in docs]
        except Exception:
            docs = q.limit(max(1, int(limit))).stream()
            items = [{'id': d.id, **d.to_dict()} for d in docs]
            # Tri côté client si possible
            try:
                items.sort(key=lambda x: x.get('timestamp'), reverse=True)
            except Exception:
                pass
            return []
    except Exception as e:
        st.error(f"Erreur get_change_history: {e}")
        return []


# --- Fonctions de gestion de stock ---

def save_product_to_firebase(product_data):
    """Sauvegarde un produit dans Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            # Ajouter timestamp de création
            product_data['created_at'] = firestore.SERVER_TIMESTAMP
            product_data['updated_at'] = firestore.SERVER_TIMESTAMP
            
            doc_ref = db.collection('stock_products').add(product_data)
            new_id = None
            try:
                new_id = doc_ref[1].id
            except Exception:
                pass
            
            # Journaliser la création
            try:
                log_change(
                    event_type='stock.product.create',
                    item_id=new_id,
                    description=f'Création du produit: {product_data.get("nom", "Inconnu")}',
                    before=None,
                    after={**product_data, 'id': new_id} if isinstance(product_data, dict) else product_data,
                    metadata={'collection': 'stock_products'}
                )
            except Exception:
                pass
            return new_id
    except Exception as e:
        st.error(f"Erreur sauvegarde produit: {e}")
        return None

@st.cache_data(ttl=300)  # Cache pendant 5 minutes
def get_all_products_from_firebase():
    """Récupère tous les produits depuis Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            products = db.collection('stock_products').stream()
            return [{'id': doc.id, **doc.to_dict()} for doc in products]
    except Exception as e:
        st.error(f"Erreur récupération produits: {e}")
        return []

def update_product_in_firebase(product_id, product_data):
    """Met à jour un produit dans Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            doc_ref = db.collection('stock_products').document(product_id)
            
            # Récupérer l'état avant modification
            try:
                snap_before = doc_ref.get()
                before_doc = snap_before.to_dict() if snap_before.exists else None
            except Exception:
                before_doc = None
            
            # Ajouter timestamp de mise à jour
            product_data['updated_at'] = firestore.SERVER_TIMESTAMP
            doc_ref.update(product_data)
            
            # Journaliser la modification
            try:
                log_change(
                    event_type='stock.product.update',
                    item_id=product_id,
                    description=f'Mise à jour du produit: {product_data.get("nom", "Inconnu")}',
                    before=before_doc,
                    after=product_data,
                    metadata={'collection': 'stock_products'}
                )
            except Exception:
                pass
            return True
    except Exception as e:
        st.error(f"Erreur mise à jour produit: {e}")
        return False

def delete_product_from_firebase(product_id):
    """Supprime un produit de Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            doc_ref = db.collection('stock_products').document(product_id)
            
            # Récupérer les données avant suppression pour le log
            try:
                snap_before = doc_ref.get()
                before_doc = snap_before.to_dict() if snap_before.exists else None
            except Exception:
                before_doc = None
            
            # Supprimer le document
            doc_ref.delete()
            
            # Journaliser la suppression
            try:
                log_change(
                    event_type='stock.product.delete',
                    item_id=product_id,
                    description=f'Suppression du produit: {before_doc.get("nom", "Inconnu") if before_doc else "Inconnu"}',
                    before=before_doc,
                    after=None,
                    metadata={'collection': 'stock_products'}
                )
            except Exception:
                pass
            return True
    except Exception as e:
        st.error(f"Erreur suppression produit: {e}")
        return False

def save_client_to_firebase(client_data):
    """Sauvegarde un client dans Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            # Ajouter timestamp de création
            client_data['created_at'] = firestore.SERVER_TIMESTAMP
            client_data['updated_at'] = firestore.SERVER_TIMESTAMP
            
            doc_ref = db.collection('stock_clients').add(client_data)
            new_id = None
            try:
                new_id = doc_ref[1].id
            except Exception:
                pass
            
            # Journaliser la création
            try:
                log_change(
                    event_type='stock.client.create',
                    item_id=new_id,
                    description=f'Création du client: {client_data.get("nom", "Inconnu")}',
                    before=None,
                    after={**client_data, 'id': new_id} if isinstance(client_data, dict) else client_data,
                    metadata={'collection': 'stock_clients'}
                )
            except Exception:
                pass
            return new_id
    except Exception as e:
        st.error(f"Erreur sauvegarde client: {e}")
        return None

@st.cache_data(ttl=300)  # Cache pendant 5 minutes
def get_all_clients_from_firebase():
    """Récupère tous les clients depuis Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            clients = db.collection('stock_clients').stream()
            return [{'id': doc.id, **doc.to_dict()} for doc in clients]
    except Exception as e:
        st.error(f"Erreur récupération clients: {e}")
        return []

def save_invoice_to_firebase(invoice_data):
    """Sauvegarde une facture dans Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            # Ajouter timestamp de création
            invoice_data['created_at'] = firestore.SERVER_TIMESTAMP
            invoice_data['updated_at'] = firestore.SERVER_TIMESTAMP
            
            doc_ref = db.collection('stock_invoices').add(invoice_data)
            new_id = None
            try:
                new_id = doc_ref[1].id
            except Exception:
                pass
            
            # Journaliser la création
            try:
                log_change(
                    event_type='stock.invoice.create',
                    item_id=new_id,
                    description=f'Création de la facture: {invoice_data.get("numero", "Inconnu")}',
                    before=None,
                    after={**invoice_data, 'id': new_id} if isinstance(invoice_data, dict) else invoice_data,
                    metadata={'collection': 'stock_invoices'}
                )
            except Exception:
                pass
            return new_id
    except Exception as e:
        st.error(f"Erreur sauvegarde facture: {e}")
        return None

@st.cache_data(ttl=300)  # Cache pendant 5 minutes
def get_all_invoices_from_firebase():
    """Récupère toutes les factures depuis Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            invoices = db.collection('stock_invoices').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
            return [{'id': doc.id, **doc.to_dict()} for doc in invoices]
    except Exception as e:
        st.error(f"Erreur récupération factures: {e}")
        return []

def save_stock_movement_to_firebase(movement_data):
    """Sauvegarde un mouvement de stock dans Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            # Ajouter timestamp de création
            movement_data['created_at'] = firestore.SERVER_TIMESTAMP
            
            doc_ref = db.collection('stock_movements').add(movement_data)
            new_id = None
            try:
                new_id = doc_ref[1].id
            except Exception:
                pass
            
            # Journaliser le mouvement
            try:
                log_change(
                    event_type='stock.movement.create',
                    item_id=new_id,
                    description=f'Mouvement de stock: {movement_data.get("type", "Inconnu")} - {movement_data.get("produit_nom", "Inconnu")}',
                    before=None,
                    after={**movement_data, 'id': new_id} if isinstance(movement_data, dict) else movement_data,
                    metadata={'collection': 'stock_movements'}
                )
            except Exception:
                pass
            return new_id
    except Exception as e:
        st.error(f"Erreur sauvegarde mouvement: {e}")
        return None

@st.cache_data(ttl=300)  # Cache pendant 5 minutes
def get_stock_movements_from_firebase(limit=100):
    """Récupère les mouvements de stock depuis Firestore"""
    try:
        db = init_firebase_admin()
        if db:
            movements = db.collection('stock_movements').order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit).stream()
            return [{'id': doc.id, **doc.to_dict()} for doc in movements]
    except Exception as e:
        st.error(f"Erreur récupération mouvements: {e}")
        return []

def clear_stock_cache():
    """Vide le cache des données de stock pour forcer le rechargement"""
    get_all_products_from_firebase.clear()
    get_all_clients_from_firebase.clear()
    get_all_invoices_from_firebase.clear()
    get_stock_movements_from_firebase.clear()

def sync_sqlite_to_firebase():
    """Synchronise les données SQLite vers Firebase"""
    import sqlite3
    import pandas as pd
    from datetime import datetime
    
    try:
        # Connexion à la base SQLite
        conn = sqlite3.connect('energie_solaire.db')
        
        # Synchroniser les produits
        produits_df = pd.read_sql_query("SELECT * FROM produits", conn)
        for _, produit in produits_df.iterrows():
            product_data = {
                'nom': produit['nom'],
                'categorie': produit['categorie'],
                'prix_achat': float(produit['prix_achat']) if produit['prix_achat'] else 0,
                'prix_vente': float(produit['prix_vente']) if produit['prix_vente'] else 0,
                'stock_actuel': int(produit['stock_actuel']) if produit['stock_actuel'] else 0,
                'stock_min': int(produit['stock_min']) if produit['stock_min'] else 0,
                'unite': produit['unite'],
                'sqlite_id': int(produit['id'])
            }
            save_product_to_firebase(product_data)
        
        # Synchroniser les clients
        clients_df = pd.read_sql_query("SELECT * FROM clients", conn)
        for _, client in clients_df.iterrows():
            client_data = {
                'nom': client['nom'],
                'telephone': client['telephone'] or '',
                'adresse': client['adresse'] or '',
                'email': client['email'] or '',
                'sqlite_id': int(client['id'])
            }
            save_client_to_firebase(client_data)
        
        # Synchroniser les factures
        factures_df = pd.read_sql_query("SELECT * FROM factures", conn)
        for _, facture in factures_df.iterrows():
            invoice_data = {
                'numero': facture['numero'],
                'date': facture['date'],
                'client_id': int(facture['client_id']) if facture['client_id'] else None,
                'client_nom': facture['client_nom'],
                'montant_total': float(facture['montant_total']) if facture['montant_total'] else 0,
                'type': facture['type'],
                'statut': facture['statut'],
                'sqlite_id': int(facture['id'])
            }
            save_invoice_to_firebase(invoice_data)
        
        # Synchroniser les mouvements de stock
        mouvements_df = pd.read_sql_query("SELECT * FROM mouvements_stock", conn)
        for _, mouvement in mouvements_df.iterrows():
            movement_data = {
                'date': mouvement['date'],
                'produit_id': int(mouvement['produit_id']) if mouvement['produit_id'] else None,
                'produit_nom': mouvement['produit_nom'],
                'type': mouvement['type'],
                'quantite': int(mouvement['quantite']) if mouvement['quantite'] else 0,
                'reference': mouvement['reference'] or '',
                'sqlite_id': int(mouvement['id'])
            }
            save_stock_movement_to_firebase(movement_data)
        
        conn.close()
        clear_stock_cache()  # Vider le cache après synchronisation
        return True, "Synchronisation réussie"
        
    except Exception as e:
        return False, f"Erreur de synchronisation: {e}"
