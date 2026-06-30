"""Thin wrapper around Firebase Admin SDK for the bot.

Provides async-friendly helper functions used by the bot.
This module requires the environment to be configured for the
Firebase Admin SDK (GOOGLE_APPLICATION_CREDENTIALS or equivalent).
"""
import os
import time
import asyncio
from datetime import datetime, timezone
from typing import Optional, List

import firebase_admin
from firebase_admin import credentials, firestore


class FirestoreClient:
    def __init__(self):
        # Initialize the Admin SDK once
        if not firebase_admin._apps:
            cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if cred_path:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            else:
                # default app credentials
                firebase_admin.initialize_app()
        self.db = firestore.client()

    async def create_link_token(self, token: str, chat_id: int, created_at: datetime, expires_at: datetime):
        doc_ref = self.db.collection("telegramLinks").document(token)
        doc_ref.set({
            "status": "pending",
            "chat_id": chat_id,
            "created_at": created_at,
            "expires_at": expires_at,
        })

    async def wait_for_token_confirmation(self, token: str, timeout: int = 600) -> Optional[str]:
        """Poll the token document until status becomes 'confirmed' or timeout.
        Returns the confirmed uid if available, otherwise None.
        """
        doc_ref = self.db.collection("telegramLinks").document(token)
        deadline = time.time() + timeout
        while time.time() < deadline:
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                if data.get("status") == "confirmed" and data.get("uid"):
                    # Optionally delete the temp token document and write mapping under uid
                    uid = data.get("uid")
                    # write canonical mapping telegramLinks/{uid} = {chat_id, uid}
                    canonical_ref = self.db.collection("telegramLinks").document(uid)
                    canonical_ref.set({
                        "uid": uid,
                        "chat_id": data.get("chat_id"),
                        "linked_at": datetime.now(timezone.utc),
                    })
                    try:
                        doc_ref.delete()
                    except Exception:
                        pass
                    return uid
            await asyncio.sleep(2)
        return None

    async def get_top_leaderboard(self, limit: int = 10) -> List[dict]:
        coll = self.db.collection("leaderboard")
        q = coll.order_by("score", direction=firestore.Query.DESCENDING).limit(limit)
        docs = q.stream()
        results = []
        for d in docs:
            data = d.to_dict()
            results.append({"uid": d.id, "score": data.get("score", 0), "displayName": data.get("displayName")})
        return results


# Additional helper methods (placeholders)
