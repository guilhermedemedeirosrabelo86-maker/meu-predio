# Meu Prédio — instruções para o Claude

Este arquivo é lido no começo de toda sessão. Ele é o **registro oficial do projeto**:
o que é, em que pé está, o que foi decidido e o que vem a seguir.

## Regra obrigatória: manter este registro em dia

Toda sessão que mudar algo no projeto **deve atualizar este arquivo antes de terminar**
(e de preferência no mesmo commit da mudança):

1. Atualize **"Estado atual"** e **"Próximos passos"** para refletirem a realidade.
2. Acrescente uma linha no **"Diário"** (no topo da lista, a mais nova primeiro):
   `AAAA-MM-DD — o que foi feito (commit abc1234) — o que ficou pendente`.
3. Se descobrir uma armadilha nova (algo que quebrou e custou tempo), registre em **"Armadilhas"**.
4. Se o usuário tomar uma decisão de produto ou visual, registre em **"Decisões"**.

Não apague o histórico do Diário; só acrescente. Repasse esta regra adiante: ela vale para toda sessão.

## Quem é o usuário

Guilherme. Fala português do Brasil, escreve curto e informal; responda em PT-BR, em linguagem simples
(está aprendendo programação). Testa no iPhone (Safari). Pede commit explicitamente ("faça commit");
não faça commit nem push sem ele pedir. Gosta de ver prints/opções antes de aprovar mudanças visuais.
Quer vender o app para condomínios.

## O que é

PWA para condomínios pequenos: avisos, reservas, ocorrências com fotos, visitantes por QR Code,
portaria, encomendas, enquetes, telefones úteis, prestação de contas e taxa condominial.
Perfis: síndico, morador e portaria. Detalhes de cada módulo no README.

- **Backend:** Python 3.11 puro, sem bibliotecas externas (`backend/`). Roteador próprio em `backend/web.py`.
- **Frontend:** JavaScript puro em módulos (`web/js/`), sem framework e sem build. CSS único em `web/css/app.css`.
- **Banco:** SQLite local (`dados/condominio.db`) ou Turso na nuvem (`backend/db_remoto.py`, API HTTP).
- **Testes:** `python -m unittest discover -s tests` (e com `MEU_PREDIO_TESTE_TURSO=1` para o modo Turso).
- **Rodar local:** `iniciar.bat` (computador) ou `iniciar-celular.bat` (celular no mesmo Wi-Fi).

## Estado atual (atualize sempre)

- **No ar:** https://meu-predio.vercel.app — Vercel (time "GR Digital", plano Hobby grátis),
  deploy automático a cada push na branch `main` do GitHub
  (github.com/guilhermedemedeirosrabelo86-maker/meu-predio).
- **Banco em produção:** Turso, plano grátis, região AWS us-east-1 (perto da Vercel, que roda em Washington).
- **Variáveis na Vercel:** `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`, `CRON_SECRET`, `APP_URL` configuradas.
  **Falta** `RESEND_API_KEY` e `EMAIL_REMETENTE` (sem elas o "esqueci minha senha" não envia e-mail).
- **Visual:** "Claro" (ver Decisões).
- **Segurança/LGPD prontos:** limite de tentativas, PBKDF2 600 mil, esqueci minha senha, histórico do síndico,
  aceite dos termos, baixar meus dados, excluir conta, limpeza diária (cron da Vercel às 06:00 UTC).
- **Termos e privacidade são rascunho:** faltam os dados da empresa (entre `[colchetes]`
  no início de `web/js/telas/legal.js`) e revisão de um advogado antes de vender.
- **Dados locais x produção:** o banco do computador não foi copiado para a produção; a produção começou vazia.

## Próximos passos (atualize sempre)

1. Configurar o Resend (e-mail de "esqueci minha senha") — o usuário precisa criar a conta.
2. Síndico enviar a foto do próprio prédio para o topo do Início (ideia aprovada para "depois").
3. Esconder "Abrir no celular" do Perfil na versão hospedada (só faz sentido na rede local).
4. Antes de cobrar: migrar o banco para Postgres (Neon ou Supabase, região São Paulo) e as fotos para
   um armazenamento de arquivos (Vercel Blob ou Supabase Storage).
5. Do README: fechamento do mês + balancete em PDF, Web Push, alertas automáticos, planos (limites do plano grátis).

## Decisões

- **Hospedagem:** Vercel + Turso (grátis) para o piloto. Firebase foi considerado e descartado
  (exigiria reescrever o backend e cartão de crédito). Postgres só antes de começar a cobrar.
- **E-mail:** Resend, via API HTTP com urllib (`backend/correio.py`).
- **Visual "Claro" (2026-10-26):** app sempre branco (sem modo escuro), fundo `#f6f7fb`, azul `#2f6fed`,
  fonte Poppins servida pelo próprio app (`web/fonts/`), cantos arredondados, sombras suaves,
  barra de baixo branca flutuante, foto de condomínio (`web/img/condominio.jpg`, Unsplash) no topo
  do Início (barra do topo transparente sobre ela) e nas telas de login/cadastro, atalhos em ícones
  redondos azul-claro. Substituiu o visual "Interfone" (concreto/grafite/amarelo), a pedido do usuário,
  com base numa referência de app imobiliário.
- **Histórico do síndico:** só o síndico vê; ninguém apaga pelo app.

## Armadilhas (leia antes de mexer)

- **Safari do iPhone:** a navegação usa `history.pushState` (`irPara` em `web/js/estado.js`).
  Nunca mude `location.hash` direto: o Safari recarrega a página inteira.
- **CSP sem inline:** o servidor e o `vercel.json` proíbem script e estilo inline e recursos de outros sites.
  Scripts, fontes e imagens precisam ser arquivos em `web/`.
- **Rollback em erro:** quando uma rota lança `ErroHTTP`, o servidor desfaz tudo o que ela gravou.
  O que precisa ficar gravado mesmo com erro (ex.: tentativa de login errada) precisa de `conn.commit()`
  antes do erro — ver `backend/limites.py`.
- **Service worker:** ao adicionar ou remover arquivos em `web/`, atualize a lista `ARQUIVOS` e suba a
  versão `CACHE` em `web/sw.js`. Um arquivo da lista que não exista quebra o modo offline inteiro.
- **Fim de linha:** `sed -i` no Git Bash converte CRLF em LF e faz arquivos não tocados aparecerem como
  modificados. Confira `git status` e restaure com `git checkout -- arquivo` se o conteúdo não mudou.
- **Portas locais:** já houve outros programas ouvindo na porta 8765/8766 do computador; use `127.0.0.1`
  explícito nos testes com curl.
- **Prints para conferir telas:** Edge headless via CDP (script em Python com `websocket-client`).
  A extensão do Chrome não costuma estar conectada.
- **Testes:** `tests/base.py` baixa `auth.ITERACOES` para os testes ficarem rápidos; o cadastro exige
  `"aceito_termos": true`.

## Diário (mais novo primeiro; só acrescente)

- 2026-10-26 — Criado este CLAUDE.md como registro oficial, a pedido do usuário. Pendente: commit dele.
- 2026-10-26 — Visual "Claro" com foto do condomínio no topo, Poppins, barra flutuante, ícone azul
  (commit 909f85e). Publicado na Vercel.
- 2026-10-26 — Migração para Vercel + Turso, limite de tentativas, senhas mais fortes, esqueci minha
  senha, histórico do síndico, LGPD (commit feb3d36). App no ar em meu-predio.vercel.app.
- 2026-10-21 — Visual "Interfone", encomendas, telefones úteis e enquetes (commit be2ebbd).
- 2026-10-02 — MVP fechado: Início com todos os módulos e navegação por perfil (commit 2333ccf).
