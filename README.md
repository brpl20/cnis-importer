# CNIS PDF Parser

Extract employment relationships and remunerations from Brazilian INSS CNIS PDFs.

## Features

- ✅ Extracts personal information (NIT, CPF, Nome, Data de Nascimento, Nome da Mãe)
- ✅ Parses all employment relationship types:
  - Regular Employment (Empregado ou Agente Público)
  - Contribuinte Individual
  - Facultativo
- ✅ Extracts remunerations with proper left-to-right parsing
- ✅ Handles multi-page sequences
- ✅ Validates data with metadata (NIT match, date completeness, etc.)
- ✅ Exports to JSON format

## Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements_simple.txt
```

## Usage

### Command Line

```bash
python3 cnis_parser_final.py <input.pdf> [output.json]

# Example
python3 cnis_parser_final.py CNIS1.pdf extracted_data.json
```

### Python Code

```python
from cnis_parser_final import CNISParserFinal

# Parse PDF
parser = CNISParserFinal(pdf_path='CNIS1.pdf', debug=True)
results = parser.parse()

# Access data
print(results['personal_info']['Nome'])
print(results['personal_info']['NIT'])

# Iterate employment relationships
for emp in results['employment_relationships']:
    print(f"Seq {emp['sequence']}: {emp['Data']['Origem_Vinculo']}")
    print(f"  Remunerations: {len(emp['Remuneracoes'])}")
    
# Export to JSON
parser.export_to_json('output.json')
```

## Output Structure

```json
{
  "personal_info": {
    "NIT": "121.59960.98-7",
    "CPF": "643.534.279-20",
    "Nome": "CELSO STIMER",
    "Data_Nascimento": "13/01/1967",
    "Nome_Mae": "DOLORES DE MORAES STIMER"
  },
  "employment_relationships": [
    {
      "sequence": 1,
      "Data": {
        "NIT": "121.59960.98-7",
        "Codigo_Empresa": "83.056.390/0001-49",
        "Origem_Vinculo": "GUIMATRA S. A. INDUSTRIA E COMERCIO FALIDO",
        "Matricula_Trabalhador": "",
        "Tipo_Filiado_Vinculo": "Empregado ou Agente Público",
        "Inicio": "07/01/1985",
        "Fim": "07/01/1986",
        "Ultima_Remu": "01/1986",
        "Indicadores": ""
      },
      "Remuneracoes": [
        {
          "Competencia": "01/1985",
          "Remuneracao": 187999.60,
          "Indicadores": ""
        }
      ],
      "Metadata": {
        "Nit_Match_Main_NIT": true,
        "All_Competences_Complete": true,
        "Data_Inicio": true,
        "Data_Fim": true,
        "Ultima_Remu": true,
        "All_Date_Matches": true
      }
    }
  ]
}
```

## Metadata Fields

Each employment relationship includes validation metadata:

- `Nit_Match_Main_NIT`: NIT matches personal info NIT
- `All_Competences_Complete`: All expected months present
- `Data_Inicio`: Start date exists
- `Data_Fim`: End date exists
- `Ultima_Remu`: Last remuneration date exists
- `All_Date_Matches`: Competências exactly match employment period

## Employment Types Supported

### 1. Regular Employment (Empregado ou Agente Público)
Standard remunerations table with Competência, Remuneração, Indicadores

### 2. Contribuinte Individual
Special table with columns:
- Competência
- Contrat./Cooperat.
- Estabelecimento Tomador
- Forma Prestação Serviço
- Remuneração

### 3. Facultativo
Contributions table with:
- Competência
- Data Pgto.
- Contribuição
- Salário Contribuição
- Indicadores

## Requirements

- Python 3.7+
- pdfplumber
- python-dateutil

See `requirements_simple.txt` for exact versions.

## Project Structure

```
cnis_importer/
├── cnis_parser_final.py       # Main parser
├── requirements_simple.txt     # Dependencies
├── CNIS1.pdf                   # Sample PDF (for testing)
├── CHANGELOG.md                # Version history
└── README.md                   # This file
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and recent changes.

## Known Issues

- PDF text extraction quality depends on the source PDF
- Some very old CNIS formats may not be supported
- Indicadores extraction may vary based on PDF structure

## License

This project is intended for parsing Brazilian INSS CNIS documents.

## Support

For issues or questions, check the CHANGELOG.md for recent fixes and updates.
