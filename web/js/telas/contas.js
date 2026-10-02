import { del, enviarArquivo, get, patch, post } from '../api.js';
import { estado, navegar, recarregar } from '../estado.js';
import { definirMesDasTaxas, nomeMes as nomeDoMes, SITUACAO } from './taxas.js';
import {
  abrirFotos, aoEnviar, cabecalho, campo, centavosDe, comErro, confirmar, dinheiro, erroForm, formatarDia, h,
  icone, item, mascaraDinheiro, maiuscula, opcoes, pill, reduzirFoto, secao, tile, toast, vazio,
} from '../ui.js';

// [rótulo, ícone]
export const CATEGORIAS = {
  receita: {
    taxa: ['Taxa condominial', 'unidade'],
    multa: ['Multas', 'alerta'],
    aluguel: ['Aluguel de áreas', 'reservas'],
    receita_outra: ['Outras entradas', 'outro'],
  },
  despesa: {
    agua: ['Água', 'vazamento'],
    energia: ['Energia', 'energia'],
    limpeza: ['Limpeza', 'limpeza'],
    manutencao: ['Manutenção', 'manutencao'],
    seguranca: ['Segurança', 'seguranca'],
    administrativo: ['Administrativo', 'documento'],
    obras: ['Obras', 'predio'],
    despesa_outra: ['Outras saídas', 'outro'],
  },
};
const COR_TIPO = { receita: 'reservas', despesa: 'avisos' };

const categoria = (tipo, chave) => CATEGORIAS[tipo][chave] || ['Outro', 'outro'];
const urlBase = () => `/api/condominios/${estado.membro.condominio_id}/contas`;
const nomeMes = (mes, opcoesData = { month: 'long', year: 'numeric' }) => {
  const [ano, m] = mes.split('-').map(Number);
  return maiuscula(new Date(ano, m - 1, 1).toLocaleDateString('pt-BR', opcoesData));
};
function somarMeses(mes, meses) {
  const [ano, m] = mes.split('-').map(Number);
  const total = ano * 12 + (m - 1) + meses;
  return `${Math.floor(total / 12)}-${String((total % 12) + 1).padStart(2, '0')}`;
}
const diaCurto = (iso) => new Date(`${iso}T12:00:00`).toLocaleDateString('pt-BR', { day: 'numeric', month: 'short' }).replace('.', '');
const valorComSinal = (l) => `${l.tipo === 'receita' ? '+' : '−'} ${dinheiro(l.valor_centavos)}`;

let mesVisto = null; // mês aberto na tela; volta ao atual ao trocar de condomínio
let condominioVisto = null;

/** Resumo do mês, para onde foi o dinheiro, lançamentos e os últimos meses. */
export async function telaContas() {
  const cid = estado.membro.condominio_id;
  if (condominioVisto !== cid) {
    condominioVisto = cid;
    mesVisto = null;
  }
  const sindico = estado.membro.papel === 'sindico';
  const [dados, taxas] = await Promise.all([
    get(`${urlBase()}${mesVisto ? `?mes=${mesVisto}` : ''}`),
    sindico ? get(`/api/condominios/${cid}/taxas${mesVisto ? `?mes=${mesVisto}` : ''}`)
      : estado.membro.unidade_id ? get(`/api/condominios/${cid}/taxas/minha`) : null,
  ]);
  const mesAtual = dados.hoje.slice(0, 7);
  mesVisto = dados.mes;
  const { resumo } = dados;
  const resultado = resumo.entradas - resumo.saidas;

  const irPara = (mes) => () => {
    mesVisto = mes;
    recarregar();
  };

  const painel = h('section', { class: 'cartao contas-painel' },
    h('div', { class: 'calendario-topo' },
      h('button', { type: 'button', class: 'botao', onclick: irPara(somarMeses(mesVisto, -1)), 'aria-label': 'Mês anterior' }, icone('voltar')),
      h('h3', {}, nomeMes(mesVisto)),
      h('button', { type: 'button', class: 'botao', disabled: mesVisto >= mesAtual, onclick: irPara(somarMeses(mesVisto, 1)), 'aria-label': 'Próximo mês' }, icone('seta'))),
    h('div', { class: 'contas-caixa' },
      h('div', { class: 'rotulo' }, mesVisto === mesAtual ? 'Saldo em caixa' : `Saldo em caixa no fim de ${nomeMes(mesVisto, { month: 'long' }).toLowerCase()}`),
      h('div', { class: `valor${resumo.saldo_caixa < 0 ? ' negativo' : ''}` }, dinheiro(resumo.saldo_caixa))),
    h('div', { class: 'contas-totais' },
      h('div', { class: 'dado' },
        h('div', { class: 'rotulo' }, h('span', { class: 'seta-valor entrada' }, icone('entrada')), 'Entrou'),
        h('div', { class: 'valor' }, dinheiro(resumo.entradas))),
      h('div', { class: 'dado' },
        h('div', { class: 'rotulo' }, h('span', { class: 'seta-valor saida' }, icone('saida')), 'Saiu'),
        h('div', { class: 'valor' }, dinheiro(resumo.saidas)))),
    (resumo.entradas > 0 || resumo.saidas > 0) && h('p', { class: 'contas-resultado' },
      resultado >= 0
        ? ['No mês, ', h('strong', {}, `sobraram ${dinheiro(resultado)}`), '.']
        : ['No mês, saiu ', h('strong', {}, `${dinheiro(-resultado)} a mais`), ' do que entrou.']));

  const lista = dados.lancamentos.length === 0
    ? vazio({
      icone: 'contas',
      cor: 'contas',
      titulo: 'Nenhum lançamento neste mês',
      texto: sindico ? 'Lance as entradas e saídas para os moradores acompanharem.' : 'Quando o síndico lançar as contas, elas aparecem aqui.',
      acao: sindico && h('a', { class: 'botao primario', href: '#/contas/novo' }, icone('mais'), 'Lançar'),
    })
    : h('div', { class: 'cartao lista' }, dados.lancamentos.map((l) => {
      const [nome, nomeIcone] = categoria(l.tipo, l.categoria);
      return item({
        inicio: tile(nomeIcone, COR_TIPO[l.tipo]),
        titulo: l.descricao,
        sub: [`${nome} · ${diaCurto(l.data)}`,
          l.comprovante && h('span', { class: 'com-icone tem-comprovante', title: 'Tem comprovante', 'aria-label': 'Tem comprovante' }, icone('recibo'))],
        fim: h('span', { class: `valor-lancamento ${l.tipo}` }, valorComSinal(l)),
        href: `#/contas/${l.id}`,
      });
    }));

  return h('div', { class: 'pagina' },
    cabecalho('Contas', {
      subtitulo: 'Prestação de contas do condomínio',
      acao: sindico && h('a', { class: 'botao primario', href: '#/contas/novo' }, icone('mais'), 'Lançar'),
    }),
    h('div', { class: 'colunas' },
      h('div', { class: 'pilha' },
        painel,
        taxas && cartaoTaxa(taxas, sindico),
        secao('Lançamentos', lista)),
      h('div', { class: 'pilha' },
        dados.categorias.length > 0 && secao('Para onde foi o dinheiro', graficoCategorias(dados.categorias, resumo.saidas)),
        secao('Últimos meses', historico(dados.historico, mesVisto, irPara)))));
}

/** Atalho para a taxa condominial: resumo do mês (síndico) ou a situação da própria unidade (morador). */
function cartaoTaxa(taxas, sindico) {
  let sub;
  let fim = null;
  if (!taxas.config.valor_centavos) {
    if (!sindico) return null;
    sub = 'Defina o valor para acompanhar quem pagou';
  } else if (sindico) {
    const { pagas, unidades, atrasadas } = taxas.totais;
    sub = `${nomeDoMes(taxas.mes)}: ${pagas} de ${unidades} pagaram`;
    if (atrasadas) fim = pill(`${atrasadas} em atraso`, 'vermelho');
  } else {
    const atual = taxas.meses[0];
    sub = `${nomeDoMes(atual.mes)} · vence dia ${taxas.config.vencimento}`;
    fim = pill(...SITUACAO[atual.situacao]);
  }
  return h('div', { class: 'cartao lista' }, item({
    inicio: tile('unidade', 'contas'),
    titulo: sindico ? 'Taxa condominial' : 'Minha taxa',
    sub,
    fim,
    href: '#/contas/taxas',
    onclick: sindico ? () => definirMesDasTaxas(taxas.mes) : undefined,
  }));
}

/** Barras horizontais, uma cor só: o tamanho mostra o peso de cada categoria nas saídas. */
function graficoCategorias(categorias, totalSaidas) {
  const maior = categorias[0].total;
  return h('div', { class: 'cartao barras', role: 'list' }, categorias.map((c) => {
    const [nome, nomeIcone] = categoria('despesa', c.categoria);
    const parte = Math.round((c.total / totalSaidas) * 100);
    const barra = h('div', { class: 'barra' });
    barra.style.setProperty('--largura', `${Math.max(2, (c.total / maior) * 100)}%`);
    return h('div', { class: 'barra-linha', role: 'listitem', title: `${nome}: ${dinheiro(c.total)} (${parte}% das saídas)` },
      h('div', { class: 'barra-texto' },
        h('span', { class: 'barra-nome' }, icone(nomeIcone), nome),
        h('span', { class: 'barra-valor' }, dinheiro(c.total), h('span', { class: 'mudo' }, ` · ${parte}%`))),
      h('div', { class: 'barra-trilho' }, barra));
  }));
}

function historico(meses, mesAberto, irPara) {
  return h('div', { class: 'cartao lista' }, [...meses].reverse().map((m) => {
    const resultado = m.entradas - m.saidas;
    const vazioMes = m.entradas === 0 && m.saidas === 0;
    const linha = item({
      titulo: nomeMes(m.mes, { month: 'long' }),
      sub: vazioMes ? 'Sem lançamentos' : `Entrou ${dinheiro(m.entradas)} · Saiu ${dinheiro(m.saidas)}`,
      fim: !vazioMes && pill(`${resultado >= 0 ? '+' : '−'} ${dinheiro(Math.abs(resultado))}`, resultado >= 0 ? 'verde' : 'vermelho', 'sem-ponto'),
      onclick: m.mes === mesAberto ? null : irPara(m.mes),
      seta: m.mes !== mesAberto,
    });
    if (m.mes === mesAberto) linha.setAttribute('aria-current', 'true');
    return linha;
  }));
}

/** Detalhe de um lançamento, com o comprovante. */
export async function telaLancamento({ id }) {
  const sindico = estado.membro.papel === 'sindico';
  const { lancamento: l } = await get(`${urlBase()}/${id}`);
  const [nome, nomeIcone] = categoria(l.tipo, l.categoria);
  const urlComprovante = `${urlBase()}/${id}/comprovante`;

  const excluir = comErro(async () => {
    if (!await confirmar(`Excluir “${l.descricao}”? O valor deixa de contar no saldo.`, { botao: 'Excluir', perigo: true })) return;
    await del(`${urlBase()}/${id}`);
    toast('Lançamento excluído.');
    navegar('contas');
  });

  return h('div', { class: 'pagina estreita' },
    cabecalho(l.descricao, { voltar: { rota: 'contas', texto: 'Contas' } }),
    h('section', { class: 'cartao' },
      h('div', { class: 'aviso-topo' },
        tile(nomeIcone, COR_TIPO[l.tipo]),
        h('div', { class: 'item-texto' },
          h('h2', {}, nome),
          h('span', { class: 'item-sub' }, maiuscula(formatarDia(l.data)))),
        pill(l.tipo === 'receita' ? 'Entrada' : 'Saída', l.tipo === 'receita' ? 'verde' : 'amarelo')),
      h('div', { class: `valor-destaque ${l.tipo}` }, valorComSinal(l)),
      l.autor && h('p', { class: 'mudo pequeno' }, `Lançado por ${l.autor}`)),
    secao('Comprovante', l.comprovante
      ? h('div', { class: 'galeria' }, h('button', {
        type: 'button', 'aria-label': 'Ampliar comprovante', onclick: () => abrirFotos([urlComprovante]),
      }, h('img', { src: urlComprovante, alt: `Comprovante de ${l.descricao}` })))
      : h('p', { class: 'mudo' }, sindico ? 'Nenhum comprovante anexado. Você pode anexar a foto da nota em “Editar”.' : 'O síndico não anexou comprovante.')),
    sindico && h('div', { class: 'acoes dividir' },
      h('a', { class: 'botao tonal', href: `#/contas/${id}/editar` }, icone('editar'), 'Editar'),
      h('button', { class: 'botao perigo-suave', onclick: excluir }, icone('lixo'), 'Excluir')));
}

/** Novo lançamento ou edição (com `id`). */
export async function telaEditarLancamento({ id } = {}) {
  const atual = id ? (await get(`${urlBase()}/${id}`)).lancamento : null;
  const hoje = new Date();
  const hojeIso = `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, '0')}-${String(hoje.getDate()).padStart(2, '0')}`;
  let tipo = atual?.tipo || 'despesa';

  const categorias = h('div');
  const desenharCategorias = (marcada) => {
    categorias.replaceChildren(opcoes('categoria', Object.entries(CATEGORIAS[tipo]).map(([valor, [rotulo, nomeIcone]]) => ({
      valor, rotulo, icone: nomeIcone, cor: COR_TIPO[tipo],
    })), { valor: marcada }));
  };
  desenharCategorias(atual?.categoria);

  const tipos = opcoes('tipo', [
    { valor: 'receita', rotulo: 'Entrada', icone: 'entrada', cor: COR_TIPO.receita },
    { valor: 'despesa', rotulo: 'Saída', icone: 'saida', cor: COR_TIPO.despesa },
  ], { valor: tipo, classe: 'duas' });
  tipos.addEventListener('change', (e) => {
    tipo = e.target.value;
    desenharCategorias(null);
  });

  // Comprovante: no máximo um. `remover` marca o atual para apagar ao salvar.
  let novo = null; // { blob, url }
  let remover = false;
  const galeria = h('div', { class: 'galeria' });
  const seletor = h('input', { type: 'file', accept: 'image/*' });
  const desenharComprovante = () => {
    const mostrado = novo?.url || (atual?.comprovante && !remover ? `${urlBase()}/${id}/comprovante` : null);
    galeria.replaceChildren(mostrado
      ? h('div', { class: 'miniatura' },
        h('img', { src: mostrado, alt: 'Comprovante' }),
        h('button', {
          type: 'button',
          class: 'remover',
          'aria-label': 'Remover comprovante',
          onclick: () => {
            if (novo) {
              URL.revokeObjectURL(novo.url);
              novo = null;
            } else {
              remover = true;
            }
            desenharComprovante();
          },
        }, icone('x')))
      : h('label', { class: 'adicionar-foto' }, seletor, icone('camera'), 'Foto da nota'));
  };
  seletor.addEventListener('change', comErro(async () => {
    const arquivo = seletor.files[0];
    seletor.value = '';
    if (!arquivo) return;
    const blob = await reduzirFoto(arquivo, 2000, 0.85); // um pouco maior que as fotos de ocorrência: precisa ler a nota
    novo = { blob, url: URL.createObjectURL(blob) };
    desenharComprovante();
  }));
  desenharComprovante();

  const valor = mascaraDinheiro(h('input', {
    name: 'valor', inputmode: 'numeric', required: true, placeholder: '0,00', autocomplete: 'off',
    value: atual ? (atual.valor_centavos / 100).toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '',
  }));

  const form = h('form', { class: 'pagina' },
    h('section', { class: 'cartao' }, tipos, h('h2', {}, 'Categoria'), categorias),
    h('section', { class: 'cartao' },
      campo('Valor (R$)', valor),
      campo('Descrição', h('input', { name: 'descricao', required: true, maxlength: 120, value: atual?.descricao || '', placeholder: 'Ex.: Conta de luz de setembro' })),
      campo('Data', h('input', { name: 'data', type: 'date', required: true, value: atual?.data || hojeIso }))),
    h('section', { class: 'cartao' },
      h('div', { class: 'pilha-curta' }, h('h2', {}, 'Comprovante'), h('p', { class: 'dica' }, 'Opcional. A foto da nota ou do recibo fica visível para os moradores.')),
      galeria),
    erroForm(),
    h('button', { class: 'botao primario grande bloco', type: 'submit' }, icone('check'), id ? 'Salvar' : 'Lançar'));

  aoEnviar(form, async (dados) => {
    if (!dados.categoria) throw new Error('Escolha uma categoria.');
    const valorCentavos = centavosDe(dados.valor);
    if (!valorCentavos) throw new Error('Informe o valor.');
    const corpo = {
      tipo, categoria: dados.categoria, descricao: dados.descricao, valor_centavos: valorCentavos, data: dados.data,
    };
    let lid = id;
    if (id) await patch(`${urlBase()}/${id}`, corpo);
    else lid = (await post(urlBase(), corpo)).id;

    let falhou = false;
    try {
      if (novo) await enviarArquivo(`${urlBase()}/${lid}/comprovante`, novo.blob);
      else if (remover) await del(`${urlBase()}/${lid}/comprovante`);
    } catch {
      falhou = true;
    }
    if (novo) URL.revokeObjectURL(novo.url);
    mesVisto = dados.data.slice(0, 7); // ao voltar para a lista, abre o mês do lançamento
    toast(falhou ? 'Lançamento salvo, mas o comprovante não foi enviado.' : id ? 'Lançamento atualizado.' : 'Lançamento registrado!', falhou ? 'erro' : 'ok');
    if (id) navegar(`contas/${id}`);
    else navegar('contas');
  });

  return h('div', { class: 'pagina estreita' },
    cabecalho(id ? 'Editar lançamento' : 'Novo lançamento', {
      voltar: id ? { rota: `contas/${id}`, texto: 'Lançamento' } : { rota: 'contas', texto: 'Contas' },
    }),
    form);
}
