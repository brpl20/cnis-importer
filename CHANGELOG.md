# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - Ruby Implementation
- Implemented `cnis_parser.rb` - Ruby version for Rails integration
- Added `Gemfile` with pdf-reader dependency
- Created comprehensive Rails integration guide in `RUBY_USAGE.md`
- Examples for:
  - Standalone Ruby usage
  - Rails service objects
  - Controller integration
  - Background jobs (Sidekiq)
  - ActiveRecord models and migrations
  - RSpec tests
- Hybrid approach documentation (Python + Ruby)
- Comparison document `PYTHON_VS_RUBY.md`

## [1.0.0] - 2025-11-28 - Python Implementation

### Added
- Implemented `cnis_parser_final.py` with robust text-based parsing
- Employment relationships now properly structured with sequence, Data, Remuneracoes, and Metadata
- Remunerations are parsed left-to-right (horizontally) as they appear in the PDF
- Multi-page sequence support - sequences spanning multiple pages are correctly extracted
- Proper detection and handling of different employment types:
  - **Regular Employment** (Empregado ou Agente) - Standard remunerations table
  - **Contribuinte Individual** - Special table with Contrat./Cooperat., Estabelecimento, Tomador columns
  - **Facultativo** - Contributions table with Data Pgto., Contribuição, Salário Contribuição
- Metadata validation for each employment relationship:
  - `Nit_Match_Main_NIT`: Validates NIT matches personal info
  - `All_Competences_Complete`: Checks if all expected months are present
  - `Data_Inicio`: Validates presence of start date
  - `Data_Fim`: Validates presence of end date
  - `Ultima_Remu`: Validates presence of last remuneration date
  - `All_Date_Matches`: Validates if competências cover the entire employment period
- Proper handling of Brazilian date format (DD/MM/YYYY and MM/YYYY)
- Proper handling of Brazilian currency format (1.234,56 → 1234.56)
- JSON export in the exact requested format
- Added `requirements_simple.txt` for minimal dependencies
- Added `IMPLEMENTATION_SUCCESS.md` and `USAGE.md` documentation

### Changed
- Switched from table-based extraction to text-based parsing for better accuracy
- Refactored employment relationship extraction to match requested JSON structure
- Improved remuneration parsing to handle horizontal table layout
- Enhanced date range validation to calculate expected vs actual months
- Better separation of Origem_Vinculo and Matricula_Trabalhador fields
- Proper handling of multi-line company names (e.g., "AGRUPAMENTO DE CONTRATANTES/COOPERATIVAS")
- Improved Indicadores extraction for each employment type

### Fixed
- Fixed Origem_Vinculo concatenation with Matricula_Trabalhador (Seq 7)
- Fixed AGRUPAMENTO DE CONTRATANTES/COOPERATIVAS multi-line parsing (Seq 8-11, 13)
- Fixed remuneration values for Contribuinte Individual (was extracting company code instead of amount)
- Fixed Indicadores extraction (IREM-ACD, PREC-FACULTCONC, etc.)
- Fixed Facultativo contributions parsing to use Salário Contribuição
- Fixed handling of empty columns in tables
- Fixed remuneration extraction to parse left-to-right instead of top-to-bottom
- Fixed multi-page sequence handling - sequences now correctly span across pages
- Fixed metadata calculation to properly validate employment periods
- Fixed NIT extraction to handle the main personal NIT correctly
- Fixed company code extraction from employment headers

## [0.1.0] - Initial Implementation

### Added
- Initial CNIS parser with personal info extraction
- Visual debugging with pdfplumber
- Basic employment and contribution detection
- Excel and JSON export capabilities
