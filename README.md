# Meu Prédio

App para condomínios pequenos (8 a 40 unidades) geridos por síndico morador.
É um web app instalável no celular (PWA), com menu lateral e layout em colunas no computador. O visual é claro e suave: fundo quase branco, cartões brancos com sombra leve e cantos arredondados, azul como cor de destaque e a foto de um condomínio no topo do Início e das telas de entrada, que muda com a hora do celular: amanhecer de manhã, dia à tarde e janelas acesas à noite (fotos de Aalo Lens no Unsplash e, a da noite, do Pexels; em `web/img/`). No celular, a barra de baixo é branca e flutuante.

A experiência foi pensada para parecer um app nativo: a troca de abas é instantânea e sem recarregar a página (o endereço muda pela API de histórico, o que evita o Safari do iPhone recarregar tudo a cada aba), com um destaque que desliza na barra de baixo, a rolagem é restaurada ao voltar, o título grande sobe para a barra ao rolar, puxar para atualizar, deslizar no calendário e nas fotos, botões com spinner e vibração leve no Android, máscaras de telefone e placa, e a fonte Poppins embutida (licença em `web/fonts/`). Quem configura "reduzir movimento" no sistema recebe o app sem animações.

Para rodar liso no celular, as telas já visitadas abrem na hora com os últimos dados e se atualizam sozinhas em segundo plano, e os dados das abas principais são buscados assim que o Início aparece. Salvar qualquer coisa descarta esse cache. O servidor mantém a conexão aberta entre os pedidos, compacta os arquivos de texto e responde "não mudou" para os que o navegador já tem.

- **Início:** a foto do condomínio com a saudação e a unidade, os atalhos de todos os módulos em ícones redondos, uma lista do que pede ação agora (pendências do síndico; encomendas, enquetes, taxa e visitas do morador), o saldo do caixa com o movimento do mês e o que aconteceu por último.
- **Navegação:** a barra de baixo do celular mostra o que cada perfil mais usa (síndico: Início, Avisos, Contas, Moradores; morador: Início, Avisos, Reservas, Visitas) e "Mais" reúne o perfil, todos os módulos e a conta. No computador, tudo fica no menu lateral.
- **Conta e acesso:** cadastro, login e sessão de 30 dias. Três perfis: síndico, morador e portaria.
- **Condomínio e convites:** o síndico cadastra o prédio e manda o link no WhatsApp. O morador escolhe a unidade, ou o funcionário entra como portaria, e o síndico aprova.
- **Cadastro:** moradores por unidade, veículos e contatos de emergência, com busca.
- **Avisos:** mural com fixar, editar, contador de não lidos e "lido por X de Y".
- **Reservas:** áreas comuns com regras, antecedência, limite por unidade e aprovação opcional, num calendário mensal.
- **Ocorrências:** o morador relata com categoria e até 5 fotos (reduzidas no celular antes do envio). O síndico responde numa conversa e marca como "em andamento" ou "resolvida". Só o síndico e a própria unidade veem.
- **Prestação de contas:** o síndico lança entradas e saídas por categoria, com a foto da nota ou do recibo. Síndico e moradores veem o saldo em caixa, o que entrou e saiu no mês, para onde foi o dinheiro (gráfico por categoria) e os últimos 6 meses. A portaria não vê as finanças.
- **Taxa condominial:** o síndico define o valor e o dia do vencimento e marca, mês a mês, quais unidades pagaram. Cada pagamento vira uma entrada na prestação de contas (e excluir a entrada desfaz o pagamento). O síndico vê quem está em atraso no Início; o morador vê só a situação da própria unidade.
- **Encomendas:** a portaria (ou o síndico) registra o pacote que chegou para uma unidade e, na retirada, quem levou. O morador vê no Início e na tela de encomendas o que está esperando por ele.
- **Telefones úteis:** o síndico cadastra zelador, prestadores e serviços. Todos ligam com um toque, e celulares ganham o botão do WhatsApp.
- **Enquetes:** o síndico abre uma votação com até 6 opções e prazo opcional. Cada unidade vota uma vez (e pode mudar o voto enquanto estiver aberta), e todos acompanham o resultado. A portaria não vê.
- **Visitantes por QR Code:** o morador libera a visita (um dia ou vários) e envia o QR pelo WhatsApp. O visitante abre um link público com o QR. A portaria lê com a câmera do celular (o QR abre a tela de validação), confere se está liberado e registra a entrada. Também dá para digitar o código curto.

## Como rodar

Precisa só do Python 3.11 ou mais novo. Não usa nenhuma biblioteca externa.

```
python rodar.py
```

Ou dê dois cliques em `iniciar.bat`. O app abre em http://localhost:8000.

### Abrir no celular

1. Conecte o celular no **mesmo Wi-Fi** do computador.
2. Feche outras janelas do servidor e dê dois cliques em `iniciar-celular.bat`. Ele inicia o servidor aberto para a rede e abre no computador a página `#/celular`, com um QR Code. Se a porta 8000 estiver ocupada, o servidor usa a próxima livre e avisa na janela.
3. Aponte a câmera do celular para o QR Code (ou digite o endereço mostrado, como `http://192.168.0.12:8000`).

Se o celular não carregar, o Firewall do Windows está bloqueando. Na primeira vez, o Windows pergunta se o Python pode acessar a rede: permita no tipo de rede em uso. Em computador da empresa, isso pode exigir o suporte de TI.
Pelo IP, o navegador não libera instalação na tela inicial nem notificações, porque elas exigem HTTPS. Isso passa a funcionar quando o app for hospedado.

O banco de dados fica em `dados/condominio.db` (SQLite), e as fotos e comprovantes ficam dentro dele, na tabela `arquivos`. Cada execução do servidor registra os pedidos em `dados/acessos.log`, útil para investigar lentidão. Ao iniciar, o servidor atualiza sozinho bancos criados por versões anteriores.

## Testes

```
python -m unittest -v
```

Os testes sobem o servidor numa porta livre e exercitam a API inteira: permissões, convites, avisos, veículos, reservas, ocorrências com fotos, visitas, portaria, prestação de contas, taxa condominial, encomendas, telefones úteis e enquetes. `test_servidor.py` confere a conexão reaproveitada, o cache dos arquivos e a compactação.

O gerador de QR Code (`web/js/qrcode.js`) foi conferido contra a biblioteca Python `qrcode` (saída idêntica módulo a módulo nas 8 máscaras) e com o leitor zxing.

## Estrutura

```
rodar.py                 inicia o servidor
backend/
  servidor.py            HTTP: arquivos do app + API JSON
  web.py                 roteador
  db.py                  esquema SQLite
  auth.py                senhas (PBKDF2), sessões, códigos de convite
  comum.py               validação e checagem de permissões
  rotas_conta.py         cadastro, login, perfil, contatos de emergência
  rotas_condominio.py    condomínio, convites, unidades, moradores, veículos
  rotas_avisos.py        mural de avisos
  rotas_reservas.py      áreas comuns e reservas
  rotas_ocorrencias.py   ocorrências, fotos e conversa
  rotas_visitas.py       visitas por QR Code e portaria
  rotas_contas.py        prestação de contas e comprovantes
  rotas_taxas.py         taxa condominial: quem pagou em cada mês
  rotas_encomendas.py    encomendas na portaria
  rotas_telefones.py     telefones úteis
  rotas_enquetes.py      enquetes e votos por unidade
  rotas_painel.py        resumo da tela inicial
web/
  index.html, sw.js, manifest.webmanifest
  css/app.css
  js/app.js              roteador, navegação por perfil e layout
  js/ui.js               componentes (ícones, listas, botões, diálogos)
  js/qrcode.js           gerador de QR Code sem dependências
  js/telas/*.js          uma tela por arquivo
tests/                   base.py (servidor de teste) e um arquivo por módulo
```

## Hospedar na Vercel

Na Vercel, as telas (pasta `web/`) saem direto da rede da Vercel e os pedidos a `/api/...` rodam em `api/index.py`, que usa o mesmo código do servidor local. Como a Vercel não guarda arquivos entre um pedido e outro, o banco fica no [Turso](https://turso.tech) (SQLite na nuvem), e fotos e comprovantes ficam numa tabela do próprio banco.

1. **Turso:** crie uma conta, crie um banco e copie o endereço (`libsql://....turso.io`) e um token de acesso.
2. **Vercel:** em *Add New → Project*, importe o repositório do GitHub. Não precisa mudar nada no formulário: o `vercel.json` já diz tudo.
3. Em *Settings → Environment Variables*, adicione as variáveis abaixo e faça um novo deploy.

| Variável | Para quê |
|---|---|
| `TURSO_DATABASE_URL` | Endereço do banco (`libsql://...`). Obrigatória. |
| `TURSO_AUTH_TOKEN` | Token de acesso ao banco. Obrigatória. |
| `APP_URL` | Endereço do app (ex.: `https://meupredio.vercel.app`), usado no link de "esqueci minha senha". |
| `RESEND_API_KEY` | Chave do [Resend](https://resend.com), que envia os e-mails. Sem ela, o e-mail não sai. |
| `EMAIL_REMETENTE` | Ex.: `Meu Prédio <nao-responda@seudominio.com.br>`. O domínio precisa estar verificado no Resend. |
| `CRON_SECRET` | Uma senha qualquer e longa. A Vercel a usa para rodar, uma vez por dia, a limpeza de dados antigos. |

As tabelas são criadas sozinhas no primeiro acesso. Com HTTPS, o cookie de sessão passa a ser `Secure`.

**Antes de vender:** preencha os dados da empresa no início de `web/js/telas/legal.js` (termos de uso e política de privacidade) e peça para um advogado revisar o texto.

## Backup

Dê dois cliques em `backup.bat` (ou `python backup.py`). Ele copia o banco inteiro do Turso, com fotos e comprovantes, para `dados/backups/backup-AAAA-MM-DD-HHMM.db`. Na primeira vez, pede o endereço e o token do banco (painel do Turso) e oferece guardá-los em `dados/turso.json`, que não vai para o GitHub.

Para conferir um backup, abra o app em cima dele: `python rodar.py --banco dados/backups/ARQUIVO.db`.
Para restaurar: crie um banco **novo e vazio** no Turso, rode `python backup.py restaurar dados/backups/ARQUIVO.db`, informe o endereço e o token do banco novo e troque `TURSO_DATABASE_URL` e `TURSO_AUTH_TOKEN` na Vercel. A restauração recusa bancos com dados, para nunca sobrescrever nada.

## Segurança e privacidade

- **Senhas:** PBKDF2-SHA256 com 600 mil repetições. Senhas antigas são refeitas no próximo login.
- **Limite de tentativas** (`backend/limites.py`): 5 senhas erradas por conta e 30 por endereço em 15 minutos; o mesmo vale para códigos de convite e para "esqueci minha senha".
- **Trocar senha** no Perfil (pede a atual e desconecta os outros aparelhos) e limite de 20 cadastros por endereço a cada 15 minutos.
- **Esqueci minha senha:** link por e-mail que vale 1 hora e uma vez só; trocar a senha desconecta todos os aparelhos.
- **Histórico** (`backend/historico.py`): o que o síndico faz no dinheiro, nos moradores e nas exclusões fica registrado, sem como apagar pelo app.
- **LGPD** (`backend/rotas_privacidade.py`): aceite dos termos no cadastro, "Baixar meus dados" e "Excluir minha conta" no Perfil, e limpeza automática de visitantes e encomendas com mais de 180 dias.

Para rodar os testes contra um "Turso" de mentira (servidor local que fala a mesma API): `MEU_PREDIO_TESTE_TURSO=1 python -m unittest discover -s tests`.

## Próximos passos

1. **Fechamento do mês** (lançamentos travados depois de fechado) e **balancete em PDF** para a assembleia.
2. **Web Push**, para notificar com o app fechado (depende da hospedagem com HTTPS). Com HTTPS, o celular do morador também passa a instalar o app e a ler o QR Code pela câmera dentro do próprio app (hoje isso só funciona em `localhost`).
3. **Alertas automáticos:** pedido de reserva, resposta em ocorrência e chegada de visitante.
4. **Banco Postgres** (Neon ou Supabase, região São Paulo) quando passar do piloto, e fotos num armazenamento de arquivos (Vercel Blob ou Supabase Storage).
5. **Planos:** o campo `plano` já existe no condomínio (padrão `gratis`). Falta aplicar os limites, como 10 unidades no plano grátis.
