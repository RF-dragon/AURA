import argparse
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
import os

# =======================================
# Paths
# =======================================
DATA_X = "data/X.npy"
DATA_Y = "data/y.npy"
MODEL_FILE = "model/model.pkl"

# =======================================
# Feature names
# =======================================
FEATURE_NAMES = [
    "lux_left", "lux_right",
    "sound_left", "sound_right",
    "pir_motion", "lux_diff", "sound_diff"
]
NUM_FEATURES = len(FEATURE_NAMES)
TIMESTEPS = 30


# =======================================
# Load dataset
# =======================================
def load_data():
    if not os.path.exists(DATA_X) or not os.path.exists(DATA_Y):
        raise FileNotFoundError("Dataset not found. Make sure X.npy and y.npy exist in /data")

    X = np.load(DATA_X)
    y = np.load(DATA_Y, allow_pickle=True)

    if X.shape[1] != TIMESTEPS * NUM_FEATURES:
        raise ValueError("Dataset shape mismatch. Expected 210 features per sample.")

    X_seq = X.reshape(-1, TIMESTEPS, NUM_FEATURES)
    return X, X_seq, y


# =======================================
# Load model
# =======================================
def load_model():
    if not os.path.exists(MODEL_FILE):
        raise FileNotFoundError("Model file not found. Train the model first.")
    return pickle.load(open(MODEL_FILE, "rb"))


# =======================================
# Plot: Feature Distributions
# =======================================
def plot_feature_histograms(X_seq):
    plt.figure(figsize=(14, 10))

    for i, name in enumerate(FEATURE_NAMES):
        plt.subplot(3, 3, i + 1)
        values = X_seq[:, :, i].flatten()
        plt.hist(values, bins=40)
        plt.title(name)

    plt.tight_layout()
    plt.savefig("histogram.png")


# =======================================
# Plot: Correlation Matrix
# =======================================
def plot_correlation_matrix(X_seq):
    X_flat = X_seq.mean(axis=1)

    corr = np.corrcoef(X_flat.T)

    plt.figure(figsize=(9, 7))
    sns.heatmap(
        corr,
        annot=True,
        cmap="coolwarm",
        xticklabels=FEATURE_NAMES,
        yticklabels=FEATURE_NAMES
    )
    plt.title("Correlation Matrix")
    plt.savefig("correlation.png")


# =======================================
# Plot: Single Sample Time-Series
# =======================================
def plot_sample_timeseries(X_seq, index):
    if index < 0 or index >= len(X_seq):
        raise IndexError(f"Sample index out of range: 0–{len(X_seq)-1}")

    sample = X_seq[index]

    plt.figure(figsize=(14, 7))
    for i in range(NUM_FEATURES):
        plt.plot(sample[:, i], label=FEATURE_NAMES[i])

    plt.legend()
    plt.title(f"Sample #{index} — 30-Frame Time Series")
    plt.yscale('log')
    plt.xlabel("Timestep")
    plt.ylabel("Value")
    plt.savefig("sample_timeseries.png")


# =======================================
# Plot: Model Loss Curve
# =======================================
def plot_loss_curve(model):
    if not hasattr(model, "loss_curve_"):
        raise AttributeError("Model does not contain loss_curve_. Train it with MLPClassifier.")

    plt.plot(model.loss_curve_)
    plt.title("Training Loss Curve")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.grid()
    plt.savefig("training_loss.png")


# =======================================
# Plot: Weight Heatmap
# Input Layer → First Hidden Layer
# =======================================
def plot_weight_heatmap(model):
    layer1 = model.coefs_[0]  # Shape: (210 inputs) → (32 neurons)

    plt.figure(figsize=(12, 6))
    sns.heatmap(layer1, cmap="viridis")
    plt.title("Input → Layer1 Weight Heatmap")
    plt.xlabel("Neuron Index")
    plt.ylabel("Input Feature Index (0–209)")
    plt.savefig("weight_heatmap.png")

def plot_model_accuracy(model, X, y):
    from sklearn.metrics import accuracy_score, confusion_matrix

    # Predict on full dataset
    y_pred = model.predict(X)

    # Compute accuracy
    acc = accuracy_score(y, y_pred)
    print(f"\nModel Accuracy: {acc*100:.2f}%")

    # Save accuracy text
    with open("model_accuracy.txt", "w") as f:
        f.write(f"Accuracy: {acc*100:.2f}%\n")

    # Confusion matrix
    cm = confusion_matrix(y, y_pred, labels=np.unique(y))

    plt.figure(figsize=(8, 6))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=np.unique(y),
        yticklabels=np.unique(y)
    )
    plt.xlabel("Predicted")
    plt.ylabel("True Label")
    plt.title("Confusion Matrix")
    plt.savefig("confusion_matrix.png")

    # Accuracy bar plot
    plt.figure(figsize=(6, 4))
    plt.bar(["Accuracy"], [acc])
    plt.ylim(0, 1)
    plt.title("Overall Model Accuracy")
    plt.ylabel("Accuracy")
    plt.savefig("accuracy_bar.png")


def show_label_distribution(y):
    from collections import Counter

    counts = Counter(y)
    print("\n=== Label Distribution ===")
    for label, count in counts.items():
        print(f"{label}: {count} samples")

    # Plot distribution
    labels = list(counts.keys())
    values = list(counts.values())

    plt.figure(figsize=(8, 5))
    plt.bar(labels, values)
    plt.title("Label Distribution")
    plt.xlabel("Label")
    plt.ylabel("Count")
    plt.savefig("label_distribution.png")
    print("\nSaved plot: label_distribution.png")



# =======================================
# Command-line Interface
# =======================================
def main():
    parser = argparse.ArgumentParser(description="Visualization tools for your NN dataset and model.")

    parser.add_argument("--hist", action="store_true", help="Plot feature histograms")
    parser.add_argument("--corr", action="store_true", help="Plot feature correlation matrix")
    parser.add_argument("--sample", type=int, help="Plot time-series of specific training sample")
    parser.add_argument("--loss", action="store_true", help="Plot model training loss curve")
    parser.add_argument("--weights", action="store_true", help="Plot weight heatmap for model")
    parser.add_argument("--accuracy", action="store_true", help="Plot model accuracy and confusion matrix")
    parser.add_argument("--labels", action="store_true", help="Show dataset label counts")


    args = parser.parse_args()

    X = None
    X_seq = None
    y = None
    model = None

    # Load dataset if any visualization needs it
    if args.hist or args.corr or args.sample is not None or args.accuracy or args.labels:
        X, X_seq, y = load_data()

    # Load model if needed
    if args.loss or args.weights or args.accuracy:
        model = load_model()

    # Execute commands
    if args.hist:
        plot_feature_histograms(X_seq)

    if args.corr:
        plot_correlation_matrix(X_seq)

    if args.sample is not None:
        plot_sample_timeseries(X_seq, args.sample)

    if args.loss:
        plot_loss_curve(model)

    if args.weights:
        plot_weight_heatmap(model)

    if args.accuracy:
        plot_model_accuracy(model, X, y)

    if args.labels:
        show_label_distribution(y)



if __name__ == "__main__":
    main()
