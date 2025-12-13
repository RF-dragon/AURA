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
  NumPy array containing flattened feature vectors  
  Shape: `(num_samples, timesteps × num_features)`

- **y.npy**  
  NumPy array containing corresponding labels for each sample

These files persist across training sessions and grow as more data is collected.

---

## Model Training Server

The backend server is responsible for:

- Accepting labeled training samples
- Training a neural network classifier
- Saving trained models to disk
- Serving inference requests to the ESP32

### Key Files

- **server.py**  
  Implements training and inference endpoints.

- **app.py**  
  Entry point for starting the backend server.

---

## Machine Learning Model

- Model Type: Multilayer Perceptron (MLP)
- Input: Flattened time-series sensor windows
- Output: Discrete class labels representing system states
- Training Strategy:
  - Batch learning
  - Validation split
  - Early stopping to prevent overfitting

---

## Model Artifacts (`/model`)

- **model.pkl**  
  Serialized trained model used for inference by the server.

---

## Visualization & Analysis Tools

The project includes tools to inspect and evaluate the dataset and trained model.

- Feature distributions
- Feature correlation analysis
- Time-series visualization of individual samples
- Training loss curves
- Confusion matrix and accuracy metrics
- Dataset label distribution

### Key File

- **visualize.py**  
  Command-line utility for generating plots and diagnostics.

---

# End-to-End Data Flow Summary

1. ESP32 collects sensor data over time
2. Data is labeled and transmitted to the backend server
3. Server stores the dataset
4. A neural network model is trained offline
5. ESP32 sends inference requests
6. Server responds with predicted system states

---

# Future Work

- Online or incremental learning
- Over-the-air model updates
- Additional sensors and modalities
- More advanced model architectures
- Real-time adaptive feedback loops

---

# Notes

- Sensor noise and environmental variability affect model performance
- Dataset balance impacts classification accuracy
- The system assumes stable network connectivity during training and inference
