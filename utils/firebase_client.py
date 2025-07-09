# utils/firebase_client.py
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Optional, Dict, Any
from config import settings
import os
from loguru import logger


class FirebaseClient:
    def __init__(self):
        self.db: Optional[firestore.Client] = None
        self.init_firebase()

    def init_firebase(self):
        """Initialize Firebase with service account file"""
        if not firebase_admin._apps:
            try:
                cred = self._get_credentials()
                if cred:
                    firebase_admin.initialize_app(cred)
                    self.db = firestore.client()
                    logger.info("Firebase initialized successfully")
                else:
                    logger.warning("Firebase credentials not found - Firebase features disabled")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase: {e}")

    def _get_credentials(self):
        """Get Firebase credentials from service account file"""
        if settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
            logger.info(f"Using Firebase credentials from file: {settings.FIREBASE_CREDENTIALS_PATH}")
            return credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)

        return None

    def is_connected(self) -> bool:
        """Check if Firebase is connected"""
        return self.db is not None

    def send_real_time_update(self, tenant_id: str, collection: str, doc_id: str, data: Dict[str, Any]):
        """Send real-time updates to Firebase"""
        if not self.db:
            logger.warning("Firebase not initialized - skipping real-time update")
            return

        try:
            doc_ref = self.db.collection(f"tenants/{tenant_id}/{collection}").document(doc_id)
            doc_ref.set(data, merge=True)
            logger.debug(f"Sent real-time update to Firebase: {tenant_id}/{collection}/{doc_id}")
        except Exception as e:
            logger.error(f"Failed to send real-time update to Firebase: {e}")

    def send_notification(self, tenant_id: str, notification_type: str, data: Dict[str, Any]):
        """Send notifications to Firebase"""
        if not self.db:
            logger.warning("Firebase not initialized - skipping notification")
            return

        try:
            doc_ref = self.db.collection(f"tenants/{tenant_id}/notifications").document()
            doc_ref.set({
                "type": notification_type,
                "data": data,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "read": False
            })
            logger.debug(f"Sent notification to Firebase: {tenant_id}/{notification_type}")
        except Exception as e:
            logger.error(f"Failed to send notification to Firebase: {e}")

    # def get_tenant_data(self, tenant_id: str, collection: str, limit: int = 50) -> List[Dict[str, Any]]:
    #     """Get tenant data from Firebase"""
    #     if not self.db:
    #         logger.warning("Firebase not initialized - cannot get tenant data")
    #         return []
    #
    #     try:
    #         docs = self.db.collection(f"tenants/{tenant_id}/{collection}").limit(limit).stream()
    #         return [doc.to_dict() for doc in docs]
    #     except Exception as e:
    #         logger.error(f"Failed to get tenant data from Firebase: {e}")
    #         return []
    #
    # def delete_tenant_data(self, tenant_id: str, collection: str, doc_id: str):
    #     """Delete tenant data from Firebase"""
    #     if not self.db:
    #         logger.warning("Firebase not initialized - cannot delete tenant data")
    #         return
    #
    #     try:
    #         doc_ref = self.db.collection(f"tenants/{tenant_id}/{collection}").document(doc_id)
    #         doc_ref.delete()
    #         logger.debug(f"Deleted data from Firebase: {tenant_id}/{collection}/{doc_id}")
    #     except Exception as e:
    #         logger.error(f"Failed to delete data from Firebase: {e}")


firebase_client = FirebaseClient()