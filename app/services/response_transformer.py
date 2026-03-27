"""Transforms raw parser output dict into standardized API JSON response."""


def transform_personal_info(raw: dict) -> dict:
    return {
        "nit": raw.get("NIT") or "",
        "cpf": raw.get("CPF") or "",
        "nome": raw.get("Nome") or "",
        "data_nascimento": raw.get("Data_Nascimento") or "",
        "nome_mae": raw.get("Nome_Mae") or "",
        "data_extracao": raw.get("Data_Extracao") or "",
    }


def transform_vinculo(emp: dict) -> dict:
    data = emp.get("Data", {})
    return {
        "sequencia": emp.get("sequence", 0),
        "nit": data.get("NIT") or "",
        "codigo_empresa": data.get("Codigo_Empresa") or "",
        "origem_vinculo": data.get("Origem_Vinculo") or "",
        "matricula_trabalhador": data.get("Matricula_Trabalhador") or "",
        "tipo_filiado": data.get("Tipo_Filiado_Vinculo") or "",
        "inicio": data.get("Inicio") or "",
        "fim": data.get("Fim") or "",
        "ultima_remuneracao": data.get("Ultima_Remu") or "",
        "indicadores": data.get("Indicadores") or "",
        "remuneracoes": [
            {
                "competencia": r.get("Competencia") or "",
                "remuneracao": r.get("Remuneracao"),
                "indicadores": r.get("Indicadores") or "",
            }
            for r in emp.get("Remuneracoes", [])
        ],
        "metadata": transform_metadata(emp.get("Metadata", {})),
    }


def transform_vinculo_summary(emp: dict) -> dict:
    """Like transform_vinculo but without remuneracoes array."""
    v = transform_vinculo(emp)
    v.pop("remuneracoes", None)
    v["total_remuneracoes"] = len(emp.get("Remuneracoes", []))
    return v


def transform_metadata(raw: dict) -> dict:
    return {
        "nit_match": raw.get("Nit_Match_Main_NIT", False),
        "competencias_completas": raw.get("All_Competences_Complete", False),
        "tem_data_inicio": raw.get("Data_Inicio", False),
        "tem_data_fim": raw.get("Data_Fim", False),
        "tem_ultima_remuneracao": raw.get("Ultima_Remu", False),
        "datas_conferem": raw.get("All_Date_Matches", False),
    }


def transform_full(parser_result: dict) -> dict:
    """Transform full parser output to standardized API response data."""
    empls = parser_result.get("employment_relationships", [])
    vinculos = [transform_vinculo(e) for e in empls]
    total_remus = sum(len(e.get("Remuneracoes", [])) for e in empls)

    return {
        "personal_info": transform_personal_info(parser_result.get("personal_info", {})),
        "vinculos": vinculos,
        "resumo": {
            "total_vinculos": len(vinculos),
            "total_remuneracoes": total_remus,
        },
    }


def transform_summary(parser_result: dict) -> dict:
    """Transform parser output to summary (no remuneracoes arrays)."""
    empls = parser_result.get("employment_relationships", [])

    return {
        "personal_info": transform_personal_info(parser_result.get("personal_info", {})),
        "vinculos": [transform_vinculo_summary(e) for e in empls],
        "resumo": {
            "total_vinculos": len(empls),
            "total_remuneracoes": sum(len(e.get("Remuneracoes", [])) for e in empls),
        },
    }
