from flask import Flask, request, jsonify
import numpy as np
import os
import pickle
from sklearn.neural_network import MLPClassifier

app = Flask(__name__)

DATA_X = "data/X.npy"
DATA_Y = "data/y.npy"
MODEL_FILE = "model/model.pkl"

# ============================
#   Utility: Load dataset
# ============================

def load_dataset():
    if os.path.exists(DATA_X) and os.path.exists(DATA_Y):
        X = np.load(DATA_X)
        y = np.load(DATA_Y, allow_pickle=True)   # ← Fix
        return X, y
    return np.zeros((0, 210)), np.array([], dtype=str)   # 30 samples × 7 features = 210

def save_dataset(X, y):
    np.save(DATA_X, X)
    np.save(DATA_Y, y)

def load_model():
    if os.path.exists(MODEL_FILE):
        with open(MODEL_FILE, "rb") as f:
            return pickle.load(f)
    return None

def save_model(model):
    with open(MODEL_FILE, "wb") as f:
        pickle.dump(model, f)

# ============================
#   /status — save training data
# ============================

@app.post("/status")
def status():
    content = request.json
    mode = content["mode"]           # "study_mode"
    data = content["data"]           # 30 × [int(lux1), int(lux2), int(n1), int(n2), int(motion), int(lux_diff), int(noise_diff)]

    # Flatten into 210-length vector
    flat = np.array(data).flatten()  # shape (210,)

    if flat.shape[0] != 210:
        return jsonify({"error": f"Expected 210 features, got {flat.shape[0]}"}), 400
    
    # Load old dataset
    X, y = load_dataset()

    # Add new example
    X = np.vstack([X, flat])
    y = np.hstack([y, mode])

    save_dataset(X, y)

    return jsonify({"message": "Saved", "count": len(y)})

# ============================
#   /train — trains NN
# ============================

@app.post("/train")
def train():
    X, y = load_dataset()

    if len(y) < 30:
        return jsonify({"error": "Not enough training samples"}), 400

    print("Training model with", len(X), "samples...")

    model = MLPClassifier(
        hidden_layer_sizes=(32, 16),
        max_iter=500
    )

    model.fit(X, y)
    save_model(model)

    return jsonify({"message": "Model trained"})

# ============================
#   /get-mode — inference
# ============================

@app.post("/get-mode")
def get_mode():
    model = load_model()
    if model is None:
        return jsonify({"mode": "study"})

    data = request.json["data"]  # 30 samples
    flat = np.array(data).flatten().reshape(1, -1)

    prediction = model.predict(flat)[0]
    return jsonify({"mode": prediction})

# ============================
#   Start server
# ============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
