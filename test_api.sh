#!/bin/bash

echo "==================================="
echo "CNIS Parser API - Test Script"
echo "==================================="
echo ""

echo "1. Health Check"
echo "-----------------------------------"
curl -X GET http://localhost:8000/health
echo -e "\n"

echo "2. Parse Summary (CNIS1.pdf)"
echo "-----------------------------------"
curl -X POST -F "file=@sensitive/CNIS1.pdf" http://localhost:8000/parse/summary
echo -e "\n"

echo "3. Full Parse (CNIS1.pdf)"
echo "-----------------------------------"
curl -X POST -F "file=@sensitive/CNIS1.pdf" http://localhost:8000/parse > /tmp/cnis_full_parse.json
echo "Full results saved to /tmp/cnis_full_parse.json"
echo -e "\n"

echo "Test complete!"
