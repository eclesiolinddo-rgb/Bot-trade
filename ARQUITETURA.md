# Cless Cripto Bot — Arquitetura

## Stack
- Python 3.11 + python-telegram-bot v21 (async, suporta APScheduler nativo)
- Firebase Admin SDK (mesmo Firestore do app — fonte única de verdade)
- APScheduler (jobs agendados: rankings diário/semanal/mensal)
- Railway (deploy, mesmo ambiente dos outros bots)

## Coleções Firestore usadas (já existem no app, zero migração)
- users/{uid}                → vol, referralEarnings, referralCount, tier
- leaderboard/{uid}           → ranking de traders
- tradeFeed/{tradeId}         → feed de trades (fonte para sinais "quentes")
- (NOVA) telegramLinks/{uid}  → vincula uid do app ↔ telegram_chat_id
- (NOVA) referralApprovals/{} → fila de bónus pendentes de aprovação
- (NOVA) botSignals/{}        → histórico de sinais publicados

## Fluxo 1 — Vincular conta (link mágico, sem password, sem tocar no app existente)
/start → bot gera token único (UUID), guarda em telegramLinks/{token}
         {status:"pending", chat_id, created_at, expires_at: +10min}
       → bot envia: "Clica para confirmar: clesscripto.app/link?t=XYZ"
       → user abre no telemóvel (app já tem a sessão ativa, login persiste)
       → rota nova /link?t=XYZ no app:
           1. Lê o token da URL
           2. Mostra "Vincular esta conta ao Telegram?" com email/nome
              do user já logado, 1 botão "Confirmar"
           3. Ao confirmar: Firestore update telegramLinks/{token}
              {status:"confirmed", uid: authUser.uid}
       → bot tem listener (onSnapshot) nesse documento → deteta confirmação
         em tempo real → grava telegramLinks/{uid} definitivo → apaga o
         token temporário → manda "✅ Conta vinculada!" no Telegram

### Implementação no app — ISOLADA, sem risco para o resto
- Novo componente standalone `LinkTelegramPage.jsx`-style, dentro do mesmo
  index.html (mantém a arquitetura monolítica que preferes)
- Detectado por query param (?t=), renderizado ANTES do App principal
  carregar — não entra em tabs, não usa Header, não toca em nenhum state
  partilhado (port, stnBal, etc). É uma página solta.
- Zero interação com placeOrder, ErrorBoundary, ou qualquer lógica de
  trading. Risco de regressão: praticamente nulo.
- Token expira em 10min e é uso único — mesmo que alguém intercete o link,
  só funciona se a vítima clicar E já estiver logada na própria conta dela.

## Fluxo 2 — Rankings automáticos (zero esforço, 100% agendado)
APScheduler:
  - Diário   23:55 → top 5 do dia (tradeFeed filtrado por hoje)
  - Semanal  Domingo 20:00 → top 10 da semana (leaderboard)
  - Mensal   Dia 1, 09:00 → top 10 do mês + reset opcional
Publica automaticamente no canal público. Sem intervenção tua.

## Fluxo 3 — Sinais de compra/venda (híbrido, conforme combinámos)
Reutiliza a lógica dos teus bots Python existentes (RSI/EMA/MACD/Bollinger)
como módulo separado `signals_engine.py`:
  1. Engine deteta sinal → guarda em botSignals (status: pending)
  2. Bot envia-te DM: "🟢 Sinal BTC detectado [Aprovar] [Rejeitar]"
  3. Clicas Aprovar → bot publica no canal automaticamente formatado
  4. Clicas Rejeitar → descartado, log guardado (para depois afinares o engine)
Um clique teu por sinal. Zero digitação manual.

## Fluxo 4 — Aprovar bónus referral (admin only)
Job verifica users com referralEarnings pendentes (campo já existe no app)
  → DM para admin(s): lista de pendentes com botões Aprovar/Rejeitar
  → Aprovar → Firestore Admin SDK escreve direto (bypassa Firestore Rules,
    porque Admin SDK corre com privilégios de servidor — comportamento
    correto e seguro, mesmo conceito do teu AdminTab no app)

## Comandos do bot
/start          → vincular conta
/ranking        → ranking atual on-demand (DM)
/meubonus       → ver status dos teus referrals
/sinais on|off  → opt-in/opt-out de receber sinais em DM (canal sempre recebe)
/admin          → painel admin (só se chat_id está na lista de admins)

## Estrutura de ficheiros
cless-bot/
├── bot.py              → entrypoint, handlers dos comandos
├── firestore_client.py → wrapper fino sobre Admin SDK
├── scheduler.py        → jobs diário/semanal/mensal
├── signals_engine.py   → lógica técnica (adaptada dos teus bots existentes)
├── admin_flows.py      → aprovação de bónus e sinais
├── formatters.py       → templates de mensagem (ranking, sinal, etc)
├── .env.example
└── requirements.txt

## Firestore Rules — nova coleção telegramLinks
Adicionar ao firestore.rules existente (não mexe nas outras regras):

match /telegramLinks/{tokenOrUid} {
  // Bot (Admin SDK) sempre pode ler/escrever — Admin SDK ignora Rules,
  // mas declaramos explícito para clareza e para o caso de algum dia
  // trocares para um service account com permissões mais restritas
  allow read: if request.auth != null
              && (resource.data.uid == request.auth.uid || isAdmin());
  // User só pode CONFIRMAR um token (mudar status pending → confirmed
  // e carimbar o próprio uid) — nunca pode criar nem ler tokens alheios
  allow update: if request.auth != null
                && resource.data.status == "pending"
                && request.resource.data.status == "confirmed"
                && request.resource.data.uid == request.auth.uid
                && request.resource.data.diff(resource.data)
                     .affectedKeys().hasOnly(["status","uid","confirmed_at"]);
  allow create, delete: if false; // só o bot (Admin SDK) cria/apaga
}

Nota de segurança: o "allow read" exige resource.data.uid == request.auth.uid,
mas no momento da leitura inicial (antes de confirmar) o documento ainda
não tem uid populado (só tem chat_id, status:pending). Por isso a página
/link no app vai ler o token de forma pública controlada — ajustamos a
regra de read para permitir leitura de documentos pending sem dono ainda:

allow read: if request.auth != null
            && (resource.data.status == "pending" || resource.data.uid == request.auth.uid || isAdmin());

## Ordem de entrega sugerida (testável a cada etapa)
1. Esqueleto + vínculo de conta (link mágico) — testas que /start funciona
   e que a tua própria conta vincula corretamente
2. /ranking on-demand + scheduler diário/semanal/mensal — testas que os
   números batem com o que vês no app
3. Aprovação de bónus referral — testas com um caso real pendente
4. Sinais técnicos públicos (reaproveitando engine dos teus bots
   existentes) — DM com aprovar/rejeitar, publica no canal
5. Autotrade assistido — só depois das 4 etapas anteriores estarem
   estáveis em produção, porque reaproveita o engine da etapa 4 e o
   padrão de confirmação por DM, mas mexe em dinheiro real de terceiros.
   Esta etapa testa-se primeiro contigo mesmo como único user, com um
   valor pequeno alocado, antes de oferecer a mais ninguém.

---

# FEATURE: Trading Autónomo Assistido (confirmação na entrada)

## Modelo escolhido
Bot decide (entry, size, SL/TP) → envia DM com proposta → user confirma
com 1 clique → bot executa via Firestore Admin SDK → depois de entrar,
SL/TP corre sozinho (reaproveitando o engine que já existe no app) →
zero confirmação extra até a posição fechar.

## Como o bot "executa" sem API de exchange
Confirmado lendo fbPlaceOrder no index.html: o Cless Cripto NÃO liga a
uma exchange real — "executar uma ordem" é escrever diretamente no
Firestore (stnBal, port, transactions). O bot replica exatamente esse
mesmo padrão via Firebase Admin SDK, escrevendo nos mesmos documentos
que o app escreve. Não precisa de nenhuma API nova — é a mesma fonte
de dados, só que escrita a partir do Python em vez do React.

## Ativação pelo user (opt-in explícito, nunca automático por defeito)
/autotrade → bot explica o modelo (decide entrada, confirmas, depois
             gere sozinho) e mostra um aviso de risco obrigatório
           → user define o limite de capital alocado ao bot
             (ex: "500 STN") — este saldo fica reservado, separado
             do saldo de trading manual do user
           → user aceita termos (1 botão "Concordo e Ativo")
           → autoTradeSettings/{uid} = {
               active: true, allocatedSTN: 500, maxPositionPct: X,
               activated_at, status:"awaiting_signal"
             }
/autotrade off → desativa imediatamente, fecha posições abertas do bot
                 (não as manuais do user) ao preço de mercado, devolve
                 saldo ao stnBal principal

## Limite rígido do BOT (camada extra acima do que o user escolhe)
Combinámos: user define até quanto aloca. Mas o bot impõe a sua própria
disciplina por cima disso — nunca arrisca tudo de uma vez, mesmo que o
user tenha alocado um valor alto:
  - Máx 1 posição aberta de cada vez (sem overlap, reduz exposição)
  - Máx 15% do allocatedSTN por trade individual (position sizing,
    não "tudo ou nada" — é o oposto do erro de stop-loss que descreveste
    como a tua maior lição de trader)
  - SL obrigatório em TODO trade do bot — nunca entra sem stop definido
  - Se 3 trades seguidos fecharem em prejuízo → bot pausa-se sozinho e
    avisa o user, espera confirmação manual para retomar (circuit breaker)

## Fluxo de proposta de trade
1. signals_engine.py deteta oportunidade (mesmo engine dos sinais públicos,
   mas agora aplicado a cada user com autotrade ativo)
2. Bot calcula: ativo, direção, tamanho (respeitando os 15%), SL, TP
3. DM ao user:
   "🤖 Proposta de Trade — BTC
    Entrada: ~52.000€ | Tamanho: 75 STN (15% do teu limite)
    Stop-Loss: 51.200€ (-1.5%) | Take-Profit: 53.600€ (+3%)
    Risco/Retorno: 1:2
    [✅ Aprovar]  [❌ Recusar]  [⏸ Pausar autotrade]"
4. Aprovar → escreve no Firestore via Admin SDK, exatamente como
   fbPlaceOrder faria, mas com origin:"autotrade_bot" na transação
   (para distinguir no histórico do que foi clicado manualmente no app)
5. Recusar → log guardado, bot tenta próxima oportunidade depois
6. SL/TP depois disto: reaproveita o mesmo engine useEffect que já
   existe no App() do index.html (linha ~7726 da versão atual),
   replicado em Python rodando como job contínuo no bot — verifica
   preços e fecha automaticamente sem nova confirmação

## Nova coleção Firestore
autoTradeSettings/{uid}  → configuração e estado do autotrade do user
autoTradePositions/{id}  → posições abertas especificamente pelo bot
                            (separado de port[], para nunca confundir
                            com posições manuais do user no app)

## Firestore Rules — autoTradeSettings e autoTradePositions
match /autoTradeSettings/{uid} {
  allow read: if isOwner(uid) || isAdmin();
  allow create, update: if isOwner(uid)
                        && request.resource.data.allocatedSTN >= 0
                        && request.resource.data.allocatedSTN <= resource.data.stnBal;
  // Bot (Admin SDK) sempre pode escrever, ignora Rules — mas o user
  // só pode mexer no PRÓPRIO documento, nunca no de outro user
  allow delete: if false;
}
match /autoTradePositions/{posId} {
  allow read: if request.auth != null
              && (resource.data.uid == request.auth.uid || isAdmin());
  allow create, update, delete: if false; // só o bot (Admin SDK) escreve
}

## Aviso de risco — texto obrigatório antes de ativar (compliance básico)
"⚠️ O autotrade é uma ferramenta automatizada que executa trades em teu
nome dentro do limite que definires. Resultados passados não garantem
resultados futuros. Podes perder parte ou todo o capital alocado.
A Cless Cripto não garante lucro. Podes desativar a qualquer momento
com /autotrade off."
Guardado em autoTradeSettings com timestamp de aceitação — equivalente
ao consentimento que já pedes no KYC do app.

## Isolamento de saldo — evitar conflito entre trading manual e autotrade
PROBLEMA: se autoTradeSettings.allocatedSTN vivesse "dentro" do stnBal
principal, uma compra manual no app ao mesmo tempo que o bot executa
um trade automático criaria race condition (dois writes simultâneos
no mesmo campo, um pode sobrescrever o outro — mesma classe de bug
que já vimos no app entre onSnapshot e setState locais).

SOLUÇÃO: saldo do autotrade é fisicamente separado do stnBal de trading
manual, nunca o mesmo campo:
  - users/{uid}.stnBal           → saldo de trading manual (já existe)
  - autoTradeSettings/{uid}.allocatedSTN → saldo dedicado ao bot
Ativar autotrade FAZ uma transferência única (Firestore transaction,
atómica) de stnBal → allocatedSTN no momento da ativação. Depois disso,
os dois saldos vivem em campos diferentes, escritos por processos
diferentes, sem nunca colidirem. Desativar faz o caminho inverso.
Isto também resolve visualmente: o user vê no app o stnBal dele (sem o
que está alocado ao bot), e vê no Telegram o saldo do autotrade — claro,
sem confusão sobre "quanto tenho disponível para mexer eu mesmo".
