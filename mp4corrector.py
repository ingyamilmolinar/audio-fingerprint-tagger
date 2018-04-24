import os
from flask import Flask, request, redirect, url_for, send_from_directory, flash, render_template
from werkzeug.utils import secure_filename
import subprocess
import hashlib

UPLOAD_FOLDER = '/var/www/html/audio-fingerprint-tagger/uploads'
CORRECTED_FOLDER = '/var/www/html/audio-fingerprint-tagger/corrected'
SCRIPT_NAME = '/var/www/html/audio-fingerprint-tagger/src/musicCorrectorWeb.py'
PYTHON_INTERPRETER = '/usr/bin/python3'
# TODO: Read from config file
ALLOWED_EXTENSIONS = set(['m4a'])

app = Flask(__name__)
app.secret_key = 'super secret key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

if __name__ == "__main__":
    app.run(host='0.0.0.0')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # TODO: See if file is already in server
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('info', audiofile=filename))
    return render_template('index.html')


@app.route('/info/<audiofile>')
def info(audiofile):
    customlog = get_logname(audiofile)
    try:
      output = subprocess.check_output([PYTHON_INTERPRETER, SCRIPT_NAME, audiofile, customlog], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
      output = "command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output)
    # TODO: Send back the modified file
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], audiofile))
    except Exception as error:
        app.logger.error("ERROR: File "+os.path.join(app.config['UPLOAD_FOLDER'], audiofile)+" not removed", error)
    try:
        os.remove(os.path.join(app.config['CORRECTED_FOLDER'], audiofile))
    except Exception as error:
        app.logger.error("ERROR: File "+os.path.join(app.config['CORRECTED_FOLDER'], audiofile)+" not removed", error)
    return '''
    <!doctype html>
    <title>File '''+str(audiofile)+''' info</title>
    '''+str(output)

def get_logname(audiofile):
  md5 = getmd5fromfile(audiofile)
  return md5

def getmd5fromfile(filename):
  with open(UPLOAD_FOLDER+'/'+filename, 'rb') as f:
    data = f.read()
    return hashlib.md5(data).hexdigest()
