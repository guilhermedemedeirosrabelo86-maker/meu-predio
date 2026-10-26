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
    campoSenha('Senha', { name: 'senha', autocomplete: 'current-password', required: true, placeholder: '••••••••' },
      h('small', { class: 'dica' }, h('a', { href: '#/esqueci' }, 'Esqueci minha senha'))),
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
    h('label', { class: 'interruptor' },
      h('input', { type: 'checkbox', name: 'aceito_termos', required: true }),
      h('span', { class: 'pequeno' }, 'Li e aceito os ',
        h('a', { href: '#/termos', target: '_blank', rel: 'noopener' }, 'termos de uso'), ' e a ',
        h('a', { href: '#/privacidade', target: '_blank', rel: 'noopener' }, 'política de privacidade'), '.')),
    erroForm(),
    h('button', { class: 'botao primario grande bloco', type: 'submit' }, 'Criar conta'));
  aoEnviar(form, async (dados) => {
    await post('/api/auth/cadastro', { ...dados, aceito_termos: dados.aceito_termos === 'on' });
    await entrouNaConta();
  });
  return telaDeAcesso('Criar sua conta', 'Leva menos de um minuto.', form,
    ['Já tem conta? ', h('a', { href: '#/entrar' }, 'Entrar')]);
}

export function telaEsqueci() {
  const form = h('form', { class: 'pilha' },
    campo('E-mail', h('input', { name: 'email', type: 'email', autocomplete: 'email', required: true, placeholder: 'voce@email.com' })),
    erroForm(),
    h('button', { class: 'botao primario grande bloco', type: 'submit' }, 'Enviar link'));
  aoEnviar(form, async (dados) => {
    const { mensagem } = await post('/api/auth/esqueci', dados);
    form.replaceChildren(h('p', {}, mensagem), h('p', { class: 'mudo' }, 'Confira também a caixa de spam.'));
  });
  return telaDeAcesso('Esqueci minha senha', 'Mandamos um link para o seu e-mail para você criar uma senha nova.', form,
    ['Lembrou? ', h('a', { href: '#/entrar' }, 'Entrar')]);
}

export function telaNovaSenha({ token }) {
  const form = h('form', { class: 'pilha' },
    campoSenha('Nova senha', { name: 'senha', autocomplete: 'new-password', required: true, minlength: 8, placeholder: 'Mínimo de 8 caracteres' }),
    erroForm(),
    h('button', { class: 'botao primario grande bloco', type: 'submit' }, 'Salvar e entrar'));
  aoEnviar(form, async (dados) => {
    await post('/api/auth/nova-senha', { ...dados, token });
    await entrouNaConta();
  });
  return telaDeAcesso('Criar nova senha', 'Por segurança, você sai da conta nos outros aparelhos.', form,
    [h('a', { href: '#/esqueci' }, 'Pedir outro link')]);
}
