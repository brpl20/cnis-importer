"""Transforms parser output into ProcStudio Planilha.spreadsheet_data schema."""

import secrets
from app.utils.type_mapper import map_tipo_filiado, is_beneficio


def _generate_uid():
    return f"p-{secrets.token_hex(4)}"


def _transform_periodo(seq: int, emp: dict) -> dict:
    data = emp.get("Data", {})
    tipo = data.get("Tipo_Filiado_Vinculo") or ""
    origem = data.get("Origem_Vinculo") or ""
    inicio = data.get("Inicio") or ""
    fim = data.get("Fim") or ""

    # For benefícios, use the tipo as name; for employment, use company name
    if is_beneficio(tipo):
        name = tipo.replace("Benefício ", "").strip()
        if not name:
            name = origem
    else:
        name = origem

    atividade_tipo = map_tipo_filiado(tipo)

    # If tipo not mapped via tipo_filiado, check origem for benefício keywords
    if not atividade_tipo and is_beneficio(tipo):
        atividade_tipo = map_tipo_filiado(origem)

    return {
        "uid": _generate_uid(),
        "seq": seq,
        "name": name,
        "inicio": inicio,
        "fim": fim,
        "ativo": True,
        "atividadeTipo": atividade_tipo,
        "especial": "normal",
        "contaParaCarencia": True,
        "fatorPersonalizadoDoEspecial": None,
        "indenizouRuralSeguradoEspecialApos31101991": False,
        "complementouAliquotaReduzida": False,
        "grauDeficiencia": None,
        "meta": {
            "tipoVinculo": tipo,
            "codigoEmpresa": data.get("Codigo_Empresa") or "",
            "indicadores": data.get("Indicadores") or "",
            "totalRemuneracoes": len(emp.get("Remuneracoes", [])),
            "inicioCnis": inicio,
            "fimCnis": fim,
        },
    }


def transform_to_planilha(parser_result: dict) -> dict:
    """Transform parser output to Planilha.spreadsheet_data schema.

    Returns a dict that can be directly stored in Planilha.spreadsheet_data (JSONB).
    """
    personal = parser_result.get("personal_info", {})
    empls = parser_result.get("employment_relationships", [])

    periodos = [_transform_periodo(i + 1, emp) for i, emp in enumerate(empls)]

    return {
        "segurado": {
            "cpf": personal.get("CPF") or "",
            "nome": personal.get("Nome") or "",
            "sexo": "",  # CNIS does not contain sex
            "dataDeNascimento": personal.get("Data_Nascimento") or "",
            "customerUuid": "",
        },
        "tabs": [
            {
                "uid": "tab-1",
                "label": "CNIS Import",
                "der": "",
                "reafirmacaoDer": "",
                "sistema": "rgps",
                "periodos": periodos,
                "periodosDeficiencia": [],
            }
        ],
        "activeTabUid": "tab-1",
        "config": {"mostrarRegrasPreReforma": False},
    }
