# CNIS PDF Parser

Extrator de dados de CNIS (Cadastro Nacional de Informações Sociais) do INSS em formato PDF. Extrai relações previdenciárias, remunerações e dados pessoais para JSON estruturado.

Validado com **100% de acurácia** contra 39 CNIS usando o [Tramitação Inteligente](https://planilha.tramitacaointeligente.com.br) como referência.

## Instalação

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_simple.txt
```

## Uso

### Linha de comando

```bash
python3 cnis_parser_final.py <cnis.pdf> [output.json]
```

### Python

```python
from cnis_parser_final import CNISParserFinal

parser = CNISParserFinal(pdf_path='CNIS.pdf', debug=True)
results = parser.parse()

# Dados pessoais
print(results['personal_info']['Nome'])
print(results['personal_info']['CPF'])
print(results['personal_info']['Data_Nascimento'])

# Vínculos empregatícios
for emp in results['employment_relationships']:
    d = emp['Data']
    print(f"Seq {emp['sequence']}: {d['Origem_Vinculo']}")
    print(f"  Tipo: {d['Tipo_Filiado_Vinculo']}")
    print(f"  Período: {d['Inicio']} a {d['Fim']}")
    print(f"  Remunerações: {len(emp['Remuneracoes'])}")

# Exportar JSON
parser.export_to_json('resultado.json')
```

### API REST

```bash
# Iniciar servidor
python3 api.py

# Health check
curl http://localhost:8000/health

# Parse completo
curl -X POST -F "file=@CNIS.pdf" http://localhost:8000/parse

# Apenas resumo
curl -X POST -F "file=@CNIS.pdf" http://localhost:8000/parse/summary
```

## Dados Extraídos

### Dados Pessoais
| Campo | Exemplo |
|---|---|
| NIT | 121.59960.98-7 |
| CPF | 643.534.279-20 |
| Nome | CELSO STIMER |
| Data_Nascimento | 13/01/1967 |
| Nome_Mae | DOLORES DE MORAES STIMER |

### Vínculos Empregatícios
Cada vínculo contém:

- **Dados**: empresa, CNPJ, tipo de filiação, datas início/fim, indicadores
- **Remunerações**: competência (MM/YYYY), valor, indicadores
- **Metadata**: validação automática (NIT match, completude de datas)

### Tipos de Vínculo Suportados
- Empregado ou Agente Público
- Contribuinte Individual
- Facultativo
- Segurado Especial (Rural)
- Benefícios (Auxílio-doença, Salário Maternidade, Aposentadoria, etc.)

## Estrutura do Projeto

```
cnis_importer/
├── cnis_parser_final.py          # Parser principal
├── api.py                        # API REST (Flask)
├── requirements.txt              # Dependências completas
├── requirements_simple.txt       # Dependências mínimas
├── tramitacao/                   # Automação Tramitação Inteligente
│   ├── automate_tramitacao.js    #   Playwright: upload CNIS + download PDFs
│   └── extract_specs.py          #   Extrai specs dos PDFs de análise
├── tests/                        # Testes de cobertura
│   └── compare_with_specs.py     #   Compara parser vs specs do Tramitação
├── sensitive-f2/                 # CNIS PDFs (não versionado - dados sensíveis)
├── downloads/                    # PDFs gerados pelo Tramitação (não versionado)
├── specs/                        # Specs JSON extraídos (não versionado)
└── README.md
```

## Validação com Tramitação Inteligente

O parser foi validado contra o sistema [Tramitação Inteligente](https://planilha.tramitacaointeligente.com.br), referência no mercado previdenciário brasileiro.

### Processo de validação

1. **Upload**: 39 CNIS PDFs enviados ao Tramitação via automação Playwright
2. **Extração**: PDFs de análise (contagem de tempo de contribuição) baixados
3. **Specs**: Dados extraídos dos PDFs de análise como "gabarito"
4. **Comparação**: Saída do nosso parser confrontada com os specs

### Rodar os testes

```bash
source venv/bin/activate
python tests/compare_with_specs.py
```

### Resultado atual

```
Testes: 39
Média: 100.0%
530 verificações (dados pessoais + datas de início/fim de todos os vínculos)
```

### Gerar novos specs (requer conta no Tramitação Inteligente)

```bash
# 1. Instalar Playwright
npm install playwright
npx playwright install chromium

# 2. Colocar CNIS PDFs em sensitive-f2/

# 3. Rodar automação (editar credenciais em automate_tramitacao.js)
node tramitacao/automate_tramitacao.js

# 4. Extrair specs dos PDFs baixados
python tramitacao/extract_specs.py

# 5. Rodar comparação
python tests/compare_with_specs.py
```

## Requisitos

- Python 3.7+
- pdfplumber
- python-dateutil
- Flask (opcional, para API REST)
- Node.js + Playwright (opcional, para validação com Tramitação)
