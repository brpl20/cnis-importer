"""
CNIS PDF Parser - Final Version
Robust text-based parsing with proper handling of all employment types
"""

import pdfplumber
import re
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta


class CNISParserFinal:
    def __init__(self, pdf_path: str, debug: bool = False):
        self.pdf_path = Path(pdf_path)
        self.debug = debug
        self.personal_info = {}
        self.employment_relationships = []
        
    def parse(self) -> Dict:
        print(f"[INFO] Parsing CNIS: {self.pdf_path}")
        
        with pdfplumber.open(self.pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
            
            self._extract_personal_info(full_text)
            self._extract_employment_relationships(full_text)
        
        for emp in self.employment_relationships:
            emp['Metadata'] = self._calculate_metadata(emp)
            
        return {
            'personal_info': self.personal_info,
            'employment_relationships': self.employment_relationships
        }
    
    def _extract_personal_info(self, text: str):
        patterns = {
            'NIT': r'NIT:\s*([\d\.\-]+)',
            'CPF': r'CPF:\s*([\d\.\-]+)',
            'Nome': r'Nome:\s*([A-ZÇÃÕÁÉÍÓÚÂÊÔÀ\s]+?)(?:Data de nascimento|$)',
            'Data_Nascimento': r'Data de nascimento:\s*(\d{2}/\d{2}/\d{4})',
            'Nome_Mae': r'Nome da mãe:\s*([A-ZÇÃÕÁÉÍÓÚÂÊÔÀ\s]+?)(?:\n|Relações)',
        }
        
        for field_name, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                self.personal_info[field_name] = match.group(1).strip()
            else:
                self.personal_info[field_name] = None
    
    def _extract_employment_relationships(self, text: str):
        seq_pattern = r'(?:^|\n)(\d+)\s+(\d{3}\.\d{5}\.\d{2}-\d)\s+([^\n]+)'
        
        lines = text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            match = re.match(r'^(\d+)\s+(\d{3}\.\d{5}\.\d{2}-\d)\s+(.+)', line)
            if match:
                seq_num = int(match.group(1))
                nit = match.group(2)
                rest_of_line = match.group(3)
                
                employment_data = self._parse_employment_header(
                    seq_num, nit, rest_of_line, lines, i
                )
                
                if employment_data:
                    self.employment_relationships.append(employment_data)
                    
                    i = self._parse_remuneracoes_after_header(
                        employment_data, lines, i + 1
                    )
                else:
                    i += 1
            else:
                i += 1
    
    def _parse_employment_header(self, seq: int, nit: str, rest_of_line: str, 
                                  lines: List[str], line_idx: int) -> Optional[Dict]:
        try:
            parts = rest_of_line.split()
            
            codigo_emp = ""
            origem_vinculo = []
            matricula = ""
            tipo_filiado = ""
            data_inicio = None
            data_fim = None
            ultima_remu = None
            indicadores = ""
            
            if parts and re.match(r'[\d\./\-]+', parts[0]):
                codigo_emp = parts[0]
                parts = parts[1:]
            
            for idx, part in enumerate(parts):
                if re.match(r'\d{2}/\d{2}/\d{4}', part):
                    if not data_inicio:
                        data_inicio = part
                    elif not data_fim:
                        data_fim = part
                elif re.match(r'\d{2}/\d{4}', part):
                    ultima_remu = part
                elif part in ['Empregado', 'Contribuinte', 'Facultativo'] or 'Agente' in part:
                    tipo_filiado_parts = [part]
                    for j in range(idx + 1, len(parts)):
                        if not re.match(r'\d{2}/\d{2}/\d{4}', parts[j]) and not re.match(r'\d{2}/\d{4}', parts[j]):
                            tipo_filiado_parts.append(parts[j])
                        else:
                            break
                    tipo_filiado = ' '.join(tipo_filiado_parts)
                    break
                else:
                    origem_vinculo.append(part)
            
            origem_str = ' '.join(origem_vinculo)
            
            if re.search(r'\d{10,}', origem_str):
                clean_name = []
                matricula_parts = []
                for word in origem_vinculo:
                    if re.match(r'\d{10,}', word.replace('.', '').replace('/', '').replace('-', '')):
                        matricula_parts.append(word)
                    elif matricula_parts:
                        matricula_parts.append(word)
                    else:
                        clean_name.append(word)
                
                origem_str = ' '.join(clean_name)
                if matricula_parts:
                    matricula = ' '.join(matricula_parts)
            
            next_line_idx = line_idx + 1
            if next_line_idx < len(lines):
                next_line = lines[next_line_idx]
                
                if next_line and not next_line.startswith('Seq.') and not next_line.startswith('Remunerações'):
                    if 'FAZENDA' in next_line or 'COOPERATIVAS' in next_line or not re.match(r'^\d', next_line):
                        origem_str += ' ' + next_line.strip()
                
                if 'Indicadores:' in next_line:
                    ind_match = re.search(r'Indicadores:\s*(.+)', next_line)
                    if ind_match:
                        indicadores = ind_match.group(1).strip()
                
                if next_line_idx + 1 < len(lines) and 'Indicadores:' in lines[next_line_idx + 1]:
                    ind_match = re.search(r'Indicadores:\s*(.+)', lines[next_line_idx + 1])
                    if ind_match:
                        indicadores = ind_match.group(1).strip()
            
            return {
                'sequence': seq,
                'Data': {
                    'NIT': nit,
                    'Codigo_Empresa': codigo_emp,
                    'Origem_Vinculo': origem_str.strip(),
                    'Matricula_Trabalhador': matricula,
                    'Tipo_Filiado_Vinculo': tipo_filiado,
                    'Inicio': data_inicio,
                    'Fim': data_fim,
                    'Ultima_Remu': ultima_remu,
                    'Indicadores': indicadores
                },
                'Remuneracoes': []
            }
            
        except Exception as e:
            if self.debug:
                print(f"[ERROR] Failed to parse employment header: {e}")
            return None
    
    def _parse_remuneracoes_after_header(self, employment: Dict, lines: List[str], 
                                         start_idx: int) -> int:
        i = start_idx
        tipo_filiado = employment['Data'].get('Tipo_Filiado_Vinculo', '')
        
        while i < len(lines):
            line = lines[i]
            
            if re.match(r'^\d+\s+\d{3}\.\d{5}\.\d{2}-\d', line):
                return i
            
            if 'Remunerações' in line:
                i += 1
                continue
            
            if 'Indicadores:' in line and not employment['Data']['Indicadores']:
                ind_match = re.search(r'Indicadores:\s*(.+)', line)
                if ind_match:
                    employment['Data']['Indicadores'] = ind_match.group(1).strip()
                i += 1
                continue
            
            if 'Competência' in line:
                if 'Salário Contribuição' in line:
                    i = self._parse_facultativo_table(employment, lines, i)
                elif 'Contrat./Cooperat.' in line or 'Estabelecimento' in line:
                    i = self._parse_contribuinte_individual_table(employment, lines, i)
                else:
                    i = self._parse_regular_remuneracoes(employment, lines, i)
                continue
            
            if line.strip() and re.match(r'\d{2}/\d{4}', line.strip()[:7]):
                if 'Contribuinte' in tipo_filiado:
                    self._parse_contribuinte_line(employment, line)
                elif 'Facultativo' in tipo_filiado:
                    self._parse_facultativo_line(employment, line)
                else:
                    self._parse_regular_remuneracao_line(employment, line)
            
            if line.startswith('O INSS poderá') or line.startswith('Página'):
                return i
            
            i += 1
        
        return i
    
    def _parse_regular_remuneracoes(self, employment: Dict, lines: List[str], start_idx: int) -> int:
        i = start_idx + 1
        
        while i < len(lines):
            line = lines[i]
            
            if re.match(r'^\d+\s+\d{3}\.\d{5}', line) or 'Seq.' in line:
                return i
            
            if line.startswith('Matrícula') or line.startswith('O INSS'):
                return i
            
            if line.strip():
                comp_remu_pattern = r'(\d{2}/\d{4})\s+([\d\.,]+)(?:\s+([A-Z\-]+(?:\s+[A-Z\-]+)*))?'
                matches = list(re.finditer(comp_remu_pattern, line))
                
                for match in matches:
                    competencia = match.group(1)
                    remuneracao_str = match.group(2)
                    indicadores = match.group(3) if match.group(3) else ""
                    
                    employment['Remuneracoes'].append({
                        'Competencia': competencia,
                        'Remuneracao': self._parse_currency(remuneracao_str),
                        'Indicadores': indicadores.strip() if indicadores else ""
                    })
            
            i += 1
        
        return i
    
    def _parse_contribuinte_individual_table(self, employment: Dict, lines: List[str], start_idx: int) -> int:
        i = start_idx + 1
        
        while i < len(lines):
            line = lines[i]
            
            if re.match(r'^\d+\s+\d{3}\.\d{5}', line) or 'Seq.' in line:
                return i
            
            if line.startswith('Matrícula') or line.startswith('O INSS'):
                return i
            
            if line.strip() and re.match(r'\d{2}/\d{4}', line.strip()[:7]):
                parts = line.split()
                if len(parts) >= 2:
                    competencia = parts[0]
                    
                    remuneracao_str = None
                    for part in reversed(parts):
                        if re.match(r'[\d\.,]+$', part) and (',' in part or '.' in part):
                            remuneracao_str = part
                            break
                    
                    indicadores = ""
                    for part in parts:
                        if 'IREM' in part.upper():
                            indicadores = part
                            break
                    
                    if remuneracao_str:
                        employment['Remuneracoes'].append({
                            'Competencia': competencia,
                            'Remuneracao': self._parse_currency(remuneracao_str),
                            'Indicadores': indicadores
                        })
            
            i += 1
        
        return i
    
    def _parse_facultativo_table(self, employment: Dict, lines: List[str], start_idx: int) -> int:
        i = start_idx + 1
        
        while i < len(lines):
            line = lines[i]
            
            if re.match(r'^\d+\s+\d{3}\.\d{5}', line) or 'Seq.' in line:
                return i
            
            if line.startswith('Matrícula') or line.startswith('O INSS'):
                return i
            
            if line.strip() and re.match(r'\d{2}/\d{4}', line.strip()[:7]):
                parts = line.split()
                if len(parts) >= 3:
                    competencia = parts[0]
                    
                    currency_values = []
                    for part in parts[1:]:
                        if re.match(r'[\d\.,]+$', part) and (',' in part or '.' in part):
                            currency_values.append(part)
                    
                    salario_contrib = currency_values[-1] if currency_values else None
                    
                    indicadores = []
                    for part in parts:
                        if 'PREC' in part.upper() or 'MENOR' in part.upper() or 'INDPEND' in part.upper() or 'FACULT' in part.upper():
                            indicadores.append(part)
                    
                    if salario_contrib:
                        employment['Remuneracoes'].append({
                            'Competencia': competencia,
                            'Remuneracao': self._parse_currency(salario_contrib),
                            'Indicadores': ', '.join(indicadores) if indicadores else ""
                        })
            
            i += 1
        
        return i
    
    def _parse_regular_remuneracao_line(self, employment: Dict, line: str):
        pass
    
    def _parse_contribuinte_line(self, employment: Dict, line: str):
        pass
    
    def _parse_facultativo_line(self, employment: Dict, line: str):
        pass
    
    def _calculate_metadata(self, employment: Dict) -> Dict:
        data = employment.get('Data', {})
        remu = employment.get('Remuneracoes', [])
        
        nit_match = data.get('NIT') == self.personal_info.get('NIT')
        has_data_inicio = bool(data.get('Inicio'))
        has_data_fim = bool(data.get('Fim'))
        has_ultima_remu = bool(data.get('Ultima_Remu'))
        
        all_competences_complete = False
        all_date_matches = False
        
        if remu and has_data_inicio and has_data_fim:
            try:
                inicio = datetime.strptime(data['Inicio'], '%d/%m/%Y')
                fim = datetime.strptime(data['Fim'], '%d/%m/%Y')
                
                expected_months = []
                current = inicio.replace(day=1)
                end = fim.replace(day=1)
                while current <= end:
                    expected_months.append(current.strftime('%m/%Y'))
                    current += relativedelta(months=1)
                
                actual_months = [r['Competencia'] for r in remu]
                all_competences_complete = len(actual_months) == len(expected_months)
                all_date_matches = set(actual_months) == set(expected_months)
            except:
                pass
        
        return {
            'Nit_Match_Main_NIT': nit_match,
            'All_Competences_Complete': all_competences_complete,
            'Data_Inicio': has_data_inicio,
            'Data_Fim': has_data_fim,
            'Ultima_Remu': has_ultima_remu,
            'All_Date_Matches': all_date_matches
        }
    
    def _parse_currency(self, value: str) -> Optional[float]:
        if not value:
            return None
        try:
            cleaned = str(value).strip().replace('.', '').replace(',', '.')
            return float(cleaned)
        except:
            return None
    
    def export_to_json(self, output_path: str):
        results = {
            'personal_info': self.personal_info,
            'employment_relationships': self.employment_relationships
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"[SUCCESS] Exported to {output_path}")


if __name__ == "__main__":
    parser = CNISParserFinal(pdf_path="CNIS1.pdf", debug=True)
    results = parser.parse()
    parser.export_to_json("cnis_extracted_final.json")
    
    print("\n" + "="*60)
    print("PARSING SUMMARY")
    print("="*60)
    print(f"Personal Info: {parser.personal_info}")
    print(f"\nEmployment Relationships: {len(parser.employment_relationships)}\n")
    
    for emp in parser.employment_relationships[:10]:
        seq = emp['sequence']
        origem = emp['Data'].get('Origem_Vinculo', 'Unknown')
        matricula = emp['Data'].get('Matricula_Trabalhador', '')
        num_remu = len(emp.get('Remuneracoes', []))
        
        print(f"Seq {seq}: {origem[:60]}")
        if matricula:
            print(f"  Matrícula: {matricula}")
        print(f"  Tipo: {emp['Data'].get('Tipo_Filiado_Vinculo', 'N/A')}")
        print(f"  Remunerações: {num_remu}")
        if emp.get('Remuneracoes'):
            print(f"  First: {emp['Remuneracoes'][0]}")
        print()
    
    print("="*60)
