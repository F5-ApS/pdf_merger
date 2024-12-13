import os
import uuid
from flask import Flask, request, send_file, jsonify
import fitz  # PyMuPDF
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def overlay_pdfs(template_path, survey_path, output_path):
    # Open the template and survey PDFs
    template_pdf = fitz.open(template_path)
    survey_pdf = fitz.open(survey_path)

    # Prepare a new PDF to save the output
    output_pdf = fitz.open()

    # Get the background template page
    template_page = template_pdf[0]  # Assuming the first page is the template

    # Iterate through the survey pages and overlay for every second page
    for i in range(len(survey_pdf)):
        survey_page = survey_pdf[i]
        if i % 2 == 1:  # For every second page
            # Create a new page based on the template size
            new_page = output_pdf.new_page(width=template_page.rect.width, height=template_page.rect.height)
            
            # Insert the template as background
            new_page.show_pdf_page(template_page.rect, template_pdf, 0)
            
            # Overlay the survey page content
            new_page.show_pdf_page(survey_page.rect, survey_pdf, i)
        else:
            # Directly insert the survey page for odd-numbered pages
            output_pdf.insert_pdf(survey_pdf, from_page=i, to_page=i)

    # Save the final output
    output_pdf.save(output_path)
    output_pdf.close()

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'template' not in request.files or 'survey' not in request.files:
        return jsonify({'status': 'error', 'message': 'Missing files'}), 400

    template = request.files['template']
    survey = request.files['survey']

    template_path = os.path.join(UPLOAD_FOLDER, template.filename)
    survey_path = os.path.join(UPLOAD_FOLDER, survey.filename)
    
    # Generate a unique file name for the output
    file_id = str(uuid.uuid4())
    output_path = os.path.join(PROCESSED_FOLDER, f'survey_with_template_overlay_{file_id}.pdf')

    # Save uploaded files
    template.save(template_path)
    survey.save(survey_path)

    # Process the PDFs
    try:
        overlay_pdfs(template_path, survey_path, output_path)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

    # Return the file identifier to the client
    return jsonify({'status': 'success', 'file_id': file_id}), 200

@app.route('/api/download/<file_id>', methods=['GET'])
def download_file(file_id):
    output_path = os.path.join(PROCESSED_FOLDER, f'survey_with_template_overlay_{file_id}.pdf')

    if not os.path.exists(output_path):
        return jsonify({'status': 'error', 'message': 'File not found'}), 404

    return send_file(output_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
