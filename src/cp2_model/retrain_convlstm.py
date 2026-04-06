"""
═══════════════════════════════════════════════════════════════════════════════
TRAK-AI KDS — WP2: Conv-LSTM Retraining (Architecture v2)
═══════════════════════════════════════════════════════════════════════════════
Fixes the Conv-LSTM underperformance on wheat by:
  1. Removing second MaxPooling (preserves temporal resolution: 30→15 instead of 30→7)
  2. Using smaller Conv1D filters with padding='causal' (respects time ordering)
  3. Adding Bidirectional LSTM for better context capture
  4. Only retrains Conv-LSTM models, keeps LSTM and XGBoost as-is

Run: python retrain_convlstm.py
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import (
    Conv1D, MaxPooling1D, LSTM, Dense, Dropout, BatchNormalization,
    Input, Bidirectional
)
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

SEED = 42
np.random.seed(SEED)
tf.random.set_seed(SEED)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

EPOCHS = 150
BATCH_SIZE = 32
TEST_RATIO = 0.2


def build_conv_lstm_v2(n_timesteps, n_features):
    """
    Improved Conv-LSTM v2:
    - Single MaxPooling (30→15 instead of 30→7)
    - Causal padding (respects temporal ordering)
    - Bidirectional first LSTM (captures both forward and backward patterns)
    - Slightly wider first Conv1D for better feature extraction
    """
    model = Sequential([
        Input(shape=(n_timesteps, n_features)),

        # Single Conv block with causal padding
        Conv1D(filters=64, kernel_size=5, activation="relu", padding="causal"),
        BatchNormalization(),
        MaxPooling1D(pool_size=2),  # 30 → 15 (not 30 → 7)
        Dropout(0.2),

        # Bidirectional LSTM captures both directions
        Bidirectional(LSTM(64, return_sequences=True)),
        Dropout(0.3),
        LSTM(32, return_sequences=False),
        Dropout(0.3),

        Dense(16, activation="relu"),
        Dropout(0.2),
        Dense(1, activation="linear"),
    ])

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=5e-4),
        loss="mse",
        metrics=["mae"],
    )
    return model


def train(prefix, label):
    print(f"\n{'━' * 60}")
    print(f"  Retraining Conv-LSTM v2: {label}")
    print(f"{'━' * 60}")

    X = np.load(os.path.join(BASE_DIR, f"X_{prefix}.npy"))
    y = np.load(os.path.join(BASE_DIR, f"y_{prefix}.npy"))

    split = int(len(X) * (1 - TEST_RATIO))
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    print(f"   Train: {X_train.shape[0]}, Val: {X_val.shape[0]}")
    print(f"   Input: ({X.shape[1]}, {X.shape[2]})")

    model = build_conv_lstm_v2(X.shape[1], X.shape[2])
    model.summary(print_fn=lambda x: print(f"   {x}"))

    model_path = os.path.join(BASE_DIR, f"model_convlstm_{prefix}.keras")

    callbacks = [
        EarlyStopping(monitor="val_loss", patience=20,
                      restore_best_weights=True, mode="min", verbose=1),
        ModelCheckpoint(filepath=model_path, monitor="val_loss",
                        save_best_only=True, mode="min", verbose=1),
        ReduceLROnPlateau(monitor="val_loss", factor=0.5,
                          patience=10, min_lr=1e-6, verbose=1),
    ]

    history = model.fit(
        X_train, y_train,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        validation_data=(X_val, y_val),
        callbacks=callbacks,
        verbose=1,
    )

    best_val_loss = min(history.history["val_loss"])
    best_val_mae = min(history.history["val_mae"])
    epochs_run = len(history.history["loss"])

    print(f"\n   [DONE] {label} Conv-LSTM v2:")
    print(f"   Best val_loss: {best_val_loss:.6f}")
    print(f"   Best val_mae:  {best_val_mae:.6f}")
    print(f"   Epochs run:    {epochs_run}")
    print(f"   Model saved:   {model_path}")

    return best_val_loss, best_val_mae


def main():
    print("=" * 60)
    print("  TRAK-AI KDS — Conv-LSTM v2 Retraining")
    print("=" * 60)

    results = {}
    for prefix, label in [("wheat", "Wheat"), ("sunflower", "Sunflower")]:
        loss, mae = train(prefix, label)
        results[label] = {"val_loss": loss, "val_mae": mae}

    # Update training_results.json
    results_path = os.path.join(BASE_DIR, "training_results.json")
    if os.path.exists(results_path):
        with open(results_path) as f:
            all_results = json.load(f)
        for crop_label, metrics in results.items():
            if crop_label in all_results:
                for entry in all_results[crop_label]:
                    if "Conv-LSTM" in entry.get("model_name", ""):
                        entry["best_val_loss"] = metrics["val_loss"]
                        entry["best_val_mae"] = metrics["val_mae"]
                        entry["model_name"] += " (v2)"
        with open(results_path, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\n[UPDATED] {results_path}")

    print(f"\n{'=' * 60}")
    print("  RETRAINING COMPLETE")
    print(f"{'=' * 60}")
    print("  Now run: python evaluate_cp2.py")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()