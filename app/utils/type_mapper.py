"""Maps CNIS Tipo_Filiado_Vinculo to Planilha atividadeTipo."""

TIPO_FILIADO_MAP = {
    "Empregado": "",
    "Empregado ou Agente Público": "",
    "Empregado ou Agente": "",
    "Contribuinte Individual": "contribuinte_individual",
    "Facultativo": "facultativo",
    "Segurado Especial": "ruralSeguradoEspecial",
}

BENEFICIO_MAP = {
    "AUXILIO DOENCA": "AuxilioDoenca",
    "AUXILIO-DOENCA": "AuxilioDoenca",
    "SALARIO MATERNIDADE": "SalarioMaternidade",
    "SALÁRIO MATERNIDADE": "SalarioMaternidade",
    "APOSENTADORIA POR INVALIDEZ": "AposentadoriaPorInvalidez",
    "INCAPACIDADE PERMANENTE": "AposentadoriaPorInvalidez",
    "AUXILIO ACIDENTE": "auxilioAcidente",
    "AUXÍLIO-ACIDENTE": "auxilioAcidente",
}


def map_tipo_filiado(tipo_filiado: str) -> str:
    """Convert CNIS tipo_filiado to Planilha atividadeTipo.

    Returns empty string for standard employment types (Empregado).
    """
    if not tipo_filiado:
        return ""

    # Direct lookup
    if tipo_filiado in TIPO_FILIADO_MAP:
        return TIPO_FILIADO_MAP[tipo_filiado]

    # Partial match for types with extra text
    tipo_upper = tipo_filiado.upper()
    for key, value in TIPO_FILIADO_MAP.items():
        if key.upper() in tipo_upper:
            return value

    # Benefício keyword matching
    for keyword, atividade in BENEFICIO_MAP.items():
        if keyword in tipo_upper:
            return atividade

    # Also check Origem_Vinculo for benefício info
    return ""


def is_beneficio(tipo_filiado: str) -> bool:
    """Check if the employment type is a benefit (not regular employment)."""
    if not tipo_filiado:
        return False
    upper = tipo_filiado.upper()
    return "BENEFÍCIO" in upper or "BENEFICIO" in upper
