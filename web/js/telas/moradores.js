import { del, get, patch, post } from '../api.js';
import { carregarUsuario, estado, recarregar } from '../estado.js';
import {
  aoEnviar, avatar, cabecalho, comErro, confirmar, copiar, erroForm, formatarPlaca, h, icone, linkTelefone,
  pill, placa, secao, toast,
} from '../ui.js';

/** Painel do síndico: convite, pedidos pendentes, equipe e cadastro de unidades. */
export async function telaMoradores() {
  const cid = estado.membro.condominio_id;
  const [condominio, cadastro] = await Promise.all([
    get(`/api/condominios/${cid}`),
    get(`/api/condominios/${cid}/cadastro`),
  ]);
  const ocupadas = cadastro.unidades.filter((u) => u.moradores.length).length;
  const lateral = [
    cadastro.pendentes.length > 0 && cartaoPendentes(cid, cadastro.pendentes),
    cadastro.sem_unidade.length > 0 && h('section', { class: 'cartao' },
      h('h2', {}, 'Equipe e sem unidade'),
      cadastro.sem_unidade.map((m) => blocoMorador(cid, m))),
  ].filter(Boolean);
  return h('div', { class: 'pagina' },
    cabecalho('Moradores', { subtitulo: `${ocupadas} de ${cadastro.unidades.length} unidades com moradores no app` }),
    lateral.length
      ? h('div', { class: 'colunas' }, cartaoConvite(cid, condominio), h('div', { class: 'pilha' }, lateral))
      : cartaoConvite(cid, condominio),
    secaoUnidades(cid, cadastro));
}

function cartaoConvite(cid, condominio) {
  const link = `${location.origin}/#/convite/${condominio.codigo_convite}`;
  const mensagem = `Olá! Entre no app do ${condominio.nome} para receber avisos, reservar o salão e liberar visitas: ${link} `
    + `(código ${condominio.codigo_convite})`;
  const renovar = comErro(async () => {
    if (!await confirmar('O código atual deixa de funcionar. Quem já entrou continua com acesso.', { titulo: 'Gerar novo código?', botao: 'Gerar novo' })) return;
    await post(`/api/condominios/${cid}/convite`);
    toast('Novo código gerado.');
    recarregar();
  });
  return h('section', { class: 'cartao convite' },
    h('div', { class: 'pilha-curta' },
      h('h2', {}, 'Convide os moradores'),
      h('p', {}, 'Mande o link no grupo do prédio. Cada um escolhe a unidade e você aprova.')),
    h('div', { class: 'codigo-grande', 'aria-label': 'Código de convite' }, condominio.codigo_convite),
    h('div', { class: 'acoes dividir' },
      h('a', { class: 'botao', href: `https://wa.me/?text=${encodeURIComponent(mensagem)}`, target: '_blank', rel: 'noopener' },
        icone('conversa'), 'WhatsApp'),
      h('button', { class: 'botao fantasma', onclick: () => copiar(link) }, icone('copiar'), 'Copiar link')),
    h('button', { class: 'botao fantasma pequeno', onclick: renovar }, icone('trocar'), 'Gerar novo código'));
}

function cartaoPendentes(cid, pendentes) {
  return h('section', { class: 'cartao alerta' },
    h('h2', {}, pendentes.length === 1 ? '1 pedido para entrar' : `${pendentes.length} pedidos para entrar`),
    pendentes.map((p) => {
      const aprovar = comErro(async () => {
        await patch(`/api/condominios/${cid}/membros/${p.id}`, { status: 'ativo' });
        toast(`${p.nome} aprovado.`);
        recarregar();
      });
      const recusar = comErro(async () => {
        if (!await confirmar(`${p.nome} não terá acesso ao condomínio.`, { titulo: 'Recusar pedido?', botao: 'Recusar', perigo: true })) return;
        await del(`/api/condominios/${cid}/membros/${p.id}`);
        recarregar();
      });
      return h('div', { class: 'morador' },
        avatar(p.nome),
        h('div', { class: 'morador-texto' },
          h('div', { class: 'morador-nome' }, p.nome,
            p.papel === 'portaria' ? pill('Funcionário', 'azul') : p.unidade && pill(`Unidade ${p.unidade}`, 'roxo')),
          h('span', { class: 'item-sub' }, [p.email, p.telefone].filter(Boolean).join(' · ')),
          h('div', { class: 'acoes' },
            h('button', { class: 'botao primario pequeno', onclick: aprovar }, icone('check'), 'Aprovar'),
            h('button', { class: 'botao fantasma pequeno perigo', onclick: recusar }, 'Recusar'))));
    }));
}

function secaoUnidades(cid, cadastro) {
  const busca = h('input', { type: 'search', placeholder: 'Buscar unidade, nome ou placa', 'aria-label': 'Buscar' });
  const cartoes = cadastro.unidades.map((u) => ({
    el: cartaoUnidade(cid, u),
    texto: [u.identificador, ...u.moradores.map((m) => m.nome), ...u.veiculos.map((v) => v.placa)].join(' ').toLowerCase(),
  }));
  busca.addEventListener('input', () => {
    const termo = busca.value.trim().toLowerCase().replace(/-/g, '');
    for (const c of cartoes) c.el.hidden = Boolean(termo) && !c.texto.includes(termo);
  });

  return secao('Unidades', h('div', { class: 'pilha' },
    cadastro.unidades.length > 3 && busca,
    h('div', { class: 'grade' }, cartoes.map((c) => c.el), formNovaUnidade(cid))));
}

function cartaoUnidade(cid, unidade) {
  const vazia = unidade.moradores.length === 0;
  const excluir = comErro(async () => {
    if (!await confirmar(`A unidade ${unidade.identificador} será removida da lista.`, { titulo: 'Excluir unidade?', botao: 'Excluir', perigo: true })) return;
    await del(`/api/condominios/${cid}/unidades/${unidade.id}`);
    recarregar();
  });
  return h('article', { class: 'cartao compacto' },
    h('div', { class: 'unidade-cabecalho' },
      h('h3', {}, placa(unidade.identificador)),
      vazia
        ? pill('Ninguém no app', '', 'sem-ponto')
        : pill(unidade.moradores.length === 1 ? '1 morador' : `${unidade.moradores.length} moradores`, 'verde')),
    unidade.moradores.map((m) => blocoMorador(cid, m)),
    unidade.veiculos.length > 0 && h('div', { class: 'veiculos' },
      unidade.veiculos.map((v) => h('span', { class: 'placa' }, formatarPlaca(v.placa),
        (v.modelo || v.cor) && h('small', {}, [v.modelo, v.cor].filter(Boolean).join(' '))))),
    vazia && unidade.veiculos.length === 0 && h('details', {},
      h('summary', {}, 'Opções'),
      h('div', { class: 'acoes' }, h('button', { class: 'botao fantasma pequeno perigo', onclick: excluir }, icone('lixo'), 'Excluir unidade'))));
}

function blocoMorador(cid, morador) {
  const souEu = morador.usuario_id === estado.usuario.id;
  const { papel } = morador;
  const mudarPapel = (novo, texto) => comErro(async () => {
    if (!await confirmar(texto, { botao: 'Confirmar' })) return;
    await patch(`/api/condominios/${cid}/membros/${morador.id}`, { papel: novo });
    await carregarUsuario(); // se o síndico tirou o próprio cargo, a navegação muda
    recarregar();
  });
  const remover = comErro(async () => {
    if (!await confirmar(`${morador.nome} perderá o acesso ao condomínio.`, { titulo: 'Remover do condomínio?', botao: 'Remover', perigo: true })) return;
    await del(`/api/condominios/${cid}/membros/${morador.id}`);
    recarregar();
  });

  return h('div', { class: 'morador' },
    avatar(morador.nome),
    h('div', { class: 'morador-texto' },
      h('div', { class: 'morador-nome' },
        morador.nome,
        papel === 'sindico' && pill('Síndico', 'roxo', 'sem-ponto'),
        papel === 'portaria' && pill('Portaria', 'azul', 'sem-ponto'),
        souEu && h('span', { class: 'fraco pequeno' }, 'você')),
      h('div', { class: 'contatos' },
        morador.telefone && h('a', { href: linkTelefone(morador.telefone) }, icone('telefone'), morador.telefone),
        h('a', { href: `mailto:${morador.email}` }, icone('email'), morador.email)),
      morador.contatos?.length > 0 && h('details', {},
        h('summary', {}, `Contatos de emergência (${morador.contatos.length})`),
        h('ul', { class: 'lista-simples' }, morador.contatos.map((c) => h('li', {},
          `${c.nome}${c.parentesco ? ` (${c.parentesco})` : ''}: `,
          h('a', { href: linkTelefone(c.telefone) }, c.telefone))))),
      h('details', {},
        h('summary', {}, 'Opções'),
        h('div', { class: 'acoes' },
          papel === 'morador' && h('button', {
            class: 'botao fantasma pequeno',
            onclick: mudarPapel('sindico', `${morador.nome} poderá publicar avisos, aprovar reservas e gerenciar moradores.`),
          }, 'Tornar síndico'),
          papel === 'sindico' && h('button', {
            class: 'botao fantasma pequeno',
            onclick: mudarPapel('morador', `${morador.nome} deixará de ser síndico.`),
          }, 'Tirar da função de síndico'),
          !souEu && h('button', { class: 'botao fantasma pequeno perigo', onclick: remover }, 'Remover')))));
}

function formNovaUnidade(cid) {
  const form = h('form', { class: 'cartao compacto' },
    h('h3', {}, 'Adicionar unidade'),
    h('div', { class: 'linha' },
      h('div', { class: 'campo' },
        h('input', { name: 'identificador', required: true, maxlength: 30, placeholder: 'Ex.: 301 ou Casa 5', 'aria-label': 'Nova unidade' })),
      h('button', { class: 'botao tonal', type: 'submit' }, icone('mais'), 'Adicionar')),
    erroForm());
  aoEnviar(form, async (dados) => {
    await post(`/api/condominios/${cid}/unidades`, dados);
    toast('Unidade adicionada.');
    recarregar();
  });
  return form;
}
