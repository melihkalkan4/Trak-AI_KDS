import numpy as np
import os
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import (
    Conv1D, MaxPooling1D, LSTM, Dense, Dropout, BatchNormalization
)
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from sklearn.model_selection import train_test_split

# Tekrarlanabilirlik için seed
SEED = 42
np.random.seed(SEED)
tf.random.set_seed(SEED)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def build_and_train_convlstm(X_train, y_train, X_val, y_val, model_name):
    model = Sequential([
        # CNN Bloğu: BatchNorm eklendi, eğitimi kararlı kılar
        Conv1D(filters=64, kernel_size=3, activation='relu',
               input_shape=(X_train.shape[1], X_train.shape[2])),
        BatchNormalization(),
        MaxPooling1D(pool_size=2),
        Dropout(0.2),

        # LSTM Bloğu
        LSTM(100, return_sequences=True),
        Dropout(0.2),
        LSTM(50, return_sequences=False),
        Dropout(0.2),

        # Çıktı öncesi Dense: Dropout eklendi
        Dense(32, activation='relu'),
        Dropout(0.2),          # ← EKSİK OLAN BU SATIRDI
        Dense(1, activation='linear')
    ])

    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    model.summary()

    model_path = os.path.join(BASE_DIR, model_name)

    callbacks = [
        EarlyStopping(monitor='val_loss', patience=15,
                      restore_best_weights=True, mode='min'),
        ModelCheckpoint(filepath=model_path, monitor='val_loss',
                        save_best_only=True, mode='min', verbose=1),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5,   # ← YENİ
                          patience=7, min_lr=1e-6, verbose=1)
    ]

    print(f"\n--- {model_name} Eğitimi Başlıyor ---")
    history = model.fit(
        X_train, y_train,
        epochs=100,
        batch_size=32,
        validation_data=(X_val, y_val),
        callbacks=callbacks,
        verbose=1
    )
    return model, history   # ← ARTIK KULLAN


def load_and_split(file_prefix):
    X = np.load(os.path.join(BASE_DIR, f'X_{file_prefix}.npy'))
    y = np.load(os.path.join(BASE_DIR, f'y_{file_prefix}.npy'))
    # Zaman serisi sızıntısını önlemek için shuffle=False
    return train_test_split(X, y, test_size=0.2, shuffle=False)


if __name__ == "__main__":
    print("Veriler yükleniyor...")

    configs = [
        ("wheat",     "model_wheat.keras",     "Buğday"),
        ("sunflower",  "model_sunflower.keras", "Ayçiçeği"),
    ]

    results = {}
    for prefix, model_name, label in configs:
        try:
            X_tr, X_val, y_tr, y_val = load_and_split(prefix)
            print(f"\n{label} — Eğitim: {X_tr.shape}, Doğrulama: {X_val.shape}")
            model, history = build_and_train_convlstm(
                X_tr, y_tr, X_val, y_val, model_name
            )
            results[label] = history
        except FileNotFoundError:
            print(f"{label} verisi bulunamadı. Önce preprocessing_cp2.py çalıştırın.")

    print("\nTüm eğitim süreçleri tamamlandı!")