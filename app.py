from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, send_file
import os
import subprocess
import csv
import logging
import io
import zipfile
import yaml
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# use an environment variable APP_ENV to determine environment. To set the variable in azure, from the console:
# echo 'export APP_ENV=production' >> ~/.bashrc
# source ~/.bashrc
env = os.getenv("APP_ENV", "local")  # default to "local" if not set
if env == "local":
    FRONTEND_ROOT = '/home/steven/code/ESGFrontEnd/'
    BACKEND_ROOT = '/home/steven/code/AutoESG/'
else:
    FRONTEND_ROOT = '/home/azureuser/ESGFrontEnd/'
    BACKEND_ROOT = '/home/azureuser/AutoESG/'

UPLOAD_FOLDER = FRONTEND_ROOT + 'inputs/'
DOWNLOAD_FOLDER = FRONTEND_ROOT + 'outputs/'
APPLICATION = BACKEND_ROOT + 'bin/esg'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER


logging.basicConfig(level=logging.DEBUG)

def zip_files_in_download_folder(zip_filename):
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for root, dirs, files in os.walk(DOWNLOAD_FOLDER):
            for file in files:
                file_path = os.path.join(root, file)
                # Get the relative path of the file with respect to the DOWNLOAD_FOLDER
                relative_path = os.path.relpath(file_path, DOWNLOAD_FOLDER)
                zipf.write(file_path, relative_path)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'config_file' in request.files:
            config_file = request.files['config_file']
            if config_file.filename != '':
                # Check file extension
                if not config_file.filename.lower().endswith('.yaml'):
                    flash('Error: Config file must be a .yaml file', 'danger')
                    return redirect(url_for('index'))

                # Load YAML and validate
                try:
                    config_data = yaml.safe_load(config_file)
                except yaml.YAMLError:
                    flash('Error: Invalid YAML format', 'danger')
                    return redirect(url_for('index'))

                required_fields = {
                    'paths': {
                        'fileNamesWithPaths': False,
                        'input': '/home/steven/code/AutoESG/demo/',
                        'output': '/home/steven/code/AutoESG/demo_outputs/'
                    }
                }

                if 'paths' not in config_data:
                    flash('Error: Missing "paths" section in config file', 'danger')
                    return redirect(url_for('index'))

                paths = config_data['paths']
                if 'fileNamesWithPaths' not in paths or \
                   'input' not in paths or \
                   'output' not in paths:
                    flash('Error: Config file missing required fields in "paths"', 'danger')
                    return redirect(url_for('index'))

                if paths['fileNamesWithPaths'] is True:
                    flash('Error: fileNamesWithPaths cannot be true', 'danger')
                    return redirect(url_for('index'))

                # Overwrite input/output paths
                config_data['paths']['input'] = app.config['UPLOAD_FOLDER']
                config_data['paths']['output'] = app.config['DOWNLOAD_FOLDER']

                # Save the modified YAML to upload folder
                new_config_path = os.path.join(app.config['UPLOAD_FOLDER'], config_file.filename)
                with open(new_config_path, 'w') as f:
                    yaml.safe_dump(config_data, f)

                session['config_file_name'] = config_file.filename
                flash('Config file uploaded and validated successfully', 'success')

        elif 'data_files' in request.files:
            data_files = request.files.getlist('data_files')
            for data_file in data_files:
                if data_file.filename != '':
                    data_file.save(os.path.join(app.config['UPLOAD_FOLDER'], data_file.filename))
            flash('Data files uploaded successfully', 'success')

    config_file_name = session.get('config_file_name')
    return render_template('index.html', config_file_name=config_file_name)

@app.route('/delete_files', methods=['POST'])
def delete_files():
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    session.pop('config_file_name', None)
    flash('All files deleted successfully', 'success')
    return redirect(url_for('index'))

@app.route('/run_app', methods=['POST'])
def run_app():
    config_file_name = session.get('config_file_name')
    if config_file_name:
        # Convert CSV files to Unix format
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if filename.endswith('.csv'):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                subprocess.run(['dos2unix', file_path])

        # Run the economic scenario generator app and capture output
        config_file_path = os.path.join(app.config['UPLOAD_FOLDER'], config_file_name)
        process = subprocess.Popen([APPLICATION, config_file_path],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output, error = process.communicate()
        if process.returncode == 0:
            flash('ESG application executed successfully', 'success')
            session['esg_output'] = output
        else:
            flash('ESG application execution failed', 'danger')
            session['esg_output'] = error
    else:
        flash('Config file is missing', 'danger')
    return redirect(url_for('index'))

@app.route('/output')
def output():
    esg_output = session.get('esg_output', '')
    return render_template('output.html', esg_output=esg_output)

@app.route('/download_outputs')
def download():
    # Create a new zip file of just the DOWNLOAD_FOLDER contents
    zip_path = os.path.join(app.config['DOWNLOAD_FOLDER'], 'outputs.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(DOWNLOAD_FOLDER):
            for file in files:
                file_path = os.path.join(root, file)
                # Exclude the outputs.zip file
                if file_path == zip_path:
                    continue
                # Calculate relative path to maintain folder structure
                arcname = os.path.relpath(file_path, DOWNLOAD_FOLDER)
                zipf.write(file_path, arcname)
    
    # Send the zip file
    return send_file(zip_path,
                    mimetype='application/zip',
                    as_attachment=True,
                    download_name='outputs.zip')

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(host='0.0.0.0', port=8000, debug=True)
