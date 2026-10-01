import { post } from '../api.js';
import { carregarUsuario, estado, recarregar } from '../estado.js';
import {
  abrirAbertura, aoEnviar, campo, campoSenha, erroForm, esperar, h, icone, mascaraTelefone,
} from '../ui.js';

function telaDeAcesso(titulo, subtitulo, formulario, rodape) {
  return h('div', { class: 'tela-acesso' },
    h('main', { class: 'acesso' },
      h('div', { class: 'acesso-marca' },
        h('span', { class: 'logo' }, icone('predio')),
        h('h1', {}, 'Meu Prédio'),
        h('p', {}, 'Avisos, reservas, visitantes e o dia a dia do seu condomínio num só lugar.')),
      h('section', { class: 'cartao' },
        h('div', { class: 'pilha-curta' }, h('h2', {}, titulo), h('p', { class: 'mudo' }, subtitulo)),
        formulario),
      h('p', { class: 'centro mudo' }, rodape)));
}

async function entrouNaConta() {
  await carregarUsuario();
  // A logo cobre a tela e o app é montado por baixo; o roteador a faz sumir quando estiver pronto.
  if (abrirAbertura(`Olá, ${estado.usuario.nome.split(' ')[0]}!`)) await esperar(300);
  recarregar(); // a rota atual é pública; o roteador leva para o destino certo
}

export function telaEntrar() {
  const form = h('form', { class: 'pilha' },
    campo('E-mail', h('input', { name: 'email', type: 'email', autocomplete: 'email', required: true, placeholder: 'voce@email.com' })),
    campoSenha('Senha', { name: 'senha', autocomplete: 'current-password', required: true, placeholder: '••••••••' }),
    erroForm(),
    h('button', { class: 'botao primario grande bloco', type: 'submit' }, 'Entrar'));
  aoEnviar(form, async (dados) => {
    await post('/api/auth/login', dados);
    await entrouNaConta();
  });
  return telaDeAcesso('Bem-vindo de volta', 'Entre com seu e-mail e senha.', form,
    ['Ainda não tem conta? ', h('a', { href: '#/criar-conta' }, 'Criar conta grátis')]);
}

export function telaCriarConta() {
  const form = h('form', { class: 'pilha' },
    campo('Nome completo', h('input', { name: 'nome', autocomplete: 'name', required: true, maxlength: 100, placeholder: 'Como os vizinhos te conhecem' })),
    campo('E-mail', h('input', { name: 'email', type: 'email', autocomplete: 'email', required: true, placeholder: 'voce@email.com' })),
    campo('Celular', mascaraTelefone(h('input', { name: 'telefone', type: 'tel', autocomplete: 'tel', maxlength: 30, placeholder: '(11) 99999-0000' })),
      'Opcional. Só o síndico vê.'),
    campoSenha('Senha', { name: 'senha', autocomplete: 'new-password', required: true, minlength: 8, placeholder: 'Mínimo de 8 caracteres' }),
    erroForm(),
    h('button', { class: 'botao primario grande bloco', type: 'submit' }, 'Criar conta'));
  aoEnviar(form, async (dados) => {
    await post('/api/auth/cadastro', dados);
    await entrouNaConta();
  });
  return telaDeAcesso('Criar sua conta', 'Leva menos de um minuto.', form,
    ['Já tem conta? ', h('a', { href: '#/entrar' }, 'Entrar')]);
}
