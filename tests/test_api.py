"""Tests for the FastAPI CNIS Parser microservice."""

import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

CNIS_DIR = os.path.join(os.path.dirname(__file__), '..', 'sensitive-f2')
SAMPLE_PDF = os.path.join(CNIS_DIR, 'ADEMAR FRANCISCO ROMAN (2330) - CNIS - 2025.03.pdf')
API_KEY = "changeme"


def has_sample_pdf():
    return os.path.exists(SAMPLE_PDF)


class TestHealth:
    def test_health_no_auth(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestAuth:
    def test_no_api_key_returns_403(self):
        if not has_sample_pdf():
            pytest.skip("No sample PDF")
        with open(SAMPLE_PDF, "rb") as f:
            r = client.post("/api/v1/parse", files={"file": ("test.pdf", f, "application/pdf")})
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "AUTH_MISSING"

    def test_wrong_api_key_returns_403(self):
        if not has_sample_pdf():
            pytest.skip("No sample PDF")
        with open(SAMPLE_PDF, "rb") as f:
            r = client.post("/api/v1/parse", files={"file": ("test.pdf", f, "application/pdf")},
                           headers={"X-API-Key": "wrong-key"})
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "AUTH_INVALID"


class TestValidation:
    def test_non_pdf_returns_400(self):
        r = client.post("/api/v1/parse",
                       files={"file": ("test.txt", b"not a pdf", "text/plain")},
                       headers={"X-API-Key": API_KEY})
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "INVALID_FILE_TYPE"

    def test_empty_filename_returns_error(self):
        r = client.post("/api/v1/parse",
                       files={"file": ("", b"content", "application/pdf")},
                       headers={"X-API-Key": API_KEY})
        assert r.status_code in (400, 422)  # FastAPI may reject before our validation


class TestParse:
    @pytest.mark.skipif(not os.path.exists(SAMPLE_PDF), reason="No sample PDF")
    def test_parse_full(self):
        with open(SAMPLE_PDF, "rb") as f:
            r = client.post("/api/v1/parse", files={"file": ("cnis.pdf", f, "application/pdf")},
                           headers={"X-API-Key": API_KEY})
        assert r.status_code == 200
        d = r.json()
        assert d["success"] is True
        assert d["processing_time_ms"] > 0
        assert d["data"]["personal_info"]["nome"] == "ADEMAR FRANCISCO ROMAN"
        assert d["data"]["personal_info"]["cpf"] == "272.364.632-72"
        assert len(d["data"]["vinculos"]) > 0
        v = d["data"]["vinculos"][0]
        assert "sequencia" in v
        assert "inicio" in v
        assert "fim" in v
        assert "remuneracoes" in v
        assert "metadata" in v

    @pytest.mark.skipif(not os.path.exists(SAMPLE_PDF), reason="No sample PDF")
    def test_parse_summary(self):
        with open(SAMPLE_PDF, "rb") as f:
            r = client.post("/api/v1/parse/summary", files={"file": ("cnis.pdf", f, "application/pdf")},
                           headers={"X-API-Key": API_KEY})
        assert r.status_code == 200
        d = r.json()
        assert d["success"] is True
        v = d["data"]["vinculos"][0]
        assert "remuneracoes" not in v
        assert "total_remuneracoes" in v

    @pytest.mark.skipif(not os.path.exists(SAMPLE_PDF), reason="No sample PDF")
    def test_parse_planilha(self):
        with open(SAMPLE_PDF, "rb") as f:
            r = client.post("/api/v1/parse/planilha", files={"file": ("cnis.pdf", f, "application/pdf")},
                           headers={"X-API-Key": API_KEY})
        assert r.status_code == 200
        d = r.json()
        assert d["success"] is True
        data = d["data"]
        # Check segurado
        assert data["segurado"]["nome"] == "ADEMAR FRANCISCO ROMAN"
        assert data["segurado"]["cpf"] == "272.364.632-72"
        assert data["segurado"]["dataDeNascimento"] == "09/11/1967"
        # Check tabs
        assert len(data["tabs"]) == 1
        tab = data["tabs"][0]
        assert tab["uid"] == "tab-1"
        assert tab["sistema"] == "rgps"
        assert len(tab["periodos"]) > 0
        # Check periodo structure
        p = tab["periodos"][0]
        assert "uid" in p
        assert "seq" in p
        assert "name" in p
        assert "inicio" in p
        assert "fim" in p
        assert "atividadeTipo" in p
        assert "especial" in p
        assert p["especial"] == "normal"
        assert p["contaParaCarencia"] is True
        assert "meta" in p


class TestTypeMapper:
    def test_empregado(self):
        from app.utils.type_mapper import map_tipo_filiado
        assert map_tipo_filiado("Empregado ou Agente Público") == ""
        assert map_tipo_filiado("Empregado") == ""

    def test_contribuinte(self):
        from app.utils.type_mapper import map_tipo_filiado
        assert map_tipo_filiado("Contribuinte Individual") == "contribuinte_individual"

    def test_facultativo(self):
        from app.utils.type_mapper import map_tipo_filiado
        assert map_tipo_filiado("Facultativo") == "facultativo"

    def test_segurado_especial(self):
        from app.utils.type_mapper import map_tipo_filiado
        assert map_tipo_filiado("Segurado Especial") == "ruralSeguradoEspecial"

    def test_beneficio_auxilio_doenca(self):
        from app.utils.type_mapper import map_tipo_filiado
        assert map_tipo_filiado("Benefício 31 - AUXILIO DOENCA PREVIDENCIARIO") == "AuxilioDoenca"

    def test_beneficio_maternidade(self):
        from app.utils.type_mapper import map_tipo_filiado
        assert map_tipo_filiado("Benefício 80 - AUXILIO SALARIO MATERNIDADE") == "SalarioMaternidade"

    def test_beneficio_acidente(self):
        from app.utils.type_mapper import map_tipo_filiado
        assert map_tipo_filiado("Benefício 36 - AUXILIO ACIDENTE PREVIDENCIARIO") == "auxilioAcidente"

    def test_empty(self):
        from app.utils.type_mapper import map_tipo_filiado
        assert map_tipo_filiado("") == ""
        assert map_tipo_filiado(None) == ""

    def test_is_beneficio(self):
        from app.utils.type_mapper import is_beneficio
        assert is_beneficio("Benefício 31 - AUXILIO DOENCA") is True
        assert is_beneficio("Empregado ou Agente Público") is False
        assert is_beneficio("") is False
