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
- **Visual:** "Claro" (ver Decisões). Início no computador no layout "B" (ver Decisões).
- **Contadores em tempo real** nas abas (barra de baixo e menu lateral): `GET /api/condominios/{cid}/contadores`,
  consultado a cada 10 s com o app na tela (60 s em segundo plano), ao voltar para o app e logo após qualquer
  ação (`dados-mudaram`). Quando um número muda, a tela aberta busca os dados de novo (`revalidar`).
  No "Mais" do celular aparece a soma das abas que só existem lá.
- **Segurança/LGPD prontos:** limite de tentativas, PBKDF2 600 mil, esqueci minha senha, histórico do síndico,
  aceite dos termos, baixar meus dados, excluir conta, limpeza diária (cron da Vercel às 06:00 UTC).
- **Termos e privacidade são rascunho:** e-mail de contato preenchido; faltam nome, CPF/CNPJ e cidade (entre `[colchetes]`
  no início de `web/js/telas/legal.js`) e revisão de um advogado antes de vender.
- **Backup:** `backup.bat` / `python backup.py` copia o Turso para `dados/backups/`; `python backup.py restaurar`
  só aceita banco vazio. Primeiro backup real feito em 2026-10-26 (50 linhas, 27 tabelas; abriu com o código do
  app: 3 contas, 2 condomínios). Credenciais locais em `dados/turso.json` (fora do Git). Rodar toda semana.
- **Revisão de segurança (2026-10-26):** todas as rotas conferidas — isolamento por condomínio, papel exigido
  e posse dos itens (veículo, reserva, visita etc.). Corrigido: `/api/rede` sem endereços na Vercel, limite de
  cadastro por endereço, "Trocar senha" no Perfil. Sem `innerHTML` no frontend.
- **Dados locais x produção:** o banco do computador não foi copiado para a produção; a produção começou vazia.

## Próximos passos (atualize sempre)

1. Configurar o Resend (e-mail de "esqueci minha senha") — o usuário precisa criar a conta e, para enviar a
   qualquer pessoa, um domínio próprio (ex.: registro.br) com os registros DNS do Resend. Explicado em 2026-10-26.
2. Esconder "Abrir no celular" do Perfil na versão hospedada (só faz sentido na rede local).
3. Antes de cobrar: migrar o banco para Postgres (Neon ou Supabase, região São Paulo) e as fotos para
   um armazenamento de arquivos (Vercel Blob ou Supabase Storage).
4. Do README: fechamento do mês + balancete em PDF, Web Push, alertas automáticos, planos (limites do plano grátis).

## Decisões

- **Hospedagem:** Vercel + Turso (grátis) para o piloto. Firebase foi considerado e descartado
  (exigiria reescrever o backend e cartão de crédito). Postgres só antes de começar a cobrar.
- **E-mail:** Resend, via API HTTP com urllib (`backend/correio.py`).
- **Visual "Claro" (2026-10-26):** app sempre branco (sem modo escuro), fundo `#f6f7fb`, azul `#2f6fed`,
  fonte Poppins servida pelo próprio app (`web/fonts/`), cantos arredondados, sombras suaves,
  barra de baixo branca flutuante, foto de condomínio (`web/img/condominio-{manha,tarde,noite}.jpg`, Unsplash) no topo
  do Início (barra do topo transparente sobre ela) e nas telas de login/cadastro, atalhos em ícones
  redondos azul-claro. Substituiu o visual "Interfone" (concreto/grafite/amarelo), a pedido do usuário,
  com base numa referência de app imobiliário.
- **Foto do topo pela hora do celular (2026-10-26):** manhã 5h–12h (render ao amanhecer + brilho alaranjado),
  tarde 12h–18h (a foto original), noite 18h–5h (residência moderna de alto padrão à noite, céu azul-noite e
  luzes quentes). O usuário quer noite de verdade (imersão) e arquitetura moderna e bonita: recusou foto de
  entardecer escurecida e um prédio antigo de tijolo.
  Classe `periodo-*` no `<html>` (`aplicarPeriodo` em ui.js, conferida a cada minuto); a saudação segue os
  mesmos horários. Manhã, tarde e noite: Aalo Lens (Unsplash; a da noite é a QHyUx3OcCns, torres ao anoitecer
  com janelas acesas). A noite antes era uma casa (Pexels 31737860); trocada em 2026-10-26 porque o app se chama
  "Meu Prédio" e tem que ser prédio. O usuário escolheu essa entre 4 opções, mesmo com o céu ainda não fechado.
- **Foto do prédio (opção "A", escolhida pelo usuário):** o síndico envia no Perfil a foto do prédio, que vale
  o dia todo no topo do Início, e opcionalmente uma "à noite" (18h–5h). Sem foto, ficam as fotos padrão por
  horário. Colunas `foto`/`foto_noite` em `condominios`; arquivo em `arquivos` com nome `predios/<aleatório>`,
  novo a cada envio (o celular pode guardar sem mostrar foto velha). Aplicada em `atualizarFotoDoTopo` (app.js).
  Serve para vender: o app "vira" do prédio do cliente na demonstração.
- **Início no computador, layout "B" (2026-10-26):** o usuário achou o Início vazio no notebook/monitor e o cartão
  de atalhos "encavalado" na foto meio torto. Escolheu, entre 3 maquetes, a "B": foto com a saudação à esquerda e,
  à direita, dois cartões (síndico: saldo + "3 de 6 pagas" com barra; morador: minha taxa + saldo); embaixo,
  atenção e recentes lado a lado. A grade de atalhos **não aparece no computador** (o usuário achou repetitivo com o
  menu lateral): no lugar, "ações rápidas" que já fazem algo (síndico: Publicar aviso, Lançar conta, Nova enquete,
  Liberar visita; morador: Liberar visita, Abrir ocorrência, Reservar área).
  O Início usa até 1480px de largura e a barra do topo acompanha a largura do conteúdo (`--largura`/`--respiro`).
  O celular não mudou. `taxas_mes` no `/painel` (só síndico) dá pagas/unidades do mês.
- **Fundo no computador (2026-10-26):** o usuário achou o fundo cinza liso vazio no notebook/monitor. Escolheu,
  entre 3 opções (foto desfocada no topo, prédios no rodapé, degradê nos cantos), os **prédios no rodapé**, "melhorado":
  `web/img/skyline.svg` (dia) e `skyline-noite.svg` (prédios mais escuros, janelas amarelas acesas), em azul bem
  claro, fixos no pé da tela (`.app.com-nav::after`, só ≥960px). Duas camadas de prédios, caixas d'água, antenas e
  árvores. Os SVGs foram gerados por um script Python (prédios aleatórios com semente fixa); para mudar, edite o SVG
  ou gere de novo. Celular sem mudança.
- **Login no computador (2026-10-26):** foto na metade esquerda, de cima a baixo; login à direita, com a marca em
  texto escuro. No celular, igual (foto no alto). Vale para entrar/cadastro, passe do visitante e "Abrir no celular".
- **Histórico do síndico:** só o síndico vê; ninguém apaga pelo app.
- **Contadores e selos:** ninguém é avisado do que ele mesmo fez (encomenda que registrou, enquete ou
  ocorrência que criou, reserva que pediu). Vale para o menu (`/contadores`) e para o Início (`/painel`).

## Armadilhas (leia antes de mexer)

- **Fotos do topo são em pé (até 1000×1500):** numa faixa larga e baixa com `cover`, o navegador amplia e corta a
  foto e só sobra um pedaço do meio (no login do computador aparecia só o teto da varanda). Use molduras em pé
  ou quase quadradas para elas.

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
- **Zoom no iPhone:** campos com letra menor que 16px fazem o Safari dar zoom ao tocar; e o toque duplo
  dá zoom. Por isso `input, textarea, select` têm `font-size: 16px` e o `html` tem `touch-action: manipulation`.
  Não baixe a letra dos campos.
- **Cache das telas (`web/js/api.js`):** `get(..., { fresco: true })` atualiza o cache mas **não** redesenha a tela;
  para buscar de novo e redesenhar se mudou, use `revalidar(caminho)`.
- **Token do Turso colado duas vezes:** o campo de senha não mostra o que se cola; o usuário colou o token em
  dobro (5 partes em vez de 3) e o Turso respondeu "JWT error: Base64 error". `limpar_token` em backup.py corrige.
- **Testes:** `tests/base.py` baixa `auth.ITERACOES` para os testes ficarem rápidos; o cadastro exige
  `"aceito_termos": true`.

## Diário (mais novo primeiro; só acrescente)

- 2026-10-26 — Fundo do computador: fileira de prédios em azul claro no rodapé (versão noite com janelas acesas);
  nome do condomínio alinhado nas telas estreitas. Commitado.
- 2026-10-26 — Foto da noite trocada: era uma casa, agora são torres modernas ao anoitecer (Aalo Lens, mesmo
  fotógrafo da manhã e da tarde). Commitado.
- 2026-10-26 — Login no computador "desenquadrado" corrigido: a foto em pé virava uma faixa larga cortada; agora
  ocupa a metade esquerda da tela. Celular igual. Commitado.
- 2026-10-26 — Início no computador refeito (layout "B": foto + caixa/taxas ao lado, atalhos numa faixa, atenção e
  recentes lado a lado; barra do topo alinhada); atalhos trocados por ações rápidas no computador (repetiam o menu).
  `taxas_mes` no painel do síndico. Celular igual. Commitado.
- 2026-10-26 — Backup/restauração (backup.py, backup.bat), revisão de segurança rota por rota (3 correções),
  trocar senha no Perfil, "Abrir no celular" só na rede local. Primeiro backup real feito. E-mail de contato nos termos. Commitado.
- 2026-10-26 — Síndico envia a foto do prédio (dia e, opcional, noite) no Perfil; aparece no topo do Início
  para todos. Commitado.
- 2026-10-26 — Foto da noite trocada por uma residência moderna (a anterior, prédio de tijolo, foi achada feia).
  Commitado.
- 2026-10-26 — Foto do topo muda com a hora (manhã, tarde, noite de verdade) no Início e no login; saudação nos
  mesmos horários ("Boa noite" de madrugada). Commitado junto com contadores, zoom e fluidez.
- 2026-10-26 — Zoom do iPhone corrigido (letra 16px nos campos, sem zoom no toque duplo); contadores em tempo
  real nas abas e no menu lateral (consulta a cada 10 s; ninguém é avisado do que ele mesmo fez); número
  centralizado na bolinha; telas entram com animação curta; rolagem mais leve; fontes pré-carregadas.
- 2026-10-26 — Criado este CLAUDE.md como registro oficial, a pedido do usuário. Commitado (f74ee6b).
- 2026-10-26 — Visual "Claro" com foto do condomínio no topo, Poppins, barra flutuante, ícone azul
  (commit 909f85e). Publicado na Vercel.
- 2026-10-26 — Migração para Vercel + Turso, limite de tentativas, senhas mais fortes, esqueci minha
  senha, histórico do síndico, LGPD (commit feb3d36). App no ar em meu-predio.vercel.app.
- 2026-10-21 — Visual "Interfone", encomendas, telefones úteis e enquetes (commit be2ebbd).
- 2026-10-02 — MVP fechado: Início com todos os módulos e navegação por perfil (commit 2333ccf).
