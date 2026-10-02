import { estado } from '../estado.js';
import { avatar, cabecalho, comErro, h, icone, item, NOMES_PAPEL, secao, tile } from '../ui.js';
import { sairDaConta } from './perfil.js';

/** Todos os módulos e opções da conta (no celular, o que não cabe na barra inferior). */
export function telaMenu() {
  const membro = estado.membro;
  const papel = membro.papel;
  const modulos = [
    // [rota, ícone, cor, título, descrição]
    papel !== 'portaria' && ['inicio', 'inicio', 'unidade', 'Início', 'Resumo do condomínio'],
    ['avisos', 'avisos', 'avisos', 'Avisos', 'Comunicados do síndico'],
    ['reservas', 'reservas', 'reservas', 'Reservas', 'Salão, churrasqueira e outras áreas'],
    ['ocorrencias', 'ocorrencias', 'ocorrencias', 'Ocorrências', 'Barulho, vazamento, garagem…'],
    papel !== 'portaria' && ['visitas', 'visitas', 'visitas', 'Visitantes', 'Libere a entrada por QR Code'],
    papel !== 'morador' && ['portaria', 'portaria', 'portaria', 'Portaria', 'Validar visitantes e registrar entradas'],
    papel !== 'portaria' && ['contas', 'contas', 'contas', 'Prestação de contas', 'Entradas, saídas e saldo em caixa'],
    papel === 'sindico' && ['contas/taxas', 'unidade', 'contas', 'Taxa condominial', 'Quem já pagou em cada mês'],
    papel === 'morador' && membro.unidade_id && ['contas/taxas', 'unidade', 'contas', 'Minha taxa', 'Situação da taxa da sua unidade'],
    papel === 'sindico' && ['moradores', 'moradores', 'moradores', 'Moradores', 'Convites, unidades e cadastro'],
    papel === 'sindico' && ['reservas/areas', 'editar', 'reservas', 'Áreas comuns', 'Regras e aprovação das reservas'],
    membro.unidade_id && ['unidade', 'carro', 'unidade', 'Minha unidade', 'Veículos cadastrados'],
  ].filter(Boolean);

  return h('div', { class: 'pagina estreita' },
    cabecalho('Menu'),
    h('a', { class: 'cartao', href: '#/perfil' },
      h('div', { class: 'perfil-topo' },
        avatar(estado.usuario.nome, 'grande'),
        h('div', { class: 'item-texto' },
          h('h2', {}, estado.usuario.nome),
          h('span', { class: 'mudo pequeno' }, [NOMES_PAPEL[papel], membro.unidade && `Unidade ${membro.unidade}`].filter(Boolean).join(' · ')),
          h('span', { class: 'pequeno' }, 'Ver e editar perfil')),
        icone('seta', 'icone fraco'))),
    secao('Condomínio', h('div', { class: 'cartao lista' },
      modulos.map(([rota, nomeIcone, cor, titulo, sub]) => item({ inicio: tile(nomeIcone, cor), titulo, sub, href: `#/${rota}` })))),
    secao('Conta', h('div', { class: 'cartao lista' },
      item({ inicio: tile('trocar', 'neutra'), titulo: 'Trocar ou adicionar condomínio', href: '#/condominios' }),
      item({ inicio: tile('sair', 'ocorrencias'), titulo: 'Sair da conta', onclick: comErro(sairDaConta), seta: false }))));
}
