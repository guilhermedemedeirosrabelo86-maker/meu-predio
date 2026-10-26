import { del, get, patch, post } from '../api.js';
import { carregarUsuario, estado, limparSessao, navegar, recarregar } from '../estado.js';
import { pararVerificacao, pedirPermissao, suportaNotificacoes } from '../notificacoes.js';
import {
  aoEnviar, avatar, cabecalho, campo, campoSenha, comErro, confirmar, erroForm, h, icone, item, linkTelefone, mascaraTelefone, NOMES_PAPEL,
  pill, secao, tile, toast,
} from '../ui.js';

export async function sairDaConta() {
  await post('/api/auth/logout');
  limparSessao();
  pararVerificacao();
  navegar('entrar');
}

export async function telaPerfil() {
  const membro = estado.membro;
  const sindico = membro?.papel === 'sindico';
  const [{ contatos }, condominio] = await Promise.all([
    get('/api/eu/contatos'),
    sindico ? get(`/api/condominios/${membro.condominio_id}`) : null,
  ]);
  const u = estado.usuario;

  return h('div', { class: 'pagina estreita' },
    cabecalho('Perfil', { voltar: membro ? { rota: 'menu', texto: 'Mais' } : { rota: 'condominios' } }),
    h('section', { class: 'cartao' },
      h('div', { class: 'perfil-topo' },
        avatar(u.nome, 'grande'),
        h('div', { class: 'item-texto' },
          h('h2', {}, u.nome),
          h('span', { class: 'mudo pequeno' }, u.email),
          membro && h('span', {}, pill([NOMES_PAPEL[membro.papel], membro.unidade && `Unidade ${membro.unidade}`].filter(Boolean).join(' · '), 'roxo'))))),
    secao('Meus dados', formDados()),
    secao('Contatos de emergência', cartaoContatos(contatos)),
    membro && secao('Notificações', cartaoNotificacoes()),
    estado.pedidoInstalacao && cartaoInstalar(),
    sindico && secao('Condomínio', formCondominio(condominio)),
    secao('Conta', cartaoConta()),
    secao('Privacidade', cartaoPrivacidade()));
}

function formDados() {
  const u = estado.usuario;
  const form = h('form', { class: 'cartao' },
    campo('Nome', h('input', { name: 'nome', required: true, maxlength: 100, autocomplete: 'name', value: u.nome })),
    campo('Celular', mascaraTelefone(h('input', { name: 'telefone', type: 'tel', maxlength: 30, autocomplete: 'tel', value: u.telefone, placeholder: '(11) 99999-0000' })),
      'Só o síndico vê.'),
    erroForm(),
    h('div', { class: 'acoes fim' }, h('button', { class: 'botao primario', type: 'submit' }, 'Salvar')));
  aoEnviar(form, async (dados) => {
    await patch('/api/eu', dados);
    await carregarUsuario();
    toast('Dados salvos.');
    recarregar();
  });
  return form;
}

function cartaoContatos(contatos) {
  const form = h('form', { class: 'pilha' },
    h('div', { class: 'linha' },
      campo('Nome', h('input', { name: 'nome', required: true, maxlength: 100 })),
      campo('Parentesco', h('input', { name: 'parentesco', maxlength: 40, placeholder: 'Ex.: filha' }))),
    campo('Telefone', mascaraTelefone(h('input', { name: 'telefone', type: 'tel', required: true, maxlength: 30, placeholder: '(11) 99999-0000' }))),
    erroForm(),
    h('button', { class: 'botao tonal bloco', type: 'submit' }, icone('mais'), 'Adicionar contato'));
  aoEnviar(form, async (dados) => {
    await post('/api/eu/contatos', dados);
    toast('Contato adicionado.');
    recarregar();
  });

  return h('div', { class: 'cartao' },
    h('p', { class: 'dica' }, 'Quem o síndico deve chamar se algo acontecer com você. Só o síndico vê.'),
    contatos.length > 0 && h('div', { class: 'cartao lista' }, contatos.map((c) => item({
      inicio: tile('telefone', 'ocorrencias'),
      titulo: c.parentesco ? `${c.nome} (${c.parentesco})` : c.nome,
      sub: h('a', { href: linkTelefone(c.telefone) }, c.telefone),
      fim: h('button', {
        class: 'botao fantasma pequeno perigo',
        'aria-label': `Remover ${c.nome}`,
        onclick: comErro(async () => {
          await del(`/api/eu/contatos/${c.id}`);
          recarregar();
        }),
      }, icone('lixo')),
      seta: false,
    }))),
    contatos.length < 5 && form);
}

function cartaoNotificacoes() {
  if (!suportaNotificacoes()) {
    return h('div', { class: 'cartao lista' }, item({
      inicio: tile('sino', 'neutra'),
      titulo: 'Indisponível neste navegador',
      sub: 'No iPhone, adicione o app à Tela de Início primeiro.',
    }));
  }
  const textos = {
    granted: ['Ativadas', 'Você é avisado quando sair um aviso novo com o app aberto, mesmo em segundo plano.', 'verde'],
    denied: ['Bloqueadas', 'Libere as notificações deste site nas configurações do navegador.', 'vermelho'],
    default: ['Desativadas', 'Receba um alerta quando o síndico publicar um aviso.', ''],
  };
  const [estadoTexto, sub, cor] = textos[Notification.permission];
  const ativar = comErro(async () => {
    if (await pedirPermissao() === 'granted') toast('Notificações ativadas!');
    recarregar();
  });
  return h('div', { class: 'cartao lista' }, item({
    inicio: tile('sino', 'avisos'),
    titulo: 'Alertas de avisos',
    sub,
    fim: Notification.permission === 'default'
      ? h('button', { class: 'botao primario pequeno', onclick: ativar }, 'Ativar')
      : pill(estadoTexto, cor),
    seta: false,
  }));
}

function cartaoInstalar() {
  const instalar = async () => {
    const pedido = estado.pedidoInstalacao;
    estado.pedidoInstalacao = null;
    pedido.prompt();
    await pedido.userChoice;
    recarregar();
  };
  return h('div', { class: 'cartao lista' }, item({
    inicio: tile('instalar', 'unidade'),
    titulo: 'Instalar o app',
    sub: 'Abra o Meu Prédio direto da tela inicial, como um aplicativo.',
    fim: h('button', { class: 'botao primario pequeno', onclick: instalar }, 'Instalar'),
    seta: false,
  }));
}

function formCondominio(condominio) {
  const form = h('form', { class: 'cartao' },
    campo('Nome', h('input', { name: 'nome', required: true, maxlength: 100, value: condominio.nome })),
    campo('Endereço', h('input', { name: 'endereco', maxlength: 200, value: condominio.endereco })),
    erroForm(),
    h('div', { class: 'acoes fim' }, h('button', { class: 'botao primario', type: 'submit' }, 'Salvar')));
  aoEnviar(form, async (dados) => {
    await patch(`/api/condominios/${condominio.id}`, dados);
    await carregarUsuario();
    toast('Condomínio atualizado.');
    recarregar();
  });
  return form;
}

function cartaoConta() {
  const membro = estado.membro;
  const sairDoCondominio = comErro(async () => {
    if (!await confirmar(`Você deixará de ver os avisos e reservas do ${membro.condominio}.`, { titulo: 'Sair do condomínio?', botao: 'Sair', perigo: true })) return;
    await del(`/api/condominios/${membro.condominio_id}/membros/${membro.membro_id}`);
    await carregarUsuario();
    toast(`Você saiu do ${membro.condominio}.`);
    navegar('condominios');
  });
  return h('div', { class: 'cartao lista' },
    item({ inicio: tile('trocar', 'neutra'), titulo: 'Trocar ou adicionar condomínio', href: '#/condominios' }),
    item({ inicio: tile('celular', 'visitas'), titulo: 'Abrir no celular', sub: 'QR Code para testar no celular pela rede Wi-Fi', href: '#/celular' }),
    membro && item({ inicio: tile('sair', 'neutra'), titulo: 'Sair deste condomínio', onclick: sairDoCondominio, seta: false }),
    item({ inicio: tile('sair', 'ocorrencias'), titulo: 'Sair da conta', onclick: comErro(sairDaConta), seta: false }));
}

async function baixarMeusDados() {
  const dados = await get('/api/eu/dados', { fresco: true });
  const arquivo = new Blob([JSON.stringify(dados, null, 2)], { type: 'application/json' });
  const link = h('a', { href: URL.createObjectURL(arquivo), download: 'meus-dados-meu-predio.json' });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 10_000);
}

/** Pede a senha antes de excluir. Se for o único síndico, o servidor explica o que fazer antes. */
function excluirConta() {
  const form = h('form', { class: 'pilha' },
    h('div', { class: 'pilha-curta' },
      h('h2', {}, 'Excluir sua conta?'),
      h('p', { class: 'mudo' }, 'Seus dados pessoais serão apagados e não dá para desfazer. Avisos, ocorrências e a prestação de contas continuam com o condomínio, sem o seu nome.')),
    campoSenha('Digite sua senha para confirmar', { name: 'senha', autocomplete: 'current-password', required: true }),
    erroForm(),
    h('div', { class: 'acoes dividir' },
      h('button', { class: 'botao', type: 'button', onclick: () => dialogo.close() }, 'Voltar'),
      h('button', { class: 'botao perigo', type: 'submit' }, 'Excluir conta')));
  const dialogo = h('dialog', { class: 'dialogo' }, form);
  aoEnviar(form, async (dados) => {
    await post('/api/eu/excluir', dados);
    dialogo.close();
    limparSessao();
    pararVerificacao();
    toast('Sua conta foi excluída.');
    navegar('entrar');
  });
  dialogo.addEventListener('close', () => dialogo.remove());
  document.body.append(dialogo);
  dialogo.showModal();
}

function cartaoPrivacidade() {
  return h('div', { class: 'cartao lista' },
    item({ inicio: tile('baixar', 'neutra'), titulo: 'Baixar meus dados', sub: 'Uma cópia de tudo o que está ligado à sua conta', onclick: comErro(baixarMeusDados), seta: false }),
    item({ inicio: tile('documento', 'neutra'), titulo: 'Termos de uso', href: '#/termos' }),
    item({ inicio: tile('seguranca', 'neutra'), titulo: 'Política de privacidade', href: '#/privacidade' }),
    item({ inicio: tile('lixo', 'ocorrencias'), titulo: 'Excluir minha conta', onclick: excluirConta, seta: false }));
}
