"""Envio de e-mail pelo Resend (resend.com), pela API HTTP, sem bibliotecas externas.

Configuração (variáveis de ambiente):
  RESEND_API_KEY   chave da conta no Resend
  EMAIL_REMETENTE  ex.: "Meu Prédio <nao-responda@seudominio.com.br>" (domínio verificado no Resend)
Sem a chave (no computador), o e-mail não sai: o conteúdo aparece na janela do servidor.
"""
import json
import os
import sys
import urllib.error
import urllib.request

REMETENTE_PADRAO = "Meu Prédio <onboarding@resend.dev>"  # o endereço de teste do Resend


class ErroEnvio(Exception):
    pass


def enviar(para, assunto, texto):
    chave = os.environ.get("RESEND_API_KEY")
    if not chave:
        print(f"\n[e-mail não enviado: falta RESEND_API_KEY]\nPara: {para}\nAssunto: {assunto}\n{texto}\n",
              file=sys.stderr, flush=True)
        return
    corpo = {"from": os.environ.get("EMAIL_REMETENTE") or REMETENTE_PADRAO, "to": [para],
             "subject": assunto, "text": texto}
    pedido = urllib.request.Request(
        "https://api.resend.com/emails", data=json.dumps(corpo).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {chave}"},
    )
    try:
        with urllib.request.urlopen(pedido, timeout=10):
            pass
    except urllib.error.HTTPError as erro:
        raise ErroEnvio(f"Resend respondeu {erro.code}: {erro.read()[:300]!r}") from None
    except (urllib.error.URLError, TimeoutError) as erro:
        raise ErroEnvio(f"Sem conexão com o Resend: {erro}") from None
