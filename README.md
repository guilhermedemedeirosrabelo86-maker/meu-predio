# Meu Prédio

App para condomínios pequenos (8 a 40 unidades) geridos por síndico morador.
É um web app instalável no celular (PWA), com menu lateral e layout em colunas no computador, e tema claro/escuro automático. A identidade visual usa azul-petróleo e pêssego, com títulos serifados e ícones em quadradinhos de fundo suave.

A experiência foi pensada para parecer um app nativo: a troca de abas é instantânea e sem recarregar a página (o endereço muda pela API de histórico, o que evita o Safari do iPhone recarregar tudo a cada aba), com um destaque que desliza na barra de baixo, a rolagem é restaurada ao voltar, o título grande sobe para a barra ao rolar, puxar para atualizar, deslizar no calendário e nas fotos, botões com spinner e vibração leve no Android, máscaras de telefone e placa, e as fontes Inter e Fraunces embutidas (licenças em `web/fonts/`). Quem configura "reduzir movimento" no sistema recebe o app sem animações.

Para rodar liso no celular, as telas já visitadas abrem na hora com os últimos dados e se atualizam sozinhas em segundo plano, e os dados das abas principais são buscados assim que o Início aparece. Salvar qualquer coisa descarta esse cache. O servidor mantém a conexão aberta entre os pedidos, compacta os arquivos de texto e responde "não mudou" para os que o navegador já tem.

- **Início:** grade com todos os módulos do perfil (nada fica escondido), com selos no que pede atenção, pendências do síndico, último aviso e próxima reserva.
- **Navegação:** a barra de baixo do celular mostra o que cada perfil mais usa (síndico: Início, Avisos, Contas, Moradores; morador: Início, Avisos, Reservas, Visitas) e "Mais" reúne o perfil, todos os módulos e a conta. No computador, tudo fica no menu lateral.
- **Conta e acesso:** cadastro, login e sessão de 30 dias. Três perfis: síndico, morador e portaria.
- **Condomínio e convites:** o síndico cadastra o prédio e manda o link no WhatsApp. O morador escolhe a unidade, ou o funcionário entra como portaria, e o síndico aprova.
- **Cadastro:** moradores por unidade, veículos e contatos de emergência, com busca.
- **Avisos:** mural com fixar, editar, contador de não lidos e "lido por X de Y".
- **Reservas:** áreas comuns com regras, antecedência, limite por unidade e aprovação opcional, num calendário mensal.
- **Ocorrências:** o morador relata com categoria e até 5 fotos (reduzidas no celular antes do envio). O síndico responde numa conversa e marca como "em andamento" ou "resolvida". Só o síndico e a própria unidade veem.
- **Prestação de contas:** o síndico lança entradas e saídas por categoria, com a foto da nota ou do recibo. Síndico e moradores veem o saldo em caixa, o que entrou e saiu no mês, para onde foi o dinheiro (gráfico por categoria) e os últimos 6 meses. A portaria não vê as finanças.
- **Taxa condominial:** o síndico define o valor e o dia do vencimento e marca, mês a mês, quais unidades pagaram. Cada pagamento vira uma entrada na prestação de contas (e excluir a entrada desfaz o pagamento). O síndico vê quem está em atraso no Início; o morador vê só a situação da própria unidade.
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

O banco de dados fica em `dados/condominio.db` (SQLite), e as fotos e comprovantes ficam em `dados/arquivos/`. Cada execução do servidor registra os pedidos em `dados/acessos.log`, útil para investigar lentidão. Ao iniciar, o servidor atualiza sozinho bancos criados por versões anteriores.

## Testes

```
python -m unittest -v
```

Os testes sobem o servidor numa porta livre e exercitam a API inteira: permissões, convites, avisos, veículos, reservas, ocorrências com fotos, visitas, portaria, prestação de contas e taxa condominial. `test_servidor.py` confere a conexão reaproveitada, o cache dos arquivos e a compactação.

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

## Próximos passos

1. **Fechamento do mês** (lançamentos travados depois de fechado) e **balancete em PDF** para a assembleia.
2. **Hospedagem com HTTPS** e **Web Push**, para notificar com o app fechado. Com HTTPS, o celular do morador também passa a instalar o app e a ler o QR Code pela câmera dentro do próprio app (hoje isso só funciona em `localhost`).
3. **Alertas automáticos:** pedido de reserva, resposta em ocorrência e chegada de visitante.
4. **Recuperação de senha** por e-mail e limite de tentativas de login.
5. **Planos:** o campo `plano` já existe no condomínio (padrão `gratis`). Falta aplicar os limites, como 10 unidades no plano grátis.
