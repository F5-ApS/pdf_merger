import os
from flask import Flask, request, send_file, render_template_string
import fitz  # PyMuPDF
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configure folders
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
PROCESSED_FOLDER = os.path.join(BASE_DIR, 'processed')
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

@app.route('/')
def upload_form():
    with open(os.path.join(BASE_DIR, 'upload.html')) as file:
        return render_template_string(file.read())

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'template' not in request.files or 'survey' not in request.files:
        return 'Missing files', 400

    template = request.files['template']
    survey = request.files['survey']

    # Ensure secure filenames for the uploaded files
    template_filename = secure_filename(template.filename)
    survey_filename = secure_filename(survey.filename)

    template_path = os.path.join(UPLOAD_FOLDER, template_filename)
    survey_path = os.path.join(UPLOAD_FOLDER, survey_filename)
    output_path = os.path.join(PROCESSED_FOLDER, 'survey_with_template_overlay.pdf')

    # Save uploaded files
    template.save(template_path)
    survey.save(survey_path)

    # Process the PDFs
    overlay_pdfs(template_path, survey_path, output_path)

    # Serve the processed file
    return send_file(output_path, as_attachment=True)

if __name__ == '__main__':
    # Use a production-ready WSGI server like Gunicorn or uWSGI for deployment
    from waitress import serve
    serve(app, host='0.0.0.0', port=8030)
