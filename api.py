"""
CNIS Parser API - Flask REST API
Provides endpoints to upload and parse CNIS PDF files
"""

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
from pathlib import Path
from cnis_parser_final import CNISParserFinal
import tempfile

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "service": "CNIS Parser API"}), 200

@app.route('/parse', methods=['POST'])
def parse_cnis():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are allowed"}), 400
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        debug_mode = request.args.get('debug', 'false').lower() == 'true'
        parser = CNISParserFinal(pdf_path=tmp_path, debug=debug_mode)
        results = parser.parse()
        
        os.unlink(tmp_path)
        
        return jsonify({
            "success": True,
            "data": {
                "personal_info": results['personal_info'],
                "employment_relationships": results['employment_relationships']
            },
            "summary": {
                "total_employment_relationships": len(results['employment_relationships']),
                "total_remunerations": sum(len(emp.get('Remuneracoes', [])) for emp in results['employment_relationships'])
            }
        }), 200
    
    except Exception as e:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return jsonify({"error": str(e)}), 500

@app.route('/parse/summary', methods=['POST'])
def parse_cnis_summary():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are allowed"}), 400
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        parser = CNISParserFinal(pdf_path=tmp_path, debug=False)
        results = parser.parse()
        
        os.unlink(tmp_path)
        
        summary = {
            "personal_info": results['personal_info'],
            "total_employment_relationships": len(results['employment_relationships']),
            "employment_summary": []
        }
        
        for emp in results['employment_relationships']:
            summary['employment_summary'].append({
                "sequence": emp['sequence'],
                "origem_vinculo": emp['Data'].get('Origem_Vinculo', ''),
                "tipo_filiado": emp['Data'].get('Tipo_Filiado_Vinculo', ''),
                "inicio": emp['Data'].get('Inicio'),
                "fim": emp['Data'].get('Fim'),
                "total_remunerations": len(emp.get('Remuneracoes', [])),
                "metadata": emp.get('Metadata', {})
            })
        
        return jsonify({
            "success": True,
            "data": summary
        }), 200
    
    except Exception as e:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("CNIS Parser API")
    print("=" * 60)
    print("Endpoints:")
    print("  GET  /health          - Health check")
    print("  POST /parse           - Parse CNIS PDF (full data)")
    print("  POST /parse/summary   - Parse CNIS PDF (summary only)")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=8000)
