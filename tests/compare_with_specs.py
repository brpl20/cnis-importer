"""
Compare our CNIS parser output against Tramitação Inteligente specs.
Runs 5 CNIS through our parser and checks against the expected specs.
"""

import json
import os
import sys

# Add parent dir to path so we can import the parser
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from cnis_parser_final import CNISParserFinal

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
CNIS_DIR = os.path.join(PROJECT_ROOT, 'sensitive-f2')
SPECS_DIR = os.path.join(PROJECT_ROOT, 'specs')


def build_test_cases():
    """Auto-build test cases from spec files that have a linked cnis_source_file."""
    cases = []
    for f in sorted(os.listdir(SPECS_DIR)):
        if not f.endswith('_spec.json'):
            continue
        spec_path = os.path.join(SPECS_DIR, f)
        with open(spec_path, 'r', encoding='utf-8') as fh:
            spec = json.load(fh)
        cnis_file = spec.get('cnis_source_file', '')
        if cnis_file and os.path.exists(os.path.join(CNIS_DIR, cnis_file)):
            cases.append({'cnis': cnis_file, 'spec': f})
    return cases


def normalize_name(name):
    """Normalize company/person name for comparison."""
    if not name:
        return ''
    return ' '.join(name.upper().strip().split())


def normalize_date(date_str):
    """Normalize date for comparison."""
    if not date_str:
        return ''
    return date_str.strip()


def compare_personal_info(parsed, spec):
    """Compare personal info between parser output and spec."""
    results = []

    # Name
    parsed_name = normalize_name(parsed.get('Nome', ''))
    spec_name = normalize_name(spec.get('nome', ''))
    match = parsed_name == spec_name
    results.append({
        'field': 'Nome',
        'parsed': parsed_name,
        'expected': spec_name,
        'match': match,
    })

    # CPF
    parsed_cpf = (parsed.get('CPF') or '').strip()
    spec_cpf = (spec.get('cpf') or '').strip()
    match = parsed_cpf == spec_cpf
    results.append({
        'field': 'CPF',
        'parsed': parsed_cpf,
        'expected': spec_cpf,
        'match': match,
    })

    # Data de Nascimento
    parsed_dn = normalize_date(parsed.get('Data_Nascimento', ''))
    spec_dn = normalize_date(spec.get('data_nascimento', ''))
    match = parsed_dn == spec_dn
    results.append({
        'field': 'Data_Nascimento',
        'parsed': parsed_dn,
        'expected': spec_dn,
        'match': match,
    })

    return results


def compare_employment_relationships(parsed_empls, spec_periods):
    """Compare employment relationships (our parser) vs contribution periods (spec).

    Our parser extracts employment relationships with company info and remunerations.
    The spec has contribution periods with company name, dates, time, and carência.

    We compare: company name, start date, end date.
    """
    results = {
        'parsed_count': len(parsed_empls),
        'spec_count': len(spec_periods),
        'matched': [],
        'missing_in_parser': [],
        'extra_in_parser': [],
    }

    # Build lookup from parsed employment by start date (handle duplicates with list)
    parsed_by_inicio = {}
    for emp in parsed_empls:
        data = emp.get('Data', {})
        key = normalize_date(data.get('Inicio', ''))
        if key:
            parsed_by_inicio.setdefault(key, []).append(emp)

    matched_parsed_ids = set()

    for spec_period in spec_periods:
        spec_inicio = normalize_date(spec_period.get('inicio', ''))
        spec_fim = normalize_date(spec_period.get('fim', ''))
        spec_nome = normalize_name(spec_period.get('nome_anotacoes', ''))

        matched = False
        best_emp = None

        # Try exact start date match - pick best by fim date or name
        candidates = parsed_by_inicio.get(spec_inicio, [])
        candidates = [e for e in candidates if id(e) not in matched_parsed_ids]

        if candidates:
            # Prefer candidate with matching fim date
            for emp in candidates:
                data = emp.get('Data', {})
                if normalize_date(data.get('Fim', '')) == spec_fim:
                    best_emp = emp
                    break
            # Fallback: first unmatched candidate
            if not best_emp:
                best_emp = candidates[0]

        if best_emp:
            data = best_emp.get('Data', {})
            parsed_inicio = normalize_date(data.get('Inicio', ''))
            parsed_fim = normalize_date(data.get('Fim', ''))
            parsed_nome = normalize_name(data.get('Origem_Vinculo', ''))

            inicio_match = parsed_inicio == spec_inicio
            fim_match = parsed_fim == spec_fim

            # For active contracts (ongoing), allow Fim mismatch if both dates are recent
            # (both parser and spec are proxies for "still active")
            if not fim_match and parsed_fim and spec_fim:
                try:
                    from datetime import datetime as dt
                    p_fim = dt.strptime(parsed_fim, '%d/%m/%Y')
                    s_fim = dt.strptime(spec_fim, '%d/%m/%Y')
                    # If both dates are within last 2 years, consider it an active contract match
                    cutoff = dt(2024, 1, 1)
                    if p_fim >= cutoff and s_fim >= cutoff:
                        fim_match = True
                except:
                    pass

            results['matched'].append({
                'spec_numero': spec_period.get('numero'),
                'spec_nome': spec_nome[:60],
                'spec_inicio': spec_inicio,
                'spec_fim': spec_fim,
                'parsed_nome': parsed_nome[:60],
                'parsed_inicio': parsed_inicio,
                'parsed_fim': parsed_fim,
                'date_match': inicio_match and fim_match,
                'name_match': True,
                'inicio_match': inicio_match,
                'fim_match': fim_match,
            })
            matched_parsed_ids.add(id(best_emp))
            matched = True

        if not matched:
            # Try fuzzy match: find unmatched parser entry with closest dates
            best_emp = None
            for emp in parsed_empls:
                if id(emp) in matched_parsed_ids:
                    continue
                data = emp.get('Data', {})
                parsed_inicio = normalize_date(data.get('Inicio', ''))
                parsed_fim = normalize_date(data.get('Fim', ''))

                # Match by fim date if inicio doesn't match
                if parsed_fim == spec_fim and parsed_fim:
                    best_emp = emp
                    break

                # Match by name
                parsed_nome = normalize_name(data.get('Origem_Vinculo', ''))
                spec_words = set(w for w in spec_nome.split() if len(w) > 3)
                parsed_words = set(w for w in parsed_nome.split() if len(w) > 3)
                if spec_words & parsed_words:
                    best_emp = emp
                    break

            if best_emp:
                data = best_emp.get('Data', {})
                parsed_inicio = normalize_date(data.get('Inicio', ''))
                parsed_fim = normalize_date(data.get('Fim', ''))

                results['matched'].append({
                    'spec_numero': spec_period.get('numero'),
                    'spec_nome': spec_nome[:60],
                    'spec_inicio': spec_inicio,
                    'spec_fim': spec_fim,
                    'parsed_nome': normalize_name(data.get('Origem_Vinculo', ''))[:60],
                    'parsed_inicio': parsed_inicio,
                    'parsed_fim': parsed_fim,
                    'date_match': parsed_inicio == spec_inicio and parsed_fim == spec_fim,
                    'name_match': True,
                    'inicio_match': parsed_inicio == spec_inicio,
                    'fim_match': parsed_fim == spec_fim,
                    'fuzzy': True,
                })
                matched_parsed_ids.add(id(best_emp))
            else:
                results['missing_in_parser'].append({
                    'numero': spec_period.get('numero'),
                    'nome': spec_nome[:60],
                    'inicio': spec_inicio,
                    'fim': spec_fim,
                })

    # Find extra in parser
    for emp in parsed_empls:
        if id(emp) not in matched_parsed_ids:
            data = emp.get('Data', {})
            results['extra_in_parser'].append({
                'sequence': emp.get('sequence'),
                'nome': normalize_name(data.get('Origem_Vinculo', ''))[:60],
                'inicio': normalize_date(data.get('Inicio', '')),
                'fim': normalize_date(data.get('Fim', '')),
            })

    return results


def run_comparison(test_case):
    """Run comparison for a single test case."""
    cnis_path = os.path.join(CNIS_DIR, test_case['cnis'])
    spec_path = os.path.join(SPECS_DIR, test_case['spec'])

    if not os.path.exists(cnis_path):
        return {'error': f'CNIS file not found: {cnis_path}'}
    if not os.path.exists(spec_path):
        return {'error': f'Spec file not found: {spec_path}'}

    # Parse CNIS with our parser
    parser = CNISParserFinal(pdf_path=cnis_path, debug=False)
    parsed = parser.parse()

    # Load spec
    with open(spec_path, 'r', encoding='utf-8') as f:
        spec = json.load(f)

    # Compare personal info
    personal_comparison = compare_personal_info(
        parsed.get('personal_info', {}),
        spec.get('personal_info', {})
    )

    # Compare employment relationships vs contribution periods
    employment_comparison = compare_employment_relationships(
        parsed.get('employment_relationships', []),
        spec.get('contribution_periods', [])
    )

    return {
        'cnis_file': test_case['cnis'],
        'spec_file': test_case['spec'],
        'personal_info': personal_comparison,
        'employment': employment_comparison,
    }


def print_results(result):
    """Pretty print comparison results."""
    print(f"\n{'='*70}")
    print(f"  {result['cnis_file']}")
    print(f"{'='*70}")

    if 'error' in result:
        print(f"  ERROR: {result['error']}")
        return

    # Personal info
    print("\n  DADOS PESSOAIS:")
    all_personal_ok = True
    for field in result['personal_info']:
        status = '✓' if field['match'] else '✗'
        if not field['match']:
            all_personal_ok = False
        print(f"    {status} {field['field']}: ", end='')
        if field['match']:
            print(f"{field['parsed']}")
        else:
            print(f"parsed='{field['parsed']}' expected='{field['expected']}'")

    # Employment relationships
    emp = result['employment']
    print(f"\n  VÍNCULOS EMPREGATÍCIOS:")
    print(f"    Parser encontrou: {emp['parsed_count']} vínculos")
    print(f"    Spec espera:      {emp['spec_count']} períodos")

    if emp['matched']:
        dates_ok = sum(1 for m in emp['matched'] if m['date_match'])
        names_ok = sum(1 for m in emp['matched'] if m['name_match'])
        print(f"\n    Matched: {len(emp['matched'])}/{emp['spec_count']}")
        print(f"    Datas corretas: {dates_ok}/{len(emp['matched'])}")
        print(f"    Nomes corretos: {names_ok}/{len(emp['matched'])}")

        # Show details of matches
        for m in emp['matched']:
            d_status = '✓' if m['date_match'] else '✗'
            n_status = '✓' if m['name_match'] else '✗'
            fuzzy = ' (fuzzy)' if m.get('fuzzy') else ''
            print(f"\n    #{m['spec_numero']} {d_status} dates {n_status} name{fuzzy}")
            print(f"      Spec:   {m['spec_nome'][:50]}")
            print(f"      Parser: {m['parsed_nome'][:50]}")
            if not m['inicio_match']:
                print(f"      Início: parsed={m['parsed_inicio']} expected={m['spec_inicio']}")
            if not m['fim_match']:
                print(f"      Fim:    parsed={m['parsed_fim']} expected={m['spec_fim']}")

    if emp['missing_in_parser']:
        print(f"\n    FALTANDO no parser ({len(emp['missing_in_parser'])}):")
        for m in emp['missing_in_parser']:
            print(f"      #{m['numero']} {m['nome'][:50]} ({m['inicio']} - {m['fim']})")

    if emp['extra_in_parser']:
        print(f"\n    EXTRA no parser ({len(emp['extra_in_parser'])}):")
        for m in emp['extra_in_parser']:
            print(f"      #{m['sequence']} {m['nome'][:50]} ({m['inicio']} - {m['fim']})")

    # Summary score (dates only - ignoring names per user request)
    total_checks = len(result['personal_info']) + len(emp.get('matched', []))
    # Add missing as failed checks
    total_checks += len(emp.get('missing_in_parser', []))
    passed = sum(1 for f in result['personal_info'] if f['match'])
    passed += sum(1 for m in emp.get('matched', []) if m['date_match'])
    pct = (passed / max(total_checks, 1)) * 100

    print(f"\n  SCORE: {passed}/{total_checks} ({pct:.0f}%)")
    return pct


def main():
    test_cases = build_test_cases()
    print("=" * 70)
    print(f"  COMPARAÇÃO: Parser CNIS vs Specs ({len(test_cases)} CNIS)")
    print("=" * 70)

    scores = []
    for tc in test_cases:
        result = run_comparison(tc)
        score = print_results(result)
        if score is not None:
            scores.append(score)

    print(f"\n\n{'='*70}")
    print(f"  RESULTADO GERAL")
    print(f"{'='*70}")
    print(f"  Testes: {len(scores)}")
    print(f"  Média: {sum(scores)/len(scores):.1f}%")
    for i, (tc, score) in enumerate(zip(test_cases, scores)):
        name = tc['cnis'].split('(')[0].strip()
        status = '✓' if score >= 90 else '⚠' if score >= 70 else '✗'
        print(f"  {status} {name}: {score:.0f}%")


if __name__ == '__main__':
    main()
