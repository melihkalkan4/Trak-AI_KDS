"""
===============================================================================
TRAK-AI KDS  -  WP2: Comparative Model Training
===============================================================================
Four architectures with RESIDUAL DELTA prediction.
All custom layers use @register_keras_serializable.
No Lambda layers — full Keras 3.x save/load compatibility.

Run:  python train_models_cp2.py
===============================================================================
"""

import os, json, numpy as np, joblib

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import (
    Input, LSTM, Dense, Dropout, Conv1D, MaxPooling1D,
    BatchNormalization, Bidirectional, Add, Layer,
)
from tensorflow.keras.callbacks import (
    EarlyStopping, ModelCheckpoint, ReduceLROnPlateau,
)
from tensorflow.keras.saving import register_keras_serializable
from xgboost import XGBRegressor

SEED = 42
np.random.seed(SEED)
tf.random.set_seed(SEED)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

EPOCHS       = 200
BATCH_SIZE   = 32
PATIENCE_ES  = 25
PATIENCE_LR  = 10
TEST_RATIO   = 0.20
DELTA_SCALE  = 0.30

_NDVI_IDX = None

def _ndvi_idx():
    global _NDVI_IDX
    if _NDVI_IDX is None:
        with open(os.path.join(BASE_DIR, "feature_names.json")) as fh:
            _NDVI_IDX = json.load(fh).index("NDVI_int")
    return _NDVI_IDX


# ═════════════════════════════════════════════════════════════════════════════
# CUSTOM LAYERS — all registered for Keras 3.x serialization
# ═════════════════════════════════════════════════════════════════════════════

@register_keras_serializable(package="trak_ai")
class SelfAttention(Layer):
    """Bahdanau-style attention over LSTM time-steps."""

    def __init__(self, units=64, **kw):
        super().__init__(**kw)
        self.units = units

    def build(self, input_shape):
        d = int(input_shape[-1])
        self.W = self.add_weight(name="att_W", shape=(d, self.units),
                                 initializer="glorot_uniform")
        self.b = self.add_weight(name="att_b", shape=(self.units,),
                                 initializer="zeros")
        self.v = self.add_weight(name="att_v", shape=(self.units, 1),
                                 initializer="glorot_uniform")

    def call(self, x):
        score = tf.nn.tanh(tf.matmul(x, self.W) + self.b)
        weights = tf.nn.softmax(tf.matmul(score, self.v), axis=1)
        return tf.reduce_sum(x * weights, axis=1)

    def get_config(self):
        config = super().get_config()
        config["units"] = self.units
        return config


@register_keras_serializable(package="trak_ai")
class ExtractLastNDVI(Layer):
    """Extracts last_ndvi = input[:, -1, ndvi_idx:ndvi_idx+1]."""

    def __init__(self, ndvi_idx, **kw):
        super().__init__(**kw)
        self.ndvi_idx = ndvi_idx

    def call(self, x):
        return x[:, -1, self.ndvi_idx : self.ndvi_idx + 1]

    def compute_output_shape(self, input_shape):
        return (input_shape[0], 1)

    def get_config(self):
        config = super().get_config()
        config["ndvi_idx"] = self.ndvi_idx
        return config


@register_keras_serializable(package="trak_ai")
class ScaleDelta(Layer):
    """Scales delta by a fixed factor: output = input * scale."""

    def __init__(self, scale=0.3, **kw):
        super().__init__(**kw)
        self.scale = scale

    def call(self, x):
        return x * self.scale

    def compute_output_shape(self, input_shape):
        return input_shape

    def get_config(self):
        config = super().get_config()
        config["scale"] = self.scale
        return config


# ═════════════════════════════════════════════════════════════════════════════
# MODEL BUILDERS
# ═════════════════════════════════════════════════════════════════════════════

def _residual_head(inp, core_output):
    """Shared output head: Dense→tanh→scale→Add(last_ndvi)."""
    idx = _ndvi_idx()
    last_ndvi = ExtractLastNDVI(idx, name="last_ndvi")(inp)
    x = Dense(32, activation="relu")(core_output)
    x = Dropout(0.2)(x)
    delta = Dense(1, activation="tanh", name="delta")(x)
    scaled = ScaleDelta(DELTA_SCALE, name="scale_delta")(delta)
    return Add(name="residual_add")([last_ndvi, scaled])


def build_attention_lstm(T, F):
    inp = Input(shape=(T, F))
    x = LSTM(128, return_sequences=True)(inp)
    x = Dropout(0.3)(x)
    x = LSTM(64, return_sequences=True)(x)
    x = Dropout(0.3)(x)
    x = SelfAttention(64, name="self_attn")(x)
    out = _residual_head(inp, x)
    m = Model(inp, out, name="Attention_LSTM")
    m.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=5e-4),
              loss="mse", metrics=["mae"])
    return m


def build_conv_lstm(T, F):
    inp = Input(shape=(T, F))
    x = Conv1D(64, 5, activation="relu", padding="causal")(inp)
    x = BatchNormalization()(x)
    x = MaxPooling1D(2)(x)
    x = Dropout(0.2)(x)
    x = Bidirectional(LSTM(64, return_sequences=True))(x)
    x = Dropout(0.3)(x)
    x = LSTM(32)(x)
    x = Dropout(0.3)(x)
    out = _residual_head(inp, x)
    m = Model(inp, out, name="Conv_LSTM")
    m.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=5e-4),
              loss="mse", metrics=["mae"])
    return m


def build_lstm(T, F):
    inp = Input(shape=(T, F))
    x = LSTM(100, return_sequences=True)(inp)
    x = Dropout(0.3)(x)
    x = LSTM(50)(x)
    x = Dropout(0.3)(x)
    out = _residual_head(inp, x)
    m = Model(inp, out, name="LSTM_Baseline")
    m.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=5e-4),
              loss="mse", metrics=["mae"])
    return m


# ═════════════════════════════════════════════════════════════════════════════
# TRAINING
# ═════════════════════════════════════════════════════════════════════════════

def _callbacks(path):
    return [
        EarlyStopping(monitor="val_loss", patience=PATIENCE_ES,
                      restore_best_weights=True, verbose=1),
        ModelCheckpoint(path, monitor="val_loss",
                        save_best_only=True, verbose=1),
        ReduceLROnPlateau(monitor="val_loss", factor=0.5,
                          patience=PATIENCE_LR, min_lr=1e-6, verbose=1),
    ]


def train_keras(model, X_tr, y_tr, X_v, y_v, name, path):
    print(f"\n   --- {name} ---")
    print(f"   train {X_tr.shape[0]}  val {X_v.shape[0]}")
    model.summary(print_fn=lambda s: print(f"   {s}"))
    h = model.fit(X_tr, y_tr, validation_data=(X_v, y_v),
                  epochs=EPOCHS, batch_size=BATCH_SIZE,
                  callbacks=_callbacks(path), verbose=1)
    bl = min(h.history["val_loss"])
    bm = min(h.history["val_mae"])
    ep = len(h.history["loss"])
    print(f"   [DONE] val_loss={bl:.6f}  val_mae={bm:.6f}  epochs={ep}")

    # Verify save/load works
    loaded = tf.keras.models.load_model(path)
    print(f"   [VERIFIED] Model save/load OK")

    return dict(model_name=name, best_val_loss=float(bl),
                best_val_mae=float(bm), epochs_run=ep, model_path=path)


def train_xgboost(X_tr, y_tr, X_v, y_v, name, path):
    print(f"\n   --- {name} ---")
    print(f"   train {X_tr.shape[0]} ({X_tr.shape[1]} feat)  val {X_v.shape[0]}")
    mdl = XGBRegressor(
        n_estimators=500, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        reg_alpha=0.1, reg_lambda=1.0, min_child_weight=3,
        random_state=SEED, early_stopping_rounds=30, verbosity=1)
    mdl.fit(X_tr, y_tr, eval_set=[(X_v, y_v)], verbose=50)
    joblib.dump(mdl, path)
    pred = mdl.predict(X_v)
    mse = float(np.mean((pred - y_v) ** 2))
    mae = float(np.mean(np.abs(pred - y_v)))
    print(f"   [DONE] val_mse={mse:.6f}  val_mae={mae:.6f}")
    return dict(model_name=name, best_val_loss=mse,
                best_val_mae=mae, model_path=path)


def load_crop(prefix):
    X     = np.load(os.path.join(BASE_DIR, f"X_{prefix}.npy"))
    y     = np.load(os.path.join(BASE_DIR, f"y_{prefix}.npy"))
    X_xgb = np.load(os.path.join(BASE_DIR, f"X_xgb_{prefix}.npy"))
    s   = int(len(X) * (1 - TEST_RATIO))
    idx = _ndvi_idx()
    last_ndvi = X[:, -1, idx]
    y_delta   = y - last_ndvi
    return dict(
        X_tr=X[:s], X_v=X[s:], y_tr=y[:s], y_v=y[s:],
        Xxgb_tr=X_xgb[:s], Xxgb_v=X_xgb[s:],
        ydelta_tr=y_delta[:s], ydelta_v=y_delta[s:],
        last_ndvi_v=last_ndvi[s:], T=X.shape[1], F=X.shape[2])


def main():
    from sklearn.metrics import r2_score

    print("=" * 60)
    print("  TRAK-AI KDS  -  WP2 Training (Residual + Attention)")
    print("=" * 60)

    crops = [dict(label="Wheat", prefix="wheat"),
             dict(label="Sunflower", prefix="sunflower")]
    all_results = {}

    for crop in crops:
        lbl, pfx = crop["label"], crop["prefix"]
        print(f"\n{'━' * 60}")
        print(f"  CROP: {lbl.upper()}")
        print(f"{'━' * 60}")
        d = load_crop(pfx)
        naive_r2 = r2_score(d["y_v"], d["last_ndvi_v"])
        print(f"   samples  train={d['X_tr'].shape[0]}  val={d['X_v'].shape[0]}")
        print(f"   shape    ({d['T']}, {d['F']})")
        print(f"   naive R2 {naive_r2:.4f}")

        res = []
        res.append(train_keras(build_attention_lstm(d["T"], d["F"]),
            d["X_tr"], d["y_tr"], d["X_v"], d["y_v"],
            f"Attention-LSTM ({lbl})",
            os.path.join(BASE_DIR, f"model_attention_lstm_{pfx}.keras")))

        res.append(train_keras(build_conv_lstm(d["T"], d["F"]),
            d["X_tr"], d["y_tr"], d["X_v"], d["y_v"],
            f"Conv-LSTM ({lbl})",
            os.path.join(BASE_DIR, f"model_convlstm_{pfx}.keras")))

        res.append(train_keras(build_lstm(d["T"], d["F"]),
            d["X_tr"], d["y_tr"], d["X_v"], d["y_v"],
            f"LSTM ({lbl})",
            os.path.join(BASE_DIR, f"model_lstm_{pfx}.keras")))

        res.append(train_xgboost(
            d["Xxgb_tr"], d["ydelta_tr"], d["Xxgb_v"], d["ydelta_v"],
            f"XGBoost ({lbl})",
            os.path.join(BASE_DIR, f"model_xgb_{pfx}.pkl")))

        all_results[lbl] = res

        print(f"\n   {'─'*55}")
        print(f"   {lbl}  (naive R2={naive_r2:.4f})")
        print(f"   {'─'*55}")
        print(f"   {'Model':<35} {'MSE':>10} {'MAE':>10}")
        for r in res:
            print(f"   {r['model_name']:<35} "
                  f"{r['best_val_loss']:>10.6f} {r['best_val_mae']:>10.6f}")

    out = os.path.join(BASE_DIR, "training_results.json")
    with open(out, "w") as fh:
        json.dump(all_results, fh, indent=2, default=float)
    print(f"\n[SAVED] {out}")
    print(f"\n{'=' * 60}")
    print("  TRAINING COMPLETE  -  8 models saved & verified")
    print(f"{'=' * 60}")
    print("  Next: python evaluate_cp2.py")
    print(f"{'=' * 60}\n")

if __name__ == "__main__":
    main()