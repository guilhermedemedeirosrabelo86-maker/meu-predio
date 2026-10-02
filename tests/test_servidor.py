"""Testes do servidor HTTP: conexão reaproveitada, cache dos arquivos e compactação."""
import gzip
import http.client
import json

from tests.base import BaseApi


class TesteServidor(BaseApi):
    def conexao(self):
        return http.client.HTTPConnection("127.0.0.1", self.servidor.server_address[1], timeout=5)

    def test_varios_pedidos_na_mesma_conexao(self):
        conexao = self.conexao()
        for caminho in ("/", "/css/app.css", "/api/eu", "/js/app.js"):
            conexao.request("GET", caminho)
            resposta = conexao.getresponse()
            resposta.read()
            self.assertIn(resposta.status, (200, 401))
        conexao.close()

    def test_arquivo_sem_mudanca_responde_304(self):
        conexao = self.conexao()
        conexao.request("GET", "/js/ui.js")
        resposta = conexao.getresponse()
        resposta.read()
        etag = resposta.getheader("ETag")
        self.assertTrue(etag)
        conexao.request("GET", "/js/ui.js", headers={"If-None-Match": etag})
        resposta = conexao.getresponse()
        self.assertEqual((resposta.status, resposta.read()), (304, b""))
        conexao.close()

    def test_texto_vai_compactado(self):
        conexao = self.conexao()
        conexao.request("GET", "/css/app.css", headers={"Accept-Encoding": "gzip, br"})
        resposta = conexao.getresponse()
        corpo = resposta.read()
        self.assertEqual(resposta.getheader("Content-Encoding"), "gzip")
        self.assertIn(b":root", gzip.decompress(corpo))
        conexao.request("GET", "/icone-192.png", headers={"Accept-Encoding": "gzip"})
        resposta = conexao.getresponse()
        resposta.read()
        self.assertIsNone(resposta.getheader("Content-Encoding"))  # imagem já é compactada
        conexao.close()

    def test_erro_com_corpo_nao_lido_nao_atrapalha_o_proximo_pedido(self):
        conexao = self.conexao()
        corpo = json.dumps({"x": 1})
        conexao.request("POST", "/api/rota-que-nao-existe", body=corpo, headers={"Content-Type": "application/json"})
        resposta = conexao.getresponse()
        resposta.read()
        self.assertEqual(resposta.status, 404)
        conexao.request("GET", "/api/eu")  # http.client reconecta se o servidor fechou
        resposta = conexao.getresponse()
        resposta.read()
        self.assertEqual(resposta.status, 401)
        conexao.close()
