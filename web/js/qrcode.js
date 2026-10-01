// Gerador de QR Code (ISO/IEC 18004) sem dependências: modo byte, correção de erro nível M.
// Baseado na estrutura do "QR Code generator library" de Project Nayuki (licença MIT).

// Índice = versão (1..40). Nível M.
const ECC_POR_BLOCO = [-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28,
  28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28];
const BLOCOS = [-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25,
  26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49];
const FORMATO_M = 0; // bits do nível M no campo de formato

const bit = (valor, i) => ((valor >>> i) & 1) !== 0;

function modulosDeDados(versao) {
  let total = (16 * versao + 128) * versao + 64;
  if (versao >= 2) {
    const alinhamentos = Math.floor(versao / 7) + 2;
    total -= (25 * alinhamentos - 10) * alinhamentos - 55;
    if (versao >= 7) total -= 36;
  }
  return total;
}

const palavrasDeDados = (v) => Math.floor(modulosDeDados(v) / 8) - ECC_POR_BLOCO[v] * BLOCOS[v];

// --- Reed-Solomon sobre GF(256), polinômio 0x11D ---

function multiplicar(x, y) {
  let z = 0;
  for (let i = 7; i >= 0; i--) {
    z = (z << 1) ^ ((z >>> 7) * 0x11d);
    z ^= ((y >>> i) & 1) * x;
  }
  return z;
}

function divisorRS(grau) {
  const resultado = new Array(grau).fill(0);
  resultado[grau - 1] = 1;
  let raiz = 1;
  for (let i = 0; i < grau; i++) {
    for (let j = 0; j < resultado.length; j++) {
      resultado[j] = multiplicar(resultado[j], raiz);
      if (j + 1 < resultado.length) resultado[j] ^= resultado[j + 1];
    }
    raiz = multiplicar(raiz, 0x02);
  }
  return resultado;
}

function restoRS(dados, divisor) {
  const resto = divisor.map(() => 0);
  for (const b of dados) {
    const fator = b ^ resto.shift();
    resto.push(0);
    divisor.forEach((coef, i) => { resto[i] ^= multiplicar(coef, fator); });
  }
  return resto;
}

// --- Codificação dos dados ---

function codificar(bytes, versao) {
  const bits = [];
  const anexar = (valor, n) => { for (let i = n - 1; i >= 0; i--) bits.push((valor >>> i) & 1); };
  anexar(0b0100, 4); // modo byte
  anexar(bytes.length, versao <= 9 ? 8 : 16);
  bytes.forEach((b) => anexar(b, 8));
  const capacidade = palavrasDeDados(versao) * 8;
  anexar(0, Math.min(4, capacidade - bits.length));
  anexar(0, (8 - (bits.length % 8)) % 8);
  for (let enchimento = 0xec; bits.length < capacidade; enchimento ^= 0xec ^ 0x11) anexar(enchimento, 8);

  const palavras = [];
  for (let i = 0; i < bits.length; i += 8) palavras.push(bits.slice(i, i + 8).reduce((a, b) => (a << 1) | b, 0));
  return palavras;
}

function intercalarComCorrecao(dados, versao) {
  const numBlocos = BLOCOS[versao];
  const eccPorBloco = ECC_POR_BLOCO[versao];
  const totalPalavras = Math.floor(modulosDeDados(versao) / 8);
  const blocosCurtos = numBlocos - (totalPalavras % numBlocos);
  const tamanhoCurto = Math.floor(totalPalavras / numBlocos);
  const divisor = divisorRS(eccPorBloco);

  const blocos = [];
  for (let i = 0, k = 0; i < numBlocos; i++) {
    const parte = dados.slice(k, k + tamanhoCurto - eccPorBloco + (i < blocosCurtos ? 0 : 1));
    k += parte.length;
    const ecc = restoRS(parte, divisor);
    if (i < blocosCurtos) parte.push(0); // posição vazia para alinhar com os blocos longos
    blocos.push(parte.concat(ecc));
  }
  const resultado = [];
  for (let i = 0; i < blocos[0].length; i++) {
    blocos.forEach((bloco, j) => {
      if (i !== tamanhoCurto - eccPorBloco || j >= blocosCurtos) resultado.push(bloco[i]);
    });
  }
  return resultado;
}

// --- Montagem da matriz ---

function posicoesAlinhamento(versao, tamanho) {
  if (versao === 1) return [];
  const quantidade = Math.floor(versao / 7) + 2;
  const passo = versao === 32 ? 26 : Math.ceil((versao * 4 + 4) / (quantidade * 2 - 2)) * 2;
  const posicoes = [6];
  for (let p = tamanho - 7; posicoes.length < quantidade; p -= passo) posicoes.splice(1, 0, p);
  return posicoes;
}

class Matriz {
  constructor(versao) {
    this.versao = versao;
    this.tamanho = versao * 4 + 17;
    this.escuro = Array.from({ length: this.tamanho }, () => new Array(this.tamanho).fill(false));
    this.fixo = Array.from({ length: this.tamanho }, () => new Array(this.tamanho).fill(false));
  }

  definir(x, y, escuro) {
    this.escuro[y][x] = escuro;
    this.fixo[y][x] = true;
  }

  desenharPadroes() {
    const t = this.tamanho;
    for (let i = 0; i < t; i++) {
      this.definir(6, i, i % 2 === 0);
      this.definir(i, 6, i % 2 === 0);
    }
    for (const [x, y] of [[3, 3], [t - 4, 3], [3, t - 4]]) {
      for (let dy = -4; dy <= 4; dy++) {
        for (let dx = -4; dx <= 4; dx++) {
          const xx = x + dx;
          const yy = y + dy;
          const distancia = Math.max(Math.abs(dx), Math.abs(dy));
          if (xx >= 0 && xx < t && yy >= 0 && yy < t) this.definir(xx, yy, distancia !== 2 && distancia !== 4);
        }
      }
    }
    const posicoes = posicoesAlinhamento(this.versao, t);
    const n = posicoes.length;
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        if ((i === 0 && j === 0) || (i === 0 && j === n - 1) || (i === n - 1 && j === 0)) continue;
        for (let dy = -2; dy <= 2; dy++) {
          for (let dx = -2; dx <= 2; dx++) {
            this.definir(posicoes[i] + dx, posicoes[j] + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
          }
        }
      }
    }
    this.desenharFormato(0); // reserva a área; o valor certo entra depois da máscara
    this.desenharVersao();
  }

  desenharFormato(mascara) {
    const dados = (FORMATO_M << 3) | mascara;
    let resto = dados;
    for (let i = 0; i < 10; i++) resto = (resto << 1) ^ ((resto >>> 9) * 0x537);
    const bits = ((dados << 10) | resto) ^ 0x5412;
    const t = this.tamanho;
    for (let i = 0; i <= 5; i++) this.definir(8, i, bit(bits, i));
    this.definir(8, 7, bit(bits, 6));
    this.definir(8, 8, bit(bits, 7));
    this.definir(7, 8, bit(bits, 8));
    for (let i = 9; i < 15; i++) this.definir(14 - i, 8, bit(bits, i));
    for (let i = 0; i < 8; i++) this.definir(t - 1 - i, 8, bit(bits, i));
    for (let i = 8; i < 15; i++) this.definir(8, t - 15 + i, bit(bits, i));
    this.definir(8, t - 8, true); // módulo escuro fixo
  }

  desenharVersao() {
    if (this.versao < 7) return;
    let resto = this.versao;
    for (let i = 0; i < 12; i++) resto = (resto << 1) ^ ((resto >>> 11) * 0x1f25);
    const bits = (this.versao << 12) | resto;
    for (let i = 0; i < 18; i++) {
      const a = this.tamanho - 11 + (i % 3);
      const b = Math.floor(i / 3);
      this.definir(a, b, bit(bits, i));
      this.definir(b, a, bit(bits, i));
    }
  }

  desenharDados(palavras) {
    const t = this.tamanho;
    let i = 0;
    for (let direita = t - 1; direita >= 1; direita -= 2) {
      if (direita === 6) direita = 5;
      for (let vertical = 0; vertical < t; vertical++) {
        for (let j = 0; j < 2; j++) {
          const x = direita - j;
          const subindo = ((direita + 1) & 2) === 0;
          const y = subindo ? t - 1 - vertical : vertical;
          if (!this.fixo[y][x] && i < palavras.length * 8) {
            this.escuro[y][x] = bit(palavras[i >>> 3], 7 - (i & 7));
            i++;
          }
        }
      }
    }
  }

  aplicarMascara(mascara) {
    const regra = [
      (x, y) => (x + y) % 2 === 0,
      (x, y) => y % 2 === 0,
      (x) => x % 3 === 0,
      (x, y) => (x + y) % 3 === 0,
      (x, y) => (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0,
      (x, y) => ((x * y) % 2) + ((x * y) % 3) === 0,
      (x, y) => (((x * y) % 2) + ((x * y) % 3)) % 2 === 0,
      (x, y) => (((x + y) % 2) + ((x * y) % 3)) % 2 === 0,
    ][mascara];
    for (let y = 0; y < this.tamanho; y++) {
      for (let x = 0; x < this.tamanho; x++) {
        if (!this.fixo[y][x] && regra(x, y)) this.escuro[y][x] = !this.escuro[y][x];
      }
    }
  }

  penalidade() {
    const t = this.tamanho;
    const m = this.escuro;
    let pontos = 0;
    const linhas = [...m, ...m[0].map((_, x) => m.map((linha) => linha[x]))]; // linhas e colunas
    const padraoA = [1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0];
    const padraoB = [0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1];
    for (const linha of linhas) {
      let sequencia = 1;
      for (let i = 1; i <= t; i++) {
        if (i < t && linha[i] === linha[i - 1]) {
          sequencia++;
        } else {
          if (sequencia >= 5) pontos += 3 + (sequencia - 5);
          sequencia = 1;
        }
      }
      for (let i = 0; i + 11 <= t; i++) {
        const trecho = linha.slice(i, i + 11).map(Number);
        if (padraoA.every((v, k) => v === trecho[k]) || padraoB.every((v, k) => v === trecho[k])) pontos += 40;
      }
    }
    let escuros = 0;
    for (let y = 0; y < t; y++) {
      for (let x = 0; x < t; x++) {
        if (m[y][x]) escuros++;
        if (x < t - 1 && y < t - 1 && m[y][x] === m[y][x + 1] && m[y][x] === m[y + 1][x] && m[y][x] === m[y + 1][x + 1]) {
          pontos += 3;
        }
      }
    }
    pontos += Math.floor(Math.abs((escuros * 100) / (t * t) - 50) / 5) * 10;
    return pontos;
  }
}

/** Matriz de módulos (true = escuro). `mascara` fixa só serve para testes. */
export function gerarQR(texto, { mascara = null } = {}) {
  const bytes = Array.from(new TextEncoder().encode(texto));
  let versao = 1;
  while (versao <= 40 && 4 + (versao <= 9 ? 8 : 16) + bytes.length * 8 > palavrasDeDados(versao) * 8) versao++;
  if (versao > 40) throw new Error('Texto longo demais para um QR Code.');

  const palavras = intercalarComCorrecao(codificar(bytes, versao), versao);
  const base = new Matriz(versao);
  base.desenharPadroes();
  base.desenharDados(palavras);

  let melhor = null;
  for (const m of mascara === null ? [0, 1, 2, 3, 4, 5, 6, 7] : [mascara]) {
    const tentativa = new Matriz(versao);
    tentativa.escuro = base.escuro.map((l) => [...l]);
    tentativa.fixo = base.fixo;
    tentativa.aplicarMascara(m);
    tentativa.desenharFormato(m);
    const pontos = mascara === null ? tentativa.penalidade() : 0;
    if (!melhor || pontos < melhor.pontos) melhor = { matriz: tentativa, pontos, mascara: m };
  }
  return { versao, mascara: melhor.mascara, modulos: melhor.matriz.escuro };
}

/** SVG nítido em qualquer tamanho, com a margem branca obrigatória de 4 módulos. */
export function qrSvg(texto, { rotulo = 'QR Code' } = {}) {
  const { modulos } = gerarQR(texto);
  const margem = 4;
  const lado = modulos.length + margem * 2;
  let caminho = '';
  modulos.forEach((linha, y) => linha.forEach((escuro, x) => {
    if (escuro) caminho += `M${x + margem} ${y + margem}h1v1h-1z`;
  }));
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', `0 0 ${lado} ${lado}`);
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', rotulo);
  svg.setAttribute('shape-rendering', 'crispEdges');
  const fundo = document.createElementNS(ns, 'rect');
  fundo.setAttribute('width', lado);
  fundo.setAttribute('height', lado);
  fundo.setAttribute('fill', '#fff');
  const path = document.createElementNS(ns, 'path');
  path.setAttribute('d', caminho);
  path.setAttribute('fill', '#000');
  svg.append(fundo, path);
  return svg;
}

/** Imagem PNG do QR Code (para compartilhar), com título opcional embaixo. */
export async function qrPng(texto, { escala = 10, legenda = '' } = {}) {
  const { modulos } = gerarQR(texto);
  const margem = 4;
  const lado = (modulos.length + margem * 2) * escala;
  const alturaLegenda = legenda ? escala * 6 : 0;
  const canvas = document.createElement('canvas');
  canvas.width = lado;
  canvas.height = lado + alturaLegenda;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#000';
  modulos.forEach((linha, y) => linha.forEach((escuro, x) => {
    if (escuro) ctx.fillRect((x + margem) * escala, (y + margem) * escala, escala, escala);
  }));
  if (legenda) {
    ctx.font = `600 ${escala * 2.4}px system-ui, sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillText(legenda, lado / 2, lado + alturaLegenda / 2, lado - escala * 4);
  }
  return new Promise((resolver) => canvas.toBlob(resolver, 'image/png'));
}
