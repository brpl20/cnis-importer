"""
Extract specs from Tramitação Inteligente analysis PDFs.
Creates JSON spec files that can be used to validate the CNIS parser.
"""

import pdfplumber
import re
import json
import os
from pathlib import Path


def deduplicate_text(text):
    """Fix doubled characters from PDF rendering (e.g. 'TTeemm' → 'Tem')."""
    # Detect pattern: pairs of identical characters
    result = []
    i = 0
    while i < len(text):
        if i + 1 < len(text) and text[i] == text[i + 1] and text[i].isalpha():
            # Check if this is part of a doubled sequence (at least 3 pairs)
            j = i
            doubled = True
            pair_count = 0
            while j + 1 < len(text) and text[j] == text[j + 1] and text[j].isalpha():
                pair_count += 1
                j += 2
            if pair_count >= 3:
                # This is a doubled sequence - take every other char
                for k in range(i, j, 2):
                    result.append(text[k])
                i = j
                continue
        result.append(text[i])
        i += 1
    return ''.join(result)


def extract_tables_from_pdf(pdf_path):
    """Extract all tables and text from PDF using pdfplumber."""
    all_tables = []
    full_text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Extract text
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"

            # Extract tables
            tables = page.extract_tables()
            for table in tables:
                all_tables.append({
                    'page': page_num + 1,
                    'data': table,
                })

    # Deduplicate doubled text
    full_text = deduplicate_text(full_text)

    return full_text, all_tables


def extract_personal_info(text):
    """Extract personal data from the header."""
    info = {}
    patterns = {
        'nome': r'Segurad[oa]\s+(.+)',
        'cpf': r'CPF\s+([\d.\-]+)',
        'data_nascimento': r'Data de Nascimento\s+(\d{2}/\d{2}/\d{4})',
        'sexo': r'Sexo\s+(Masculino|Feminino)',
        'der': r'DER\s+(\d{2}/\d{2}/\d{4})',
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            info[key] = match.group(1).strip()
    return info


def extract_benefits_from_tables(tables, text):
    """Extract benefits from the tables or text."""
    benefits = []

    # Look for the benefits table in extracted tables
    for table_info in tables:
        table = table_info['data']
        if not table or len(table) < 2:
            continue

        # Check if this is the benefits table (has "Benefício" header)
        header = ' '.join(str(c or '') for c in table[0])
        if 'Benefício' not in header and 'benefício' not in header.lower():
            continue

        # Parse rows (skip header)
        for row in table[1:]:
            if not row or len(row) < 4:
                continue
            cells = [str(c or '').strip() for c in row]
            # Clean doubled text
            cells = [deduplicate_text(c) for c in cells]

            benefit_name = cells[0] if cells[0] else ''
            if not benefit_name or 'Benefício' in benefit_name:
                continue

            benefit = {'tipo': benefit_name}

            # Find tempo de contribuição (X anos, Y meses e Z dias)
            for cell in cells:
                tempo_match = re.search(r'(\d+\s*anos?,?\s*\d+\s*m[eê]s(?:es)?\s*e?\s*\d*\s*dias?)', cell)
                if tempo_match:
                    benefit['tempo_contribuicao'] = tempo_match.group(1).strip()
                    break

            # Find carência (integer)
            for cell in cells[3:]:
                if cell.isdigit():
                    benefit['carencia'] = int(cell)
                    break

            # Find status
            full_row_text = ' '.join(cells)
            if 'Tem direito' in full_row_text and 'Não' not in full_row_text:
                benefit['tem_direito'] = True
            else:
                benefit['tem_direito'] = False

            # Find RMA
            rma_match = re.search(r'R\$\s*([\d.,]+)\s*para', full_row_text)
            if rma_match:
                benefit['melhor_rma'] = f"R$ {rma_match.group(1)}"
            elif benefit['tem_direito']:
                rma_match2 = re.search(r'R\$\s*([\d.,]+)', full_row_text.split('Tem direito')[-1])
                if rma_match2:
                    benefit['melhor_rma'] = f"R$ {rma_match2.group(1)}"

            if benefit.get('tempo_contribuicao'):
                benefits.append(benefit)

    # Fallback: extract from text if tables didn't work
    if not benefits:
        benefits = extract_benefits_from_text(text)

    return benefits


def extract_benefits_from_text(text):
    """Fallback: extract benefits from raw text."""
    benefits = []

    # Simpler pattern that handles multi-line names
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        if 'Aposentadoria por' in line or 'Aposentadoria por' in deduplicate_text(line):
            # Collect the full benefit block (may span 2-3 lines)
            block = line
            for j in range(1, 4):
                if i + j < len(lines):
                    block += ' ' + lines[i + j]

            block = deduplicate_text(block)

            # Extract fields
            tempo_match = re.search(r'(\d+\s*anos?,?\s*\d+\s*m[eê]s(?:es)?\s*e?\s*\d*\s*dias?)', block)
            carencia_match = re.search(r'(\d{2,3})\s+(?:Tem|Não|Sem)', block)
            tem_direito = 'Tem direito' in block
            rma_match = re.search(r'R\$\s*([\d.,]+)\s*para', block)

            if tempo_match:
                benefit = {
                    'tipo': re.search(r'(Aposentadoria[^R$]*?)(?:\s+R\$)', block).group(1).strip() if re.search(r'(Aposentadoria[^R$]*?)(?:\s+R\$)', block) else 'Unknown',
                    'tempo_contribuicao': tempo_match.group(1).strip(),
                    'carencia': int(carencia_match.group(1)) if carencia_match else 0,
                    'tem_direito': tem_direito,
                }
                if rma_match:
                    benefit['melhor_rma'] = f"R$ {rma_match.group(1)}"
                elif not tem_direito:
                    benefit['melhor_rma'] = 'Sem direito'
                benefits.append(benefit)
        i += 1

    return benefits


def extract_contribution_periods(tables, text):
    """Extract contribution periods from tables."""
    periods = []

    for table_info in tables:
        table = table_info['data']
        if not table or len(table) < 2:
            continue

        # Check ALL rows for a header containing Nº + Nome + Início
        header_row_idx = None
        for ridx, row in enumerate(table):
            row_text = ' '.join(str(c or '') for c in row)
            if ('Nome' in row_text and 'Início' in row_text and 'Fim' in row_text) or \
               ('Nº' in row_text and 'Início' in row_text):
                header_row_idx = ridx
                break

        if header_row_idx is None:
            continue

        for row in table[header_row_idx + 1:]:
            if not row or len(row) < 4:
                continue
            # Strip empty cells and clean
            cells = [str(c or '').strip() for c in row]
            # Remove leading empty cells
            while cells and not cells[0]:
                cells = cells[1:]
            # Remove trailing empty cells
            while cells and not cells[-1]:
                cells = cells[:-1]

            if not cells:
                continue

            # First cell should be the sequence number
            try:
                num = int(cells[0])
            except (ValueError, IndexError):
                continue

            # Find dates (DD/MM/YYYY)
            full_row = ' '.join(cells)
            full_row = deduplicate_text(full_row)
            dates = re.findall(r'(\d{2}/\d{2}/\d{4})', full_row)
            if len(dates) < 2:
                continue

            # Find tempo (X anos, Y meses e Z dias)
            tempo_match = re.search(r'(\d+\s*anos?,?\s*\d+\s*m[eê]s(?:es)?\s*e?\s*\d*\s*dias?)', full_row)

            # Find fator
            fator_match = re.search(r'\b(\d+[.,]\d{2})\b', full_row)

            # Name: cell[1] or text between number and first date
            name = cells[1] if len(cells) > 1 else ''
            name = re.sub(r'\s+', ' ', deduplicate_text(name)).strip()

            # Carência: typically the last numeric cell
            carencia = 0
            for c in reversed(cells):
                c_clean = c.strip()
                if c_clean.isdigit():
                    carencia = int(c_clean)
                    break

            period = {
                'numero': num,
                'nome_anotacoes': name,
                'inicio': dates[0],
                'fim': dates[1],
                'fator': float(fator_match.group(1).replace(',', '.')) if fator_match else 1.0,
                'tempo': tempo_match.group(1).strip() if tempo_match else '',
                'carencia': carencia,
            }
            periods.append(period)

    # Fallback: extract from text if tables didn't work well
    if len(periods) < 2:
        text_periods = extract_periods_from_text(text)
        if len(text_periods) > len(periods):
            periods = text_periods

    return periods


def extract_periods_from_text(text):
    """Fallback: extract periods from raw text."""
    periods = []

    # Find the CONTAGEM section
    section_match = re.search(r'CONTAGEM DE TEMPO DE CONTRIBUI', text, re.IGNORECASE)
    if not section_match:
        return periods

    section_text = text[section_match.start():]

    # Find all rows with format: N  NAME  DD/MM/YYYY  DD/MM/YYYY  FACTOR  TIME  CARENCIA
    lines = section_text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Match lines starting with a number
        match = re.match(r'^(\d+)\s+(.+)', line)
        if match:
            num = int(match.group(1))
            rest = match.group(1) + ' ' + match.group(2)

            # May span multiple lines - collect next 2 lines
            for j in range(1, 3):
                if i + j < len(lines) and not re.match(r'^\d+\s+[A-Z]', lines[i + j].strip()):
                    rest += ' ' + lines[i + j].strip()
                else:
                    break

            rest = deduplicate_text(rest)

            dates = re.findall(r'(\d{2}/\d{2}/\d{4})', rest)
            tempo_match = re.search(r'(\d+\s*anos?,?\s*\d+\s*m[eê]s(?:es)?\s*e?\s*\d*\s*dias?)', rest)

            if len(dates) >= 2 and tempo_match:
                # Extract name between number and first date
                name_start = rest.find(str(num)) + len(str(num))
                name_end = rest.find(dates[0])
                name = rest[name_start:name_end].strip()

                # Find fator and carência
                after_dates = rest[rest.find(dates[1]) + 10:]
                fator_match = re.search(r'(\d+[.,]\d+)', after_dates)
                carencia_matches = re.findall(r'\b(\d+)\b', after_dates)

                period = {
                    'numero': num,
                    'nome_anotacoes': name,
                    'inicio': dates[0],
                    'fim': dates[1],
                    'fator': float(fator_match.group(1).replace(',', '.')) if fator_match else 1.0,
                    'tempo': tempo_match.group(1).strip(),
                    'carencia': int(carencia_matches[-1]) if carencia_matches else 0,
                }
                periods.append(period)
        i += 1

    return periods


def extract_marcos_temporais(tables, text):
    """Extract marcos temporais from tables."""
    marcos = []

    for table_info in tables:
        table = table_info['data']
        if not table or len(table) < 2:
            continue

        header = ' '.join(str(c or '') for c in table[0])
        if 'Marco Temporal' not in header:
            continue

        for row in table[1:]:
            if not row or len(row) < 3:
                continue
            cells = [str(c or '').strip() for c in row]
            cells = [deduplicate_text(c) for c in cells]

            marco_name = cells[0]
            if not marco_name or 'Marco' in marco_name:
                continue

            # Pedágio has special format
            if 'Pedágio' in marco_name or 'Pedagio' in marco_name:
                # Pedágio row: "Pedágio (EC 20/98)" + "X anos, Y meses e Z dias"
                full_row = ' '.join(cells)
                tempo_match = re.search(r'(\d+\s*anos?,?\s*\d+\s*m[eê]s(?:es)?\s*e?\s*\d*\s*dias?)', full_row)
                if tempo_match:
                    marcos.append({
                        'marco': marco_name,
                        'tempo_pedagio': tempo_match.group(1).strip(),
                    })
                continue

            # Regular marco: marco, tempo_contribuição, carência, idade, pontos
            marco = {'marco': marco_name}

            # tempo_contribuição (cell 1 or find in any cell)
            for cell in cells[1:]:
                tempo_match = re.search(r'(\d+\s*anos?,?\s*\d+\s*m[eê]s(?:es)?\s*e?\s*\d*\s*dias?)', cell)
                if tempo_match and 'tempo_contribuicao' not in marco:
                    marco['tempo_contribuicao'] = tempo_match.group(1).strip()
                elif tempo_match and 'idade' not in marco:
                    marco['idade'] = tempo_match.group(1).strip()

            # carência
            for cell in cells[2:]:
                if cell.isdigit():
                    marco['carencia'] = int(cell)
                    break

            # pontos
            for cell in cells[-2:]:
                if re.match(r'^[\d.,]+$', cell):
                    try:
                        marco['pontos'] = float(cell.replace(',', '.'))
                    except ValueError:
                        pass
                elif 'inaplic' in cell.lower():
                    marco['pontos'] = 'inaplicável'

            if marco.get('tempo_contribuicao'):
                marcos.append(marco)

    # Fallback: extract from text
    if len(marcos) < 3:
        text_marcos = extract_marcos_from_text(text)
        if len(text_marcos) > len(marcos):
            marcos = text_marcos

    return marcos


def extract_marcos_from_text(text):
    """Fallback: extract marcos from raw text."""
    marcos = []

    section_match = re.search(r'Marco Temporal', text)
    if not section_match:
        return marcos

    section_text = text[section_match.start():]
    # Limit to relevant section
    end_match = re.search(r'Compet[eê]ncias consideradas', section_text[100:])
    if end_match:
        section_text = section_text[:end_match.start() + 100]

    lines = section_text.split('\n')
    for i, line in enumerate(lines):
        line = deduplicate_text(line.strip())

        if line.startswith('Até') or line.startswith('Pedágio'):
            # Collect full block
            block = line
            for j in range(1, 3):
                if i + j < len(lines):
                    next_line = lines[i + j].strip()
                    if not next_line.startswith('Até') and not next_line.startswith('Pedágio') and not next_line.startswith('Compet'):
                        block += ' ' + next_line

            block = deduplicate_text(block)

            if 'Pedágio' in block:
                tempo_match = re.search(r'(\d+\s*anos?,?\s*\d+\s*m[eê]s(?:es)?\s*e?\s*\d*\s*dias?)', block)
                if tempo_match:
                    marcos.append({
                        'marco': re.match(r'([^0-9]+)', block).group(1).strip() if re.match(r'([^0-9]+)', block) else 'Pedágio',
                        'tempo_pedagio': tempo_match.group(1).strip(),
                    })
                continue

            # Extract tempo, carência, idade, pontos
            tempos = re.findall(r'(\d+\s*anos?,?\s*\d+\s*m[eê]s(?:es)?\s*e?\s*\d*\s*dias?)', block)
            integers = re.findall(r'\b(\d{2,3})\b', block)
            pontos_match = re.search(r'(\d+[.,]\d{4}|inaplic[áa]vel)', block, re.IGNORECASE)

            marco_name = block.split(tempos[0])[0].strip() if tempos else block[:60]

            marco = {'marco': marco_name}
            if len(tempos) >= 1:
                marco['tempo_contribuicao'] = tempos[0]
            if len(tempos) >= 2:
                marco['idade'] = tempos[1]
            if integers:
                marco['carencia'] = int(integers[0])
            if pontos_match:
                val = pontos_match.group(1)
                marco['pontos'] = 'inaplicável' if 'inaplic' in val.lower() else float(val.replace(',', '.'))

            if marco.get('tempo_contribuicao'):
                marcos.append(marco)

    return marcos


def extract_spec_from_pdf(pdf_path):
    """Extract complete spec from a Tramitação Inteligente analysis PDF."""
    text, tables = extract_tables_from_pdf(pdf_path)

    spec = {
        'source_pdf': os.path.basename(pdf_path),
        'personal_info': extract_personal_info(text),
        'benefits': extract_benefits_from_tables(tables, text),
        'contribution_periods': extract_contribution_periods(tables, text),
        'marcos_temporais': extract_marcos_temporais(tables, text),
    }

    return spec


def process_all_pdfs(downloads_dir, specs_dir):
    """Process all analysis PDFs and create spec files."""
    os.makedirs(specs_dir, exist_ok=True)

    pdf_files = sorted([f for f in os.listdir(downloads_dir) if f.endswith('_analysis.pdf')])
    print(f"Found {len(pdf_files)} analysis PDFs to process.\n")

    results = {'success': 0, 'failed': 0, 'specs': []}
    total_periods = 0
    total_marcos = 0
    total_benefits = 0

    for pdf_file in pdf_files:
        pdf_path = os.path.join(downloads_dir, pdf_file)
        spec_name = pdf_file.replace('_analysis.pdf', '_spec.json')
        spec_path = os.path.join(specs_dir, spec_name)

        try:
            spec = extract_spec_from_pdf(pdf_path)

            # Link to original CNIS file via meta
            prefix = pdf_file.split('_')[0]
            meta_files = [f for f in os.listdir(specs_dir) if f.startswith(prefix) and f.endswith('_meta.json')]
            if meta_files:
                with open(os.path.join(specs_dir, meta_files[0])) as f:
                    meta = json.load(f)
                spec['cnis_source_file'] = meta.get('cnis_file', '')
                spec['planilha_url'] = meta.get('planilha_url', '')

            # Save spec
            with open(spec_path, 'w', encoding='utf-8') as f:
                json.dump(spec, f, ensure_ascii=False, indent=2)

            n_p = len(spec['contribution_periods'])
            n_m = len(spec['marcos_temporais'])
            n_b = len(spec['benefits'])
            total_periods += n_p
            total_marcos += n_m
            total_benefits += n_b

            print(f"  {pdf_file}: nome={spec['personal_info'].get('nome', '?')}, "
                  f"benefits={n_b}, periods={n_p}, marcos={n_m}")

            results['success'] += 1
            results['specs'].append({
                'file': spec_name,
                'name': spec['personal_info'].get('nome', ''),
                'benefits': n_b,
                'periods': n_p,
                'marcos': n_m,
            })

        except Exception as e:
            print(f"  {pdf_file}: ERROR - {e}")
            results['failed'] += 1

    # Save summary
    summary_path = os.path.join(specs_dir, 'specs_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"SUMMARY: {results['success']} specs created, {results['failed']} failed")
    print(f"Total: {total_benefits} benefits, {total_periods} periods, {total_marcos} marcos")
    print(f"Avg per spec: {total_benefits/max(results['success'],1):.1f} benefits, "
          f"{total_periods/max(results['success'],1):.1f} periods, "
          f"{total_marcos/max(results['success'],1):.1f} marcos")


if __name__ == '__main__':
    project_root = os.path.join(os.path.dirname(__file__), '..')
    downloads_dir = os.path.join(project_root, 'downloads')
    specs_dir = os.path.join(project_root, 'specs')
    process_all_pdfs(downloads_dir, specs_dir)
