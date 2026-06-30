// LinkTelegramPage.jsx
// Minimal React component to confirm link tokens. Place in your React app.
// Assumes the app already initialises Firebase client SDK elsewhere.
import React, { useEffect, useState } from "react";
import { getFirestore, doc, getDoc, updateDoc } from "firebase/firestore";

export default function LinkTelegramPage() {
  const [status, setStatus] = useState("checking");
  const params = new URLSearchParams(window.location.search);
  const token = params.get("t");
  const db = getFirestore();

  useEffect(() => {
    if (!token) {
      setStatus("invalid");
      return;
    }
    (async () => {
      const docRef = doc(db, "telegramLinks", token);
      const snap = await getDoc(docRef);
      if (!snap.exists()) {
        setStatus("not_found");
        return;
      }
      const data = snap.data();
      if (data.status !== "pending") {
        setStatus("already");
        return;
      }
      // show confirmation UI with user email/name from the currently logged in app user
      // assume you have auth.currentUser
      const user = window?.currentUser; // adapt to your app's auth
      if (!user) {
        setStatus("need_login");
        return;
      }
      const confirm = window.confirm(`Vincular a conta ${user.email} ao Telegram?`);
      if (!confirm) {
        setStatus("cancelled");
        return;
      }
      // update token doc to confirmed + uid
      await updateDoc(docRef, {
        status: "confirmed",
        uid: user.uid,
        confirmed_at: new Date().toISOString()
      });
      setStatus("confirmed");
    })();
  }, [token]);

  return (
    <div style={{ padding: 20 }}>
      {status === "checking" && <p>A verificar...</p>}
      {status === "invalid" && <p>Token inválido.</p>}
      {status === "not_found" && <p>Token não encontrado ou expirado.</p>}
      {status === "need_login" && <p>Por favor inicia sessão no app para confirmar a ligação.</p>}
      {status === "confirmed" && <p>✅ Conta vinculada! Podes fechar esta página.</p>}
    </div>
  );
}
