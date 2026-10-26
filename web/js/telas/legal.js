import { estado } from '../estado.js';
import { cabecalho, h, secao } from '../ui.js';

// RASCUNHO: revisar com um advogado antes de vender. Preencha os dados abaixo (aparecem nas duas páginas).
const RESPONSAVEL = {
  nome: '[nome da empresa ou seu nome]',
  documento: '[CNPJ ou CPF]',
  email: '[e-mail para assuntos de privacidade]',
};
const ATUALIZADO_EM = '26/10/2026';

// Páginas abertas (sem a moldura do app): o <main class="conteudo"> dá as margens.
const pagina = (titulo, blocos) => h('main', { class: 'conteudo pagina legal' },
  cabecalho(titulo, {
    subtitulo: `Atualizado em ${ATUALIZADO_EM}`,
    voltar: estado.usuario ? { rota: 'perfil', texto: 'Perfil' } : { rota: 'criar-conta', texto: 'Criar conta' },
  }),
  blocos.map(([subtitulo, ...paragrafos]) => secao(subtitulo,
    h('div', { class: 'cartao pilha-curta' }, paragrafos.map((p) => h('p', {}, p))))),
  h('p', { class: 'mudo pequeno' }, `${RESPONSAVEL.nome} · ${RESPONSAVEL.documento} · ${RESPONSAVEL.email}`));

export function telaPrivacidade() {
  return pagina('Política de privacidade', [
    ['Quem cuida dos seus dados',
      `O Meu Prédio é oferecido por ${RESPONSAVEL.nome} (${RESPONSAVEL.documento}). Pela LGPD (Lei 13.709/2018), o seu condomínio é o controlador dos dados do prédio, e nós somos o operador: guardamos e processamos os dados para o condomínio usar o app.`,
      `Para qualquer pedido sobre seus dados, escreva para ${RESPONSAVEL.email}.`],
    ['Quais dados guardamos',
      'Da sua conta: nome, e-mail, celular (opcional) e a senha, que é guardada embaralhada e nunca pode ser lida, nem por nós.',
      'Do condomínio: a sua unidade, contatos de emergência, veículos, reservas, ocorrências e fotos que você enviar, votos em enquetes, visitantes que você liberar (nome e período) e encomendas da sua unidade.',
      'Do síndico, também: lançamentos e comprovantes da prestação de contas e o histórico de ações.'],
    ['Para que usamos',
      'Só para o app funcionar: mostrar avisos, controlar reservas, liberar visitantes na portaria, prestar contas e permitir a comunicação entre moradores, síndico e portaria. Não vendemos dados e não usamos para publicidade.'],
    ['Quem vê',
      'Os moradores veem avisos, reservas, enquetes e a prestação de contas do próprio condomínio. O síndico vê o cadastro dos moradores, inclusive celular e contatos de emergência. A portaria vê os visitantes liberados e as encomendas. Ninguém de outro condomínio vê nada do seu.'],
    ['Onde ficam',
      'Os dados ficam em serviços de nuvem contratados por nós (hospedagem e banco de dados), que podem estar fora do Brasil, com conexão criptografada (HTTPS).'],
    ['Por quanto tempo',
      'Visitantes: apagados 180 dias depois do fim da liberação. Encomendas: apagadas 180 dias depois de retiradas. Sua conta: até você excluí-la.',
      'Quando você exclui a conta, seus dados pessoais são apagados. O que é registro do condomínio (avisos, ocorrências, prestação de contas e histórico) continua com o condomínio, sem ligação com a sua conta.'],
    ['Seus direitos',
      'No Perfil, você pode corrigir seus dados, baixar uma cópia de tudo o que está ligado à sua conta e excluir a conta. Para outros pedidos, como saber com quem compartilhamos dados, use o e-mail acima.'],
    ['Cookies',
      'Usamos um único cookie, para manter você conectado. Não usamos cookies de propaganda nem de rastreamento.'],
  ]);
}

export function telaTermos() {
  return pagina('Termos de uso', [
    ['O que é o Meu Prédio',
      'Um app para a comunicação e a organização do condomínio: avisos, reservas, visitantes, encomendas, ocorrências, enquetes e prestação de contas.'],
    ['Sua conta',
      'Você é responsável pelas informações que cadastra e por manter sua senha em segredo. Cada pessoa deve ter a própria conta.'],
    ['Síndico',
      'Quem cria o condomínio no app é o síndico e responde pelo que publica, pelas pessoas que aprova e pelas informações financeiras que lança. O app registra as ações do síndico no histórico.'],
    ['Uso permitido',
      'Não é permitido publicar conteúdo ofensivo, ilegal ou que exponha outras pessoas, tentar acessar dados de outro condomínio ou atrapalhar o funcionamento do app. Contas que fizerem isso podem ser suspensas.'],
    ['Disponibilidade',
      'Trabalhamos para o app ficar sempre no ar, mas podem acontecer interrupções para manutenção ou por falhas de terceiros. O app não substitui os canais oficiais do condomínio em emergências.'],
    ['Planos e pagamento',
      '[Descreva aqui os planos, valores, forma de cobrança e cancelamento quando começar a cobrar.]'],
    ['Encerramento',
      'Você pode excluir sua conta quando quiser, no Perfil. Podemos encerrar o serviço avisando com antecedência, para o condomínio baixar seus dados.'],
    ['Mudanças e foro',
      'Se estes termos mudarem, avisaremos no app. Fica eleito o foro de [cidade/UF] para resolver qualquer questão.'],
  ]);
}
