# Project Overview


This project is an AIoT system built around an ESP32 microcontroller that collects environmental sensor data, performs local interaction and state management, and communicates with a backend server for machine learning–based classification. The system is designed to learn patterns in environmental conditions and user behavior, then use a trained model to make intelligent decisions in real time.


At a high level:
- The ESP32 collects multi-sensor data over time
- Labeled data is sent to a backend server
- A neural network model is trained on the collected data
- The ESP32 queries the trained model for inference


---


# System Architecture


The system is composed of three main components:


- **ESP32 Device**
  - Sensor data acquisition
  - User interaction (buttons, display)
  - Local state and alarm logic
  - Communication with the backend server


- **Backend Server**
  - Receives and stores labeled sensor data
  - Trains and saves machine learning models
  - Serves inference requests


- **Machine Learning Model**
  - Learns temporal patterns from sensor data
  - Classifies environmental or operational states


---


# ESP32 Folder (`/ESP32`)


## Purpose


This folder contains all firmware and device-side logic that runs directly on the ESP32 microcontroller. It is responsible for sensor interfacing, user interaction, local state management, and communication with the backend server.


---


## Responsibilities


- Interfacing with hardware sensors (light, sound, motion)
- Handling physical button inputs
- Managing device modes and alarm states
- Displaying information on an OLED screen
- Connecting to Wi-Fi and maintaining network state
- Sending sensor data and labels to the backend
- Receiving model inference results


---


## Main Execution Flow


1. Device boots and initializes hardware
2. Wi-Fi credentials are loaded or provisioned
3. Sensors are sampled continuously
4. Sensor readings are aggregated into fixed-length time windows
5. Data is optionally labeled based on user input or device state
6. Labeled data is transmitted to the backend server
7. Inference results are received and applied to device behavior


---


## Module Breakdown


- **main.py**  
  Entry point for the ESP32 application. Coordinates initialization, sensor sampling, and system logic.


- **boot.py**  
  Runs at device startup to prepare the system environment.


- **drivers.py**  
  Low-level hardware drivers and sensor interfaces.


- **buttons.py**  
  Handles physical button inputs and debouncing.


- **alarm_system.py**  
  Manages alarm states, triggers, and transitions.


- **menu_page.py**  
  Implements the on-device menu and user interface logic.


- **wifi_manager.py**  
  Handles Wi-Fi provisioning, connection, and reconnection logic.


- **voice_ws.py**  
  Manages WebSocket-based or voice-related communication.


- **ssd1306.py**  
  OLED display driver.


- **networks.json**  
  Persistent storage for Wi-Fi credentials.


---


# Model Training Folder (`/model_training`)


## Purpose


This folder contains all backend logic related to data storage, model training, evaluation, and visualization. It enables the system to learn from collected sensor data and produce trained models for inference.


---


## Data Collection Pipeline


- Sensor data is received from the ESP32 as labeled time windows
- Each sample consists of multiple features over a fixed number of timesteps
- Data is validated, flattened, and stored persistently for training


---


## Dataset Storage (`/data`)


- **X.npy**  
  Shape: `(num_samples, 210)`  
  Flattened time-series feature vectors


- **y.npy**  
  Shape: `(num_samples,)`  
  String labels representing system modes


These files persist across training sessions.


---


## Backend Training & Inference Server


### File: `server.py`


The backend server is implemented using **Flask** and provides REST endpoints for dataset collection, training, and inference.


### Endpoints


#### `POST /status`
Stores labeled training data sent from the ESP32.


- Input:
  - `mode`: label string (e.g., `STUDY`, `SLEEP`)
  - `data`: 30 × 7 sensor window
- Behavior:
  - Flattens data to 210 features
  - Appends to `X.npy` and `y.npy`


---


#### `POST /train`
Trains a neural network classifier using all collected data.


**Model Details (Updated):**
- Model: `sklearn.neural_network.MLPClassifier`
- Architecture: 210 → 128 → 64 → 32 → output
- Activation: ReLU
- Optimizer: Adam
- Learning rate: Adaptive
- Batch size: 32
- Max epochs: 1000
- Regularization: L2 (`alpha=1e-4`)
- Reproducibility: Fixed random seed
- Verbose training output enabled


The trained model is serialized to: `/model/model.pkl`


---


#### `POST /get-mode`
Performs inference using the trained model.


- Input:
  - 30-sample sensor window
- Output:
  - Predicted system mode label


If no trained model exists, a default mode is returned.


## Voice Interface Application (`app.py`)


### Purpose


`app.py` implements a voice-controlled interface that allows users to change the ESP32’s operating mode using natural language speech. It serves as a human-friendly control layer between the user and the embedded device.


---


### Responsibilities


- Capture live audio from a microphone
- Transcribe speech into text using OpenAI Whisper
- Use a Large Language Model (LLM) to classify user intent
- Convert free-form speech into a strict mode label
- Send structured commands to the ESP32 over a socket connection
- Display feedback to the user through a web UI


---


### Voice Processing Pipeline


1. User speaks a voice command (e.g., “set study mode”)
2. Audio is captured via a Gradio web interface
3. Whisper transcribes the audio into text
4. Transcription is sent to an LLM (via Poe API)
5. The LLM outputs a single mode label:
   - `AUTO_MODE`
   - `STUDY`
   - `RELAX`
   - `SLEEP`
   - `AWAY`
   - `ERROR`
6. The selected mode and transcription are sent to the ESP32
7. The ESP32 responds with a status message


---


### Technologies Used


- **Gradio** — Web-based UI for audio input and output
- **Whisper** — Speech-to-text transcription
- **LLM (via Poe API)** — Natural language intent classification
- **Sockets** — Direct TCP communication with the ESP32


---


### Why This Matters


This component enables:
- Hands-free control of the ESP32
- Natural language interaction instead of rigid commands
- A clean separation between human intent and embedded logic
- Easy expansion to new voice commands or modes


---


## Machine Learning Model


- Type: Multilayer Perceptron (MLP)
- Input: Flattened time-series sensor windows
- Output: Discrete system mode labels
- Training:
  - Batch learning
  - Validation split
  - Adaptive learning rate
  - Regularization to reduce overfitting


---


## Model Artifacts (`/model`)


- **model.pkl**  
  Serialized neural network used for inference


---


## Visualization & Analysis Tools


The project includes tooling to inspect and evaluate both data and models.


Capabilities include:
- Feature histograms
- Feature correlation matrices
- Time-series sample plots
- Label distribution analysis
- Confusion matrix and accuracy metrics
- Model diagnostics


### Key File


- **visualize.py**  
  Command-line analysis and plotting utility


---


# End-to-End Data Flow


1. ESP32 collects sensor data  
2. Data is labeled and sent to server  
3. Server stores dataset  
4. Neural network is trained  
5. ESP32 requests inference  
6. Server returns predicted mode  


---


# Future Work


- Online / incremental learning
- Model confidence estimation
- OTA model updates
- More advanced architectures (CNN/LSTM)
- Additional sensors and modalities
- Closed-loop adaptive control


---


# Notes


- Sensor noise affects model quality
- Dataset balance is critical
- Stable network connectivity is assumed
- Model performance improves with more labeled data

