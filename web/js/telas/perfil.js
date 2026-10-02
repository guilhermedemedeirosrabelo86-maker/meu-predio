import { del, get, patch, post } from '../api.js';
import { carregarUsuario, estado, limparSessao, navegar, recarregar } from '../estado.js';
import { pararVerificacao, pedirPermissao, suportaNotificacoes } from '../notificacoes.js';
import {
  aoEnviar, avatar, cabecalho, campo, comErro, confirmar, erroForm, h, icone, item, linkTelefone, mascaraTelefone, NOMES_PAPEL,
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
    secao('Conta', cartaoConta()));
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
