"""
SIGMA A 프로젝트 - 모델 로딩 및 실시간 예측 엔진 (CHAMPION 모델 포함)
"""

import os
import math
import numpy as np
import tensorflow as tf
from typing import Dict, Any

from tensorflow.keras import Model, regularizers
from tensorflow.keras.layers import (
    Layer, LayerNormalization, Dropout, Dense, GlobalAveragePooling1D,
    MultiHeadAttention, Input, LSTM, GRU, Conv1D, Add, Activation,
    ZeroPadding1D, Reshape
)

from tensorflow.keras.models import load_model

from .config import (
    MODEL_WEIGHTS,
    SEQUENCE_LENGTH,
)

# ======================================================================
# 1) 커스텀 Attention 레이어
# ======================================================================

class Attention(Layer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build(self, input_shape):
        self.W = self.add_weight(
            name="att_weight",
            shape=(input_shape[-1], 1),
            initializer="glorot_uniform"
        )
        self.b = self.add_weight(
            name="att_bias",
            shape=(input_shape[1], 1),
            initializer="zeros"
        )
        super().build(input_shape)

    def call(self, x):
        et = tf.squeeze(tf.tanh(tf.matmul(x, self.W) + self.b), axis=-1)
        at = tf.nn.softmax(et, axis=-1)
        at = tf.expand_dims(at, axis=-1)
        return tf.reduce_sum(x * at, axis=1)


# ======================================================================
# 2) PositionalEncoding / TransformerEncoder
# ======================================================================

class PositionalEncoding(Layer):
    def __init__(self, position, d_model, **kwargs):
        super().__init__(**kwargs)
        self.position = int(position)
        self.d_model = int(d_model)
        self.pos_encoding = self._positional_encoding(self.position, self.d_model)

    def get_config(self):
        cfg = super().get_config()
        cfg.update({"position": self.position, "d_model": self.d_model})
        return cfg

    def _get_angles(self, position, i, d_model):
        angle_rates = 1.0 / tf.pow(
            10000.0, (2 * (i // 2)) / tf.cast(d_model, tf.float32)
        )
        return tf.cast(position, tf.float32) * angle_rates

    def _positional_encoding(self, position, d_model):
        angle_rads = self._get_angles(
            tf.range(position, dtype=tf.float32)[:, tf.newaxis],
            tf.range(d_model, dtype=tf.float32)[tf.newaxis, :],
            d_model,
        )
        sines = tf.math.sin(angle_rads[:, 0::2])
        cosines = tf.math.cos(angle_rads[:, 1::2])
        return tf.concat([sines, cosines], axis=-1)[tf.newaxis, ...]

    def call(self, inputs):
        return inputs + self.pos_encoding[:, : tf.shape(inputs)[1], :]


class TransformerEncoder(Layer):
    def __init__(self, d_model, num_heads, dff, rate=0.1, **kwargs):
        super().__init__(**kwargs)
        self.d_model = d_model
        self.num_heads = num_heads
        self.dff = dff
        self.rate = rate

        self.mha = MultiHeadAttention(key_dim=d_model, num_heads=num_heads)
        self.ffn = tf.keras.Sequential(
            [Dense(dff, activation="relu"), Dense(d_model)]
        )
        self.norm1 = LayerNormalization(epsilon=1e-6)
        self.norm2 = LayerNormalization(epsilon=1e-6)
        self.drop1 = Dropout(rate)
        self.drop2 = Dropout(rate)

    def call(self, x, training=False):
        attn = self.mha(x, x, x)
        attn = self.drop1(attn, training=training)
        out1 = self.norm1(x + attn)
        ffn_out = self.ffn(out1)
        ffn_out = self.drop2(ffn_out, training=training)
        return self.norm2(out1 + ffn_out)


# ======================================================================
# 3) 7개 기본 모델 + CHAMPION 모델
# ======================================================================

L2_REG = 1e-5

def build_lstm_with_attention_reg(input_shape):
    inp = Input(shape=input_shape)
    x = LSTM(64, return_sequences=True, dropout=0.2,
             kernel_regularizer=regularizers.l2(L2_REG))(inp)
    x = Attention()(x)
    out = Dense(1)(x)
    return Model(inp, out, name="lstm_attention_reg")


def build_gru_with_attention_reg(input_shape):
    inp = Input(shape=input_shape)
    x = GRU(64, return_sequences=True, dropout=0.2,
            kernel_regularizer=regularizers.l2(L2_REG))(inp)
    x = Attention()(x)
    out = Dense(1)(x)
    return Model(inp, out, name="gru_attention_reg")


def build_transformer_model_reg(input_shape, d_model=64, num_heads=4, dff=128):
    inp = Input(shape=input_shape)
    x = Dense(d_model)(inp)
    x = PositionalEncoding(input_shape[0], d_model)(x)
    for _ in range(2):
        x = TransformerEncoder(d_model, num_heads, dff)(x)
    x = GlobalAveragePooling1D()(x)
    out = Dense(1)(x)
    return Model(inp, out, name="transformer_reg")


def _tcn_block(x, filters, kernel_size=3, dilation_rate=1):
    h = Conv1D(filters, kernel_size, padding="causal",
               dilation_rate=dilation_rate)(x)
    h = Activation("relu")(h)
    h = Conv1D(filters, kernel_size, padding="causal",
               dilation_rate=dilation_rate)(h)
    if x.shape[-1] != filters:
        x = Conv1D(filters, 1, padding="same")(x)
    return Activation("relu")(Add()([x, h]))


def build_tcn_model_reg(input_shape, filters=64, levels=4):
    inp = Input(shape=input_shape)
    x = inp
    for i in range(levels):
        x = _tcn_block(x, filters, dilation_rate=2**i)
    x = GlobalAveragePooling1D()(x)
    out = Dense(1)(x)
    return Model(inp, out, name="tcn_reg")


def build_patchtst_model_reg(input_shape, patch_len=4, d_model=64, dff=128):
    T, F = input_shape
    P = math.ceil(T / patch_len)
    pad_len = P * patch_len - T

    inp = Input(shape=input_shape)
    x = inp
    if pad_len > 0:
        x = ZeroPadding1D((0, pad_len))(x)
    x = Reshape((P, patch_len * F))(x)
    x = Dense(d_model)(x)
    for _ in range(2):
        x = TransformerEncoder(d_model, 4, dff)(x)
    x = GlobalAveragePooling1D()(x)
    out = Dense(1)(x)
    return Model(inp, out, name="patchtst_like_reg")


def build_tft_lite_model_reg(input_shape, d_model=64, dff=128):
    inp = Input(shape=input_shape)
    x = LSTM(d_model, return_sequences=True)(inp)
    attn = MultiHeadAttention(key_dim=d_model, num_heads=4)(x, x, x)
    x = LayerNormalization(epsilon=1e-6)(x + attn)
    ffn = Dense(dff, activation="relu")(x)
    ffn = Dense(d_model)(ffn)
    x = LayerNormalization(epsilon=1e-6)(x + ffn)
    x = GlobalAveragePooling1D()(x)
    out = Dense(1)(x)
    return Model(inp, out, name="tft_lite_reg")


def build_attn_lstm_cnn_model_reg(input_shape):
    inp = Input(shape=input_shape)
    x = Conv1D(64, 3, padding="same")(inp)
    x = Activation("relu")(x)
    x = Conv1D(64, 3, padding="same")(x)
    x = Activation("relu")(x)
    x = LSTM(64, return_sequences=True)(x)
    x = Attention()(x)
    out = Dense(1)(x)
    return Model(inp, out, name="attn_lstm_cnn_reg")


# === 🔥 CHAMPION MODEL 로딩용 빌더 ===
def build_champion_model(input_shape):
    return load_model("app/artifacts_golden/CHAMPION_MODEL.keras")


MODEL_BUILDERS = {
    "lstm_attention_reg": build_lstm_with_attention_reg,
    "gru_attention_reg": build_gru_with_attention_reg,
    "transformer_reg": build_transformer_model_reg,
    "tcn_reg": build_tcn_model_reg,
    "patchtst_like_reg": build_patchtst_model_reg,
    "tft_lite_reg": build_tft_lite_model_reg,
    "attn_lstm_cnn_reg": build_attn_lstm_cnn_model_reg,
    "champion_model": build_champion_model,   # ⭐ 추가됨
}

# ======================================================================
# 4) 모델 로딩
# ======================================================================

_models: Dict[str, Model] = {}
_input_shape = None

def load_models(input_shape):
    global _models, _input_shape
    _input_shape = input_shape

    for name, weight_path in MODEL_WEIGHTS.items():
        builder = MODEL_BUILDERS[name]
        try:
            model = builder(input_shape)
            print(f"[model_handler] {name} 모델 초기화 성공")
            _models[name] = model
        except Exception as e:
            print(f"[model_handler] ⚠️ {name} 초기화 실패: {e}")


# ======================================================================
# 5) Ensemble 규칙
# ======================================================================

def scaled_to_signal(y_scaled: float) -> float:
    sig = (y_scaled - 0.5) * 2
    return float(max(-1, min(1, sig)))


def signal_to_confidence(sig: float) -> float:
    return float(0.6 + 0.4 * abs(sig))


# ======================================================================
# 6) 예측 실행
# ======================================================================

def run_inference(model_input: np.ndarray) -> Dict[str, Any]:
    global _models

    if not _models:
        load_models(model_input.shape[1:])

    outputs = []
    raw_preds: Dict[str, float] = {}

    w_sum, w_tot = 0.0, 0.0

    for name, model in _models.items():
        try:
            p_scaled = float(model.predict(model_input, verbose=0)[0][0])
        except Exception:
            p_scaled = 0.5  # fallback

        sig = scaled_to_signal(p_scaled)
        conf = signal_to_confidence(sig)

        outputs.append({
            "name": name,
            "signal": sig,
            "confidence": conf,
        })

        raw_preds[name] = p_scaled

        w_sum += sig * conf
        w_tot += conf

    ensemble = w_sum / w_tot if w_tot > 0 else 0.0
    meta_prob = 1.0 / (1.0 + math.exp(-ensemble * 4.0))

    return {
        "models": outputs,
        "ensemble_score": ensemble,
        "raw_preds": raw_preds,
        "meta_probability": meta_prob,
    }


# ======================================================================
# 7) ModelHandler (FastAPI entry)
# ======================================================================

class ModelHandler:
    def __init__(self):
        self.initialized = False
        self.input_shape = None

    def ensure_models(self, input_shape):
        if not self.initialized or self.input_shape != input_shape:
            load_models(input_shape)
            self.initialized = True
            self.input_shape = input_shape
            print("[ModelHandler] 모델 초기화 완료")

    def predict(self, df):
        arr = df.astype(float).values
        x = np.expand_dims(arr, axis=0)

        self.ensure_models(x.shape[1:])
        result = run_inference(x)

        return result["ensemble_score"], result["ensemble_score"]
