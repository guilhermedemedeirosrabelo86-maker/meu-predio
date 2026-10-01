import { del, ErroApi, get, post } from '../api.js';
import { carregarUsuario, escolherCondominio, estado, navegar, recarregar } from '../estado.js';
import {
  aoEnviar, cabecalho, campo, comErro, confirmar, erroForm, h, icone, item, maiusculas, NOMES_PAPEL, opcoes, pill,
  primeiroNome, secao, tile, toast,
} from '../ui.js';

const destinoDoPapel = (papel) => (papel === 'portaria' ? 'portaria' : 'inicio');

/** Escolher condomínio, acompanhar pedidos pendentes e começar (criar ou entrar). */
export function telaCondominios() {
  const ativos = estado.condominios.filter((c) => c.status === 'ativo');
  const pendentes = estado.condominios.filter((c) => c.status === 'pendente');
  const primeiraVez = ativos.length === 0 && pendentes.length === 0;

  return h('div', { class: 'pagina estreita' },
    cabecalho(primeiraVez ? `Olá, ${primeiroNome(estado.usuario.nome)}!` : 'Seus condomínios',
      { subtitulo: primeiraVez ? 'Vamos colocar seu condomínio no app.' : 'Escolha qual condomínio abrir.' }),
    pendentes.map(cartaoPendente),
    ativos.length > 0 && h('div', { class: 'cartao lista' }, ativos.map((c) => item({
      inicio: tile('predio', 'unidade'),
      titulo: c.condominio,
      sub: [NOMES_PAPEL[c.papel], c.unidade && `Unidade ${c.unidade}`].filter(Boolean).join(' · '),
      fim: c.condominio_id === estado.membro?.condominio_id && pill('Aberto', 'verde'),
      onclick: () => {
        escolherCondominio(c.condominio_id);
        navegar(destinoDoPapel(c.papel));
      },
    }))),
    secao(primeiraVez ? 'Como você quer começar?' : 'Adicionar outro', h('div', { class: 'cartao lista' },
      item({ inicio: tile('predio', 'moradores'), titulo: 'Sou síndico', sub: 'Cadastrar meu condomínio e convidar os moradores', href: '#/novo-condominio' }),
      item({ inicio: tile('link', 'visitas'), titulo: 'Recebi um convite', sub: 'Entrar com o código que o síndico mandou', href: '#/convite' }))));
}

function cartaoPendente(pedido) {
  const cancelar = comErro(async () => {
    if (!await confirmar(`Cancelar o pedido para entrar no ${pedido.condominio}?`, { botao: 'Cancelar pedido', perigo: true })) return;
    await del(`/api/condominios/${pedido.condominio_id}/membros/${pedido.membro_id}`);
    await carregarUsuario();
    recarregar();
  });
  const verificar = comErro(async () => {
    await carregarUsuario();
    const agora = estado.condominios.find((c) => c.membro_id === pedido.membro_id);
    if (agora?.status === 'ativo') {
      escolherCondominio(pedido.condominio_id);
      toast('Seu acesso foi aprovado!');
      navegar(destinoDoPapel(agora.papel));
    } else {
      toast('Ainda aguardando o síndico.');
      recarregar();
    }
  });
  return h('section', { class: 'cartao alerta' },
    h('div', { class: 'aviso-topo' },
      h('span', { class: 'tile cor-avisos' }, icone('relogio')),
      h('div', { class: 'item-texto' },
        h('h2', {}, 'Aguardando aprovação'),
        h('p', { class: 'mudo' }, `Você pediu para entrar no ${pedido.condominio}`
          + `${pedido.unidade ? `, unidade ${pedido.unidade}` : ''}. Assim que o síndico aprovar, tudo aparece aqui.`))),
    h('div', { class: 'acoes' },
      h('button', { class: 'botao primario', onclick: verificar }, 'Verificar agora'),
      h('button', { class: 'botao fantasma perigo', onclick: cancelar }, 'Cancelar pedido')));
}

const separarUnidades = (texto) => texto.split(/[\n,;]+/).map((s) => s.trim()).filter(Boolean);

export function telaNovoCondominio() {
  const lista = h('textarea', { name: 'unidades', rows: 6, placeholder: '101\n102\n201\n202' });
  const contador = h('small', { class: 'dica' }, 'Nenhuma unidade ainda.');
  const atualizarContador = () => {
    const n = separarUnidades(lista.value).length;
    contador.textContent = n === 0 ? 'Nenhuma unidade ainda.' : n === 1 ? '1 unidade' : `${n} unidades`;
  };
  lista.addEventListener('input', atualizarContador);

  const andares = h('input', { type: 'number', min: 1, max: 60, value: 4, inputmode: 'numeric' });
  const porAndar = h('input', { type: 'number', min: 1, max: 20, value: 2, inputmode: 'numeric' });
  const gerar = () => {
    const limitar = (campoNumero, maximo) => Math.min(maximo, Math.max(1, Number(campoNumero.value) || 1));
    const nomes = [];
    for (let andar = 1; andar <= limitar(andares, 60); andar++) {
      for (let apto = 1; apto <= limitar(porAndar, 20); apto++) nomes.push(`${andar}${String(apto).padStart(2, '0')}`);
    }
    lista.value = nomes.join('\n');
    atualizarContador();
  };

  const form = h('form', { class: 'pagina' },
    h('section', { class: 'cartao' },
      h('h2', {}, 'Dados do condomínio'),
      campo('Nome', h('input', { name: 'nome', required: true, maxlength: 100, placeholder: 'Residencial das Flores' })),
      campo('Endereço', h('input', { name: 'endereco', maxlength: 200, autocomplete: 'street-address', placeholder: 'Opcional' }))),
    h('section', { class: 'cartao' },
      h('div', { class: 'pilha-curta' },
        h('h2', {}, 'Unidades'),
        h('p', { class: 'dica' }, 'Gere pelos andares ou digite uma por linha (ex.: 101, Casa 3, Bloco B 12).')),
      h('div', { class: 'linha' },
        campo('Andares', andares),
        campo('Aptos por andar', porAndar),
        h('button', { type: 'button', class: 'botao tonal', onclick: gerar }, 'Gerar lista')),
      campo('Lista de unidades', lista, contador),
      campo('Sua unidade', h('input', { name: 'minha_unidade', maxlength: 30, placeholder: 'Ex.: 101' }),
        'Se você mora no condomínio. Deixe em branco se não mora.')),
    erroForm(),
    h('button', { class: 'botao primario grande bloco', type: 'submit' }, 'Criar condomínio'));

  aoEnviar(form, async (dados) => {
    const criado = await post('/api/condominios', {
      nome: dados.nome,
      endereco: dados.endereco,
      minha_unidade: dados.minha_unidade,
      unidades: separarUnidades(dados.unidades),
    });
    await carregarUsuario();
    escolherCondominio(criado.id);
    toast('Condomínio criado! Agora convide os moradores.');
    navegar('moradores');
  });

  return h('div', { class: 'pagina estreita' },
    cabecalho('Cadastrar condomínio', { voltar: { rota: 'condominios' }, subtitulo: 'Você será o síndico no app.' }),
    form);
}

export async function telaConvite({ codigo } = {}) {
  if (!codigo) {
    const form = h('form', { class: 'cartao' },
      campo('Código de convite',
        maiusculas(h('input', { name: 'codigo', class: 'codigo', required: true, maxlength: 12, autocomplete: 'off', autocapitalize: 'characters', placeholder: 'ABC234' })),
        'Peça o código ao síndico do seu condomínio.'),
      h('button', { class: 'botao primario grande bloco', type: 'submit' }, 'Continuar'));
    aoEnviar(form, async (dados) => navegar(`convite/${encodeURIComponent(dados.codigo.trim().toUpperCase())}`));
    return h('div', { class: 'pagina estreita' },
      cabecalho('Entrar em um condomínio', { voltar: { rota: 'condominios' } }),
      form);
  }

  let convite;
  try {
    convite = await get(`/api/convites/${encodeURIComponent(codigo)}`);
  } catch (e) {
    if (!(e instanceof ErroApi && e.status === 404)) throw e;
    return h('div', { class: 'vazio' },
      tile('link', 'ocorrencias', 'grande'),
      h('h2', {}, 'Convite não encontrado'),
      h('p', {}, `O código ${codigo} não existe ou foi trocado pelo síndico.`),
      h('a', { class: 'botao primario', href: '#/convite' }, 'Digitar outro código'));
  }

  const { condominio, unidades } = convite;
  const seletor = h('select', { name: 'unidade_id' },
    h('option', { value: '' }, 'Escolha sua unidade…'),
    unidades.map((u) => h('option', { value: u.id }, u.identificador)));
  const campoUnidade = campo('Unidade', seletor);

  const form = h('form', { class: 'cartao' },
    h('h2', {}, 'Como você participa do condomínio?'),
    opcoes('vinculo', [
      { valor: 'morador', rotulo: 'Moro aqui', icone: 'unidade', cor: 'unidade' },
      { valor: 'funcionario', rotulo: 'Trabalho aqui (portaria, zeladoria)', icone: 'portaria', cor: 'portaria' },
    ], { valor: 'morador', classe: 'lista' }),
    campoUnidade,
    erroForm(),
    h('button', { class: 'botao primario grande bloco', type: 'submit' }, 'Pedir para entrar'));
  form.addEventListener('change', () => {
    campoUnidade.hidden = form.elements.vinculo.value !== 'morador';
  });

  aoEnviar(form, async (dados) => {
    let corpo;
    if (dados.vinculo === 'funcionario') {
      corpo = { funcionario: true };
    } else {
      if (!dados.unidade_id) throw new Error('Escolha sua unidade.');
      corpo = { unidade_id: Number(dados.unidade_id) };
    }
    await post(`/api/convites/${encodeURIComponent(codigo)}/entrar`, corpo);
    await carregarUsuario();
    toast('Pedido enviado ao síndico!');
    navegar('condominios');
  });

  return h('div', { class: 'pagina estreita' },
    cabecalho(condominio.nome, { subtitulo: condominio.endereco || 'Você recebeu um convite', voltar: { rota: 'condominios' } }),
    form,
    h('p', { class: 'centro dica' }, 'O síndico confirma antes de liberar seu acesso.'));
}
