import os
import uuid
import logging
from flask import Flask, request, jsonify, send_file
import fitz  # PyMuPDF
from werkzeug.utils import secure_filename
from waitress import serve
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
UPLOAD_FOLDER = os.path.abspath('uploads')
PROCESSED_FOLDER = os.path.abspath('processed')
ALLOWED_EXTENSIONS = {'pdf'}
MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # Limit to 32 MB per file

# Create directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask configuration
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH


def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def overlay_pdfs(template_path, survey_path, output_path):
    """Overlay survey PDF pages on a template PDF."""
    try:
        template_pdf = fitz.open(template_path)
        survey_pdf = fitz.open(survey_path)
        output_pdf = fitz.open()

        template_page = template_pdf[0]  # Use the first page as the template

        for i in range(len(survey_pdf)):
            survey_page = survey_pdf[i]
            if i % 2 == 1:  # Even-indexed pages
                new_page = output_pdf.new_page(width=template_page.rect.width, height=template_page.rect.height)
                new_page.show_pdf_page(template_page.rect, template_pdf, 0)
                new_page.show_pdf_page(survey_page.rect, survey_pdf, i)
            else:  # Odd-indexed pages
                output_pdf.insert_pdf(survey_pdf, from_page=i, to_page=i)

        output_pdf.save(output_path)
        output_pdf.close()
        logger.info(f"Output PDF saved at: {output_path}")

    except Exception as e:
        logger.error(f"Error during PDF overlay: {str(e)}")
        raise


@app.route('/process', methods=['POST'])
def process_pdfs():
    """Endpoint to handle PDF processing."""
    if 'template' not in request.files or 'survey' not in request.files:
        return jsonify({'error': 'Both "template" and "survey" files are required.'}), 400

    template = request.files['template']
    survey = request.files['survey']

    if not (allowed_file(template.filename) and allowed_file(survey.filename)):
        return jsonify({'error': 'Only PDF files are allowed.'}), 400

    try:
        # Save files with unique names to prevent conflicts
        template_filename = secure_filename(f"{uuid.uuid4()}_{template.filename}")
        survey_filename = secure_filename(f"{uuid.uuid4()}_{survey.filename}")
        template_path = os.path.join(UPLOAD_FOLDER, template_filename)
        survey_path = os.path.join(UPLOAD_FOLDER, survey_filename)

        template.save(template_path)
        survey.save(survey_path)

        logger.info(f"Template saved at: {template_path}")
        logger.info(f"Survey saved at: {survey_path}")

        # Process PDFs
        output_filename = f"{uuid.uuid4()}_overlayed.pdf"
        output_path = os.path.join(PROCESSED_FOLDER, output_filename)
        overlay_pdfs(template_path, survey_path, output_path)

        if not os.path.exists(output_path):
            return jsonify({'error': 'Failed to create the processed PDF file.'}), 500

        # Serve the processed file
        response = send_file(output_path, as_attachment=True)

        # Use a safe deletion approach
        def safe_delete(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
            except Exception as e:
                logger.error(f"Error deleting file {file_path}: {str(e)}")

        # Schedule file deletions
        from threading import Timer
        Timer(5, safe_delete, [template_path]).start()
        Timer(5, safe_delete, [survey_path]).start()
        Timer(5, safe_delete, [output_path]).start()

        return response

    except Exception as e:
        logger.error(f"Error processing PDFs: {str(e)}")
        return jsonify({'error': f"Error processing PDFs: {str(e)}"}), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File size exceeds the allowed limit of 32MB.'}), 413

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=8080)