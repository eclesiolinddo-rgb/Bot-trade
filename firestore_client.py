import os
import json
import logging
from typing import Optional, Dict, Any, List

import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)

class FirestoreClient:
    def __init__(self):
        # Prefer GOOGLE_APPLICATION_CREDENTIALS pointing to a JSON file path,
        # or FIREBASE_SERVICE_ACCOUNT_JSON containing the full JSON.
        sa_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if sa_path and os.path.exists(sa_path):
            cred = credentials.Certificate(sa_path)
        elif sa_json:
            # write to temp file
            data = json.loads(sa_json)
            cred = credentials.Certificate(data)
        else:
            raise RuntimeError("Firebase service account not provided. Set GOOGLE_APPLICATION_CREDENTIALS or FIREBASE_SERVICE_ACCOUNT_JSON")

        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()

    async def set_doc(self, collection: str, doc_id: str, data: Dict[str, Any]):
        # Firestore python API is blocking; running in thread pool is recommended.
        self.db.collection(collection).document(doc_id).set(data)

    async def get_doc(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        doc = self.db.collection(collection).document(doc_id).get()
        if not doc.exists:
            return None
        return doc.to_dict()

    async def delete_doc(self, collection: str, doc_id: str):
        self.db.collection(collection).document(doc_id).delete()

    async def query_docs(self, collection: str, field: str, op: str, value, limit: int = 50):
        q = self.db.collection(collection).where(field, op, value).limit(limit)
        return [d.to_dict() for d in q.stream()]

    async def get_uid_by_chat(self, chat_id: int):
        # canonical mapping is telegramLinks/{uid} with status confirmed
        col = self.db.collection("telegramLinks")
        q = col.where("chat_id", "==", chat_id).where("status", "==", "confirmed").limit(1).stream()
        for doc in q:
            return doc.to_dict().get("uid")
        return None

    async def get_top_leaderboard(self, limit=10):
        col = self.db.collection("leaderboard")
        q = col.order_by("score", direction=firestore.Query.DESCENDING).limit(limit).stream()
        return [d.to_dict() for d in q]

    async def update_doc(self, collection: str, doc_id: str, patch: Dict[str, Any]):
        self.db.collection(collection).document(doc_id).update(patch)

    # Add transaction helpers for stnBal transfer, place order, etc.
    def run_transaction(self, func):
        return self.db.transaction()(func)
