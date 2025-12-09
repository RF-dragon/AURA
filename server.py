import os
import pickle

import torch
import whisper
from flask import Flask, render_template, request

from nn import MLP

app = Flask(__name__)
mlp = None # Only load model when used to accelerate boot up.
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
whisper_model = None

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/status', methods=['POST'])
def status():
    data = request.get_json()
    print(f'Data received: {data}')
    label = data['mode']
    data.pop('mode')
    if 'device' in data:
        data.pop('device')
    if 'data_study.pkl' in os.listdir():
        with open('data_study.pkl', 'rb') as f:
            cur_data = pickle.load(f)
    else:
        cur_data = []
    cur_data.append((label, data))
    with open('data_study.pkl', 'wb') as f:
        pickle.dump(cur_data, f)
    print('Data successfully saved.')
    return ''

@app.route('/get-mode', methods=['POST'])
def get_mode():
    global mlp
    data = request.get_json()['data']
    print(f'Data received: {data}')
    if mlp is None:
        mlp = MLP()
        mlp.load_state_dict()
        mlp.to(device)
    label = mlp.predict(data)
    return label

@app.route('/vc-command', methods=['POST'])
def vc_command():
    global whisper_model
    if whisper_model is None:
        whisper_model = whisper.load_model('tiny.en')
        ...

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000)