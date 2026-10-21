import { estado } from '../estado.js';
import { avatar, cabecalho, comErro, h, icone, item, NOMES_PAPEL, secao, tile } from '../ui.js';
import { sairDaConta } from './perfil.js';

/** Todos os módulos e opções da conta (no celular, o que não cabe na barra inferior). */
export function telaMenu() {
  const membro = estado.membro;
  const papel = membro.papel;
  // Mesmos nomes, ícones e ordem da grade do Início (o Início em si já está na barra de baixo).
  const sindico = papel === 'sindico';
  const modulos = [
    // [rota, ícone, cor, título, descrição]
    ['avisos', 'avisos', 'avisos', 'Avisos', 'Comunicados do síndico'],
    sindico && ['contas', 'contas', 'contas', 'Contas', 'Prestação de contas: entradas, saídas e saldo'],
    sindico && ['moradores', 'moradores', 'moradores', 'Moradores', 'Convites, unidades e cadastro'],
    ['reservas', 'reservas', 'reservas', 'Reservas', 'Salão, churrasqueira e outras áreas'],
    sindico && ['reservas/areas', 'editar', 'reservas', 'Áreas comuns', 'Regras e aprovação das reservas'],
    papel !== 'portaria' && ['visitas', 'visitas', 'visitas', 'Visitas', 'Libere a entrada por QR Code'],
    ['ocorrencias', 'ocorrencias', 'ocorrencias', 'Ocorrências', 'Barulho, vazamento, garagem…'],
    papel !== 'morador' && ['portaria', 'portaria', 'portaria', 'Portaria', 'Validar visitantes e registrar entradas'],
    sindico && ['contas/taxas', 'recibo', 'contas', 'Taxas', 'Quem já pagou a taxa em cada mês'],
    papel === 'morador' && ['contas', 'contas', 'contas', 'Contas', 'Prestação de contas: entradas, saídas e saldo'],
    papel === 'morador' && membro.unidade_id && ['contas/taxas', 'recibo', 'contas', 'Minha taxa', 'Situação da taxa da sua unidade'],
    ['encomendas', 'pacote', 'neutra', 'Encomendas', papel === 'morador' ? 'O que chegou para você na portaria' : 'Registrar chegada e entrega de pacotes'],
    papel !== 'portaria' && ['enquetes', 'enquetes', 'neutra', 'Enquetes', sindico ? 'Pergunte e veja o resultado da votação' : 'Vote nas decisões do condomínio'],
    ['telefones', 'telefones', 'neutra', 'Telefones úteis', 'Zelador, prestadores e serviços'],
    membro.unidade_id && ['unidade', 'carro', 'unidade', 'Minha unidade', 'Veículos cadastrados'],
  ].filter(Boolean);

  return h('div', { class: 'pagina estreita' },
    cabecalho('Mais'),
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
