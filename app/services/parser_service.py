"""Wraps CNISParserFinal with proper temp file handling."""

import os
import sys
import tempfile
import logging

# Add project root to path so we can import the parser
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from cnis_parser_final import CNISParserFinal

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Raised when the parser fails to extract data."""
    pass


def parse_pdf(file_bytes: bytes) -> dict:
    """Parse a CNIS PDF from bytes. Returns the raw parser dict."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        parser = CNISParserFinal(pdf_path=tmp_path, debug=False)
        result = parser.parse()

        if not result or not result.get('personal_info'):
            raise ParseError("Could not extract data from PDF")

        return result

    except ParseError:
        raise
    except Exception as e:
        logger.exception("Parser failed")
        raise ParseError(f"Failed to parse CNIS PDF: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
