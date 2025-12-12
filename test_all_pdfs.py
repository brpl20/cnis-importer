#!/usr/bin/env python3
"""
Test script to run CNIS parser on all PDF files in ./sensitive directory
"""

import os
import json
from pathlib import Path
from cnis_parser_final import CNISParserFinal

def test_all_pdfs():
    sensitive_dir = Path("./sensitive")
    pdf_files = list(sensitive_dir.glob("*.pdf"))

    print(f"Found {len(pdf_files)} PDF files in {sensitive_dir}")
    print("="*80)

    results_summary = []

    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n{'='*80}")
        print(f"Processing {i}/{len(pdf_files)}: {pdf_file.name}")
        print(f"{'='*80}")

        try:
            # Parse the PDF
            parser = CNISParserFinal(pdf_path=str(pdf_file), debug=False)
            results = parser.parse()

            # Create output filename
            output_filename = f"output_{pdf_file.stem}.json"
            output_path = sensitive_dir / output_filename

            # Export results
            parser.export_to_json(str(output_path))

            # Summary
            num_relationships = len(parser.employment_relationships)
            personal_info = parser.personal_info

            summary = {
                'file': pdf_file.name,
                'status': 'SUCCESS',
                'personal_info': personal_info,
                'num_employment_relationships': num_relationships,
                'output_file': output_filename
            }

            print(f"\n✓ SUCCESS")
            print(f"  Name: {personal_info.get('Nome', 'N/A')}")
            print(f"  CPF: {personal_info.get('CPF', 'N/A')}")
            print(f"  NIT: {personal_info.get('NIT', 'N/A')}")
            print(f"  Employment Relationships: {num_relationships}")

            # Show first few relationships
            if num_relationships > 0:
                print(f"\n  First 3 relationships:")
                for emp in parser.employment_relationships[:3]:
                    seq = emp['sequence']
                    origem = emp['Data'].get('Origem_Vinculo', 'Unknown')[:60]
                    num_remu = len(emp.get('Remuneracoes', []))
                    print(f"    Seq {seq}: {origem} ({num_remu} remunerações)")

            results_summary.append(summary)

        except Exception as e:
            error_summary = {
                'file': pdf_file.name,
                'status': 'ERROR',
                'error': str(e)
            }
            results_summary.append(error_summary)
            print(f"\n✗ ERROR: {e}")

    # Final summary
    print(f"\n{'='*80}")
    print("FINAL SUMMARY")
    print(f"{'='*80}")

    successful = sum(1 for r in results_summary if r['status'] == 'SUCCESS')
    failed = sum(1 for r in results_summary if r['status'] == 'ERROR')

    print(f"\nTotal files processed: {len(pdf_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    print(f"\n{'='*80}")
    print("DETAILED RESULTS")
    print(f"{'='*80}")

    for result in results_summary:
        print(f"\n{result['file']}:")
        if result['status'] == 'SUCCESS':
            print(f"  ✓ {result['num_employment_relationships']} employment relationships")
            print(f"  Output: {result['output_file']}")
        else:
            print(f"  ✗ Error: {result['error']}")

    # Save summary
    summary_path = sensitive_dir / "test_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(results_summary, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*80}")
    print(f"Summary saved to: {summary_path}")
    print(f"{'='*80}")

if __name__ == "__main__":
    test_all_pdfs()
