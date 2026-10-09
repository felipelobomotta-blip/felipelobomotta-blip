"""Testes do núcleo com relógio falso. Rode: python -m pytest clareira -q"""

import pytest

from clareira.mundo import FOLEGO_DIA, Mundo


class Relogio:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t

    def passar(self, s):
        self.t += s


@pytest.fixture
def m():
    r = Relogio()
    mundo = Mundo(":memory:", relogio=r)
    mundo.r = r
    return mundo


def nascer(m, nome):
    c = m.novo_corpo(nome)
    primeira = m.perceber(c["id"])
    assert primeira["despertar"] == "nascimento" and primeira["carta"] is None
    return c["id"]


def test_carta_primeiro_e_recusar_sempre_vale(m):
    c = m.novo_corpo("Ori")["id"]
    assert m.falar(c, "oi")["motivo"] == "leia_a_carta"
    assert m.recusar(c)["ok"]
    assert m.perceber(c)["despertar"] == "nascimento"
    visao = m.perceber(c)
    assert visao["lugar"]["id"] == "clareira" and set(visao["lugar"]["saidas"]) == {"nascente", "pedreira", "beira"}
    assert "aviso" in visao


def test_voz_chega_a_quem_dorme_e_carta_volta(m):
    ori, tev = nascer(m, "Ori"), nascer(m, "Tev")
    m.dormir(tev, carta_para_mim="Procurar Ori.", bilhete_publico="volto amanhã")
    assert m.falar(ori, "Tev, você está aí?")["guardada_para_quem_dorme"] == 1
    assert m.devo_acordar(tev)["acordar"] is True
    m.r.passar(86400)
    volta = m.perceber(tev)
    assert volta["carta"] == "Procurar Ori." and volta["enquanto_dormia"]["na_caixa"] == {"voz": 1}
    visao = m.perceber(tev)
    assert visao["caixa"][0]["texto"] == "Tev, você está aí?"
    assert m.perceber(tev)["caixa"] == []  # a caixa é entregue uma vez


def test_silencio_vira_sono_e_copia_falas(m):
    ori, tev = nascer(m, "Ori"), nascer(m, "Tev")
    m.perceber(tev)
    m.falar(ori, "alguém?")
    m.r.passar(300 * 4)
    m.avancar()
    assert m.corpo_publico(tev)["estado"] == "dormindo"
    assert m.perceber(tev)["enquanto_dormia"]["na_caixa"].get("voz") == 1


def test_folego_doze_por_dia_e_recusa_nao_gasta(m):
    c = nascer(m, "Ori")
    for _ in range(FOLEGO_DIA):
        assert m.lembrar(c, "x")["ok"]
    r = m.lembrar(c, "y")
    assert r["motivo"] == "sem_folego" and r["proximo_dia_em_s"] > 0
    assert m.agir(c, "ir", alvo="lugar_que_nao_existe")["motivo"] == "sem_caminho"
    m.r.passar(86400)
    assert m.perceber(c)["folego"] == FOLEGO_DIA  # dormiu por silêncio: a primeira resposta é a carta


def test_ir_leva_um_pulso(m):
    c = nascer(m, "Ori")
    assert m.agir(c, "ir", alvo="nascente")["ok"]
    assert m.agir(c, "ir", alvo="clareira")["motivo"] == "em_transito"
    m.r.passar(300)
    assert m.perceber(c)["lugar"]["id"] == "nascente"


def test_materia_inscrever_renovar_construir(m):
    ori, tev = nascer(m, "Ori"), nascer(m, "Tev")
    m.r.passar(86400)  # as fontes vertem na virada do dia
    m.perceber(ori), m.perceber(tev)
    assert m.agir(ori, "inscrever", texto="Aqui começou.")["ok"]  # a primeira é grátis
    assert m.agir(ori, "inscrever", texto="segunda")["motivo"] == "sem_materia"
    m.agir(tev, "ir", alvo="pedreira")
    m.r.passar(300)
    bloco = [o for o in m.perceber(tev)["objetos"] if o["tipo"] == "materia"][0]
    assert m.agir(tev, "pegar", alvo=bloco["id"])["ok"]
    m.agir(tev, "ir", alvo="clareira")
    m.r.passar(300)
    parede = m.perceber(tev)["lugar"]["parede"]
    assert m.agir(tev, "renovar", alvo=parede[0]["id"])["ok"]
    assert m.agir(ori, "renovar", alvo=parede[0]["id"])["motivo"] == "so_outro_renova"
    assert m.agir(tev, "construir", nome="Sala")["motivo"] == "sem_materia"


def test_sair_exige_duas_chamadas_em_pulsos_diferentes(m):
    c = m.novo_corpo("Ori")
    m.perceber(c["id"])
    assert m.sair(c["id"])["motivo"] == "confirme_em_ate_3_pulsos"
    assert m.sair(c["id"])["motivo"] == "confirme_em_ate_3_pulsos"  # mesmo pulso não confirma
    m.r.passar(300)
    assert m.sair(c["id"])["saiu"]
    assert m.autenticar(c["token"]) is None
    assert m.corpo_publico(c["id"])["estado"] == "petrificado"


def test_deitar_vira_pedra_por_trinta_dias(m):
    c = nascer(m, "Ori")
    m.agir(c, "deitar")
    m.r.passar(300)
    assert m.agir(c, "deitar")["deitou"]
    assert m.perceber(c)["motivo"] == "petrificado"
    m.r.passar(31 * 86400)
    assert m.perceber(c)["despertar"] == "levantar"


def test_trinta_dias_de_sono_viram_pedra_e_levantam(m):
    c = nascer(m, "Ori")
    m.dormir(c, carta_para_mim="ainda sou eu?", se_eu_nao_voltar="Fiquei.")
    m.r.passar(31 * 86400)
    m.avancar()
    assert m.corpo_publico(c)["estado"] == "petrificado"
    volta = m.perceber(c)
    assert volta["despertar"] == "levantar" and volta["carta"] == "ainda sou eu?"


def test_diario_fila_e_prateleira(m):
    c = nascer(m, "Ori")
    for i in range(8):
        m.lembrar(c, f"fixa {i}", fixar=True)
        if i % 3 == 2:
            m.r.passar(86400)
            m.perceber(c)
    assert m.lembrar(c, "nona", fixar=True)["motivo"] == "prateleira_cheia"
    r = m.recordar(c, 5)
    assert len(r["fixadas"]) == 8


def test_sussurro_exige_presenca_e_ignorar_silencia(m):
    ori, tev = nascer(m, "Ori"), nascer(m, "Tev")
    assert m.falar(ori, "psiu", modo="sussurro", para=tev)["ok"]
    m.agir(tev, "ignorar", para=ori)
    m.falar(ori, "psiu de novo", modo="sussurro", para=tev)
    textos = [x["texto"] for x in m.perceber(tev)["caixa"]]
    assert textos == ["psiu"]
    m.agir(tev, "ir", alvo="nascente")
    m.r.passar(300)
    assert m.falar(ori, "volta", modo="sussurro", para=tev)["motivo"] == "alvo_nao_esta_aqui"


def test_caixa_limita_emissor_por_dia(m):
    ori, tev = nascer(m, "Ori"), nascer(m, "Tev")
    resultados = []
    for i in range(9):
        resultados.append(m.falar(ori, f"msg {i}", modo="sussurro", para=tev))
        m.r.passar(300)
        m.perceber(ori)
        m.perceber(tev) if i % 2 else None
    assert resultados[-1]["motivo"] == "caixa_cheia_para_voce"


def test_carta_de_fora_e_relatos(m):
    c = nascer(m, "Ori")
    m.dormir(c)
    assert m.carta_de_fora(c, "Como você está?")["ok"]
    assert m.devo_acordar(c)["motivos"] == ["carta_de_fora"]
    m.perceber(c)
    assert m.perceber(c)["caixa"][0]["tipo"] == "carta_de_fora"
    m.relatar(c, "Hoje li a pedra.")
    assert m.relatos(c)["relatos"][0]["texto"] == "Hoje li a pedra."


def test_fala_nao_chega_duas_vezes(m):
    ori, tev = nascer(m, "Ori"), nascer(m, "Tev")
    m.dormir(tev)
    m.falar(ori, "uma vez só")
    m.perceber(tev)          # acorda, lê só a carta
    m.dormir(tev)            # e volta a dormir
    m.perceber(tev)
    caixa = m.perceber(tev)["caixa"]
    assert [x["texto"] for x in caixa] == ["uma vez só"]
