# Cless Cripto Bot

Conteúdo:
- bot.py — Telegram bot (start, ranking, sinais, autotrade)
- firestore_client.py — wrapper do Admin SDK
- scheduler.py — APScheduler jobs
- signals_engine.py — engine scaffold
- admin_flows.py — admin interactions
- LinkTelegramPage.jsx — página para confirmar token no app
- firestore.rules — snippets a aplicar no teu rules file

Pré-requisitos
- Conta Firebase com Service Account (JSON)
- Bot Telegram (BotFather) token
- Canal Telegram (CHANNEL_CHAT_ID) e lista de ADMIN_CHAT_IDS

Variáveis de ambiente (Railway secrets)
- TELEGRAM_BOT_TOKEN (obrigatório)
- FIREBASE_SERVICE_ACCOUNT_JSON (o conteúdo JSON inteiro) OR GOOGLE_APPLICATION_CREDENTIALS (caminho para ficheiro JSON)
- CHANNEL_CHAT_ID
- ADMIN_CHAT_IDS (comma separated)
- MAGIC_LINK_DOMAIN (ex: https://clesscripto.app)
- MAX_POSITION_PCT (default 15)
- TOKEN_TTL_MIN (default 10)
- TIMEZONE (default Europe/Lisbon)

Deploy no Railway (resumo)
1. Cria projecto no Railway e liga o repo/cless-bot (ou faz upload manual).
2. Adiciona os secrets:
   - FIREBASE_SERVICE_ACCOUNT_JSON = (conteúdo do ficheiro JSON)
   - TELEGRAM_BOT_TOKEN
   - CHANNEL_CHAT_ID
   - ADMIN_CHAT_IDS
3. Procfile já presente; Railway detecta process `worker` e executa o bot.
4. Deploy e logs: verifica logs no Railway; o bot usa polling por padrão.

Se preferires que eu crie o branch e abra PR
