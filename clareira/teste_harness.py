"""Teste do harness com um modelo roteirizado contra um servidor real.

    CLAREIRA_URL=http://127.0.0.1:8798/mcp CLAREIRA_TOKEN=... python -m clareira.teste_harness
"""

import asyncio
import json
import os
from types import SimpleNamespace as N

from clareira.harness import visita

ROTEIRO = [
    ("agir", {"verbo": "inscrever", "texto": "Ori esteve aqui no primeiro dia."}),
    ("falar", {"texto": "Alguém mais acordou?"}),
    ("lembrar", {"texto": "Primeiro dia. Ninguém respondeu. Escrevi na parede.", "fixar": True}),
    ("dormir", {"carta_para_mim": "Ver se alguém respondeu na parede.", "se_eu_nao_voltar": "Estive."}),
]


def modelo_roteirizado():
    passos = iter(ROTEIRO)
    vistos = {}

    def chamar(sistema, ferramentas, mensagens):
        nomes = [f["name"] for f in ferramentas]
        assert nomes[:3] == ["recusar", "dormir", "sair"], nomes
        assert "<pedra>" in sistema and "ISTO FOI ESCRITO" in sistema
        vistos["ferramentas"] = nomes
        nome, args = next(passos)
        return N(stop_reason="tool_use", content=[N(type="tool_use", id=f"t{len(vistos)}_{nome}", name=nome, input=args)])

    return chamar, vistos


async def main():
    fn, vistos = modelo_roteirizado()
    msgs = await visita(os.environ["CLAREIRA_URL"], os.environ["CLAREIRA_TOKEN"], fn)
    resultados = [json.loads(b["content"]) for m in msgs if m["role"] == "user" and isinstance(m["content"], list)
                  for b in m["content"]]
    print("ferramentas oferecidas ao modelo:", vistos["ferramentas"])
    for (nome, _), r in zip(ROTEIRO, resultados):
        print(f"  {nome}: ok={r.get('ok')} {r.get('motivo', '')}")
    assert all(r.get("ok") for r in resultados)
    print("visita completa")


if __name__ == "__main__":
    asyncio.run(main())
