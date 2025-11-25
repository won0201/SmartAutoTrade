# backend/app/model_runner.py
"""
SIGMA A 프로젝트 - 실제 모델 실행용 모듈

- 7개 딥러닝 모델 구조를 kospi200_trading_system_2.py 에서 그대로 가져와서 재구성
- 6단계에서 만든 step6_data.npz 의 X_test 를 "데모용 시퀀스 스트림"으로 사용
- run_models() 가 호출될 때마다 X_test 에서 다음 샘플 하나를 꺼내
  7개 모델로 예측 → signal / confidence 계산 → 최종 앙상블 score 반환

⚠️ 실제 실시간 KOSPI200 데이터로 바꾸고 싶으면:
    - (1) 현재는 X_test[i] 를 입력으로 쓰고 있으니,
    - (2) 새로운 시퀀스를 만들어서 이 모듈에 넘겨주는 구조로 확장하면 됨.
"""

import os
import math
import numpy as np
import tensorflow as tf
from tensorflow.keras import Model, regularizers
from tensorflow.keras.layers import (
    Layer,
    LayerNormalization,
    Dropout,
    Dense,
    GlobalAveragePooling1D,
    MultiHeadAttention,
    Input,
    LSTM,
    GRU,
    Conv1D,
    Add,
    Activation,
    ZeroPadding1D,
    Reshape,
)

# ======================================================================
# 0. 아티팩트 경로 설정
# ======================================================================

# 기본적으로는 model_runner.py 가 있는 디렉터리에 아티팩트를 둔다고 가정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 가중치 파일들 (네가 업로드한 파일 이름 그대로)
WEIGHT_FILES = {
    "gru_attention_reg":      os.path.join(BASE_DIR, "tmp_gru_attention_reg.weights.h5"),
    "lstm_attention_reg":     os.path.join(BASE_DIR, "tmp_lstm_attention_reg.weights.h5"),
    "transformer_reg":        os.path.join(BASE_DIR, "tmp_transformer_reg.weights.h5"),
    "tcn_reg":                os.path.join(BASE_DIR, "tmp_tcn_reg.weights.h5"),
    "patchtst_like_reg":      os.path.join(BASE_DIR, "tmp_patchtst_like_reg.weights.h5"),
    "tft_lite_reg":           os.path.join(BASE_DIR, "tmp_tft_lite_reg.weights.h5"),
    "attn_lstm_cnn_reg":      os.path.join(BASE_DIR, "tmp_attn_lstm_cnn_reg.weights.h5"),
}

STEP6_PATH = os.path.join(BASE_DIR, "step6_data.npz")
# SCALER_PATH = os.path.join(BASE_DIR, "scaler.pkl")  # 필요하면 나중에 사용


# ======================================================================
# 1. 커스텀 레이어 (Attention / PositionalEncoding / TransformerEncoder)
#    → kospi200_trading_system_2.py 에서 가져온 것과 동일하게 구현
# ======================================================================

class Attention(Layer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build(self, input_shape):
        self.W = self.add_weight(
            name="att_weight",
            shape=(input_shape[-1], 1),
            initializer="glorot_uniform",
        )
        self.b = self.add_weight(
            name="att_bias",
            shape=(input_shape[1], 1),
            initializer="zeros",
        )
        super().build(input_shape)

    def call(self, x):
        # x: (batch, time, features)
        et = tf.squeeze(tf.tanh(tf.matmul(x, self.W) + self.b), axis=-1)
        at = tf.nn.softmax(et, axis=-1)
        at = tf.expand_dims(at, axis=-1)
        return tf.reduce_sum(x * at, axis=1)


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
        pos_encoding = tf.concat([sines, cosines], axis=-1)[tf.newaxis, ...]
        return pos_encoding

    def call(self, inputs):
        return inputs + self.pos_encoding[:, : tf.shape(inputs)[1], :]


class TransformerEncoder(Layer):
    def __init__(self, d_model, num_heads, dff, rate=0.1, **kwargs):
        super().__init__(**kwargs)
        self.d_model = int(d_model)
        self.num_heads = int(num_heads)
        self.dff = int(dff)
        self.rate = float(rate)

        self.mha = MultiHeadAttention(key_dim=self.d_model, num_heads=self.num_heads)
        self.ffn = tf.keras.Sequential(
            [Dense(self.dff, activation="relu"), Dense(self.d_model)]
        )
        self.norm1 = LayerNormalization(epsilon=1e-6)
        self.norm2 = LayerNormalization(epsilon=1e-6)
        self.drop1 = Dropout(self.rate)
        self.drop2 = Dropout(self.rate)

    def get_config(self):
        cfg = super().get_config()
        cfg.update(
            {
                "d_model": self.d_model,
                "num_heads": self.num_heads,
                "dff": self.dff,
                "rate": self.rate,
            }
        )
        return cfg

    def call(self, x, training=False):
        attn = self.mha(x, x, x)
        attn = self.drop1(attn, training=training)
        out1 = self.norm1(x + attn)
        ffn = self.ffn(out1)
        ffn = self.drop2(ffn, training=training)
        return self.norm2(out1 + ffn)


# ======================================================================
# 2. 7개 모델 빌더 (학습 때 사용한 구조를 그대로 복원)
# ======================================================================

L2_REG = 1e-5  # 학습 코드와 동일한 정규화 강도

def build_lstm_with_attention_reg(input_shape):
    inp = Input(shape=input_shape)
    x = LSTM(
        64,
        return_sequences=True,
        dropout=0.2,
        kernel_regularizer=regularizers.l2(L2_REG),
    )(inp)
    x = Attention()(x)
    out = Dense(1)(x)
    return Model(inp, out, name="lstm_attention_reg")


def build_gru_with_attention_reg(input_shape):
    inp = Input(shape=input_shape)
    x = GRU(
        64,
        return_sequences=True,
        dropout=0.2,
        kernel_regularizer=regularizers.l2(L2_REG),
    )(inp)
    x = Attention()(x)
    out = Dense(1)(x)
    return Model(inp, out, name="gru_attention_reg")


def build_transformer_model_reg(
    input_shape, d_model=64, num_heads=4, dff=128, num_encoders=2, rate=0.1
):
    inp = Input(shape=input_shape)
    x = Dense(d_model, kernel_regularizer=regularizers.l2(L2_REG))(inp)
    x = PositionalEncoding(int(input_shape[0]), int(d_model))(x)
    for _ in range(num_encoders):
        x = TransformerEncoder(d_model, num_heads, dff, rate)(x)
    x = GlobalAveragePooling1D()(x)
    x = Dropout(0.2)(x)
    out = Dense(1)(x)
    return Model(inp, out, name="transformer_reg")


def _tcn_block_reg(x, filters, kernel_size=3, dilation_rate=1, dropout=0.1):
    h = Conv1D(
        filters,
        kernel_size,
        padding="causal",
        dilation_rate=dilation_rate,
        kernel_regularizer=regularizers.l2(L2_REG),
    )(x)
    h = LayerNormalization(epsilon=1e-6)(h)
    h = Activation("relu")(h)
    h = Dropout(dropout)(h)
    h = Conv1D(
        filters,
        kernel_size,
        padding="causal",
        dilation_rate=dilation_rate,
        kernel_regularizer=regularizers.l2(L2_REG),
    )(h)
    h = LayerNormalization(epsilon=1e-6)(h)
    if x.shape[-1] != filters:
        x = Conv1D(filters, 1, padding="same")(x)
    return Activation("relu")(Add()([x, h]))


def build_tcn_model_reg(input_shape, filters=64, levels=4, kernel_size=3, dropout=0.1):
    inp = Input(shape=input_shape)
    x = inp
    for i in range(levels):
        x = _tcn_block_reg(
            x,
            filters=filters,
            kernel_size=kernel_size,
            dilation_rate=2**i,
            dropout=dropout,
        )
    x = GlobalAveragePooling1D()(x)
    x = Dropout(0.2)(x)
    out = Dense(1)(x)
    return Model(inp, out, name="tcn_reg")


def build_patchtst_model_reg(
    input_shape, patch_len=4, d_model=64, num_heads=4, dff=128, num_encoders=2, rate=0.1
):
    T, F = int(input_shape[0]), int(input_shape[1])
    P = math.ceil(T / patch_len)
    pad_len = P * patch_len - T

    inp = Input(shape=input_shape)
    x = inp
    if pad_len > 0:
        x = ZeroPadding1D(padding=(0, pad_len))(x)
    x = Reshape((P, patch_len * F))(x)
    x = Dense(d_model, kernel_regularizer=regularizers.l2(L2_REG))(x)
    for _ in range(num_encoders):
        x = TransformerEncoder(
            d_model=d_model, num_heads=num_heads, dff=dff, rate=rate
        )(x)
    x = GlobalAveragePooling1D()(x)
    x = Dropout(0.2)(x)
    out = Dense(1)(x)
    return Model(inp, out, name="patchtst_like_reg")


def build_tft_lite_model_reg(
    input_shape, d_model=64, num_heads=4, dff=128, rate=0.1
):
    inp = Input(shape=input_shape)
    x = LSTM(
        d_model, return_sequences=True, kernel_regularizer=regularizers.l2(L2_REG)
    )(inp)
    attn = MultiHeadAttention(key_dim=d_model, num_heads=num_heads)(x, x, x)
    x1 = LayerNormalization(epsilon=1e-6)(x + attn)
    ffn = Dense(dff, activation="relu")(x1)
    ffn = Dropout(rate)(ffn)
    ffn = Dense(d_model)(ffn)
    x2 = LayerNormalization(epsilon=1e-6)(x1 + ffn)
    x2 = GlobalAveragePooling1D()(x2)
    x2 = Dropout(0.2)(x2)
    out = Dense(1)(x2)
    return Model(inp, out, name="tft_lite_reg")


def build_attn_lstm_cnn_model_reg(
    input_shape, filters=64, kernel_size=3, lstm_units=64, rate=0.1
):
    inp = Input(shape=input_shape)
    x = Conv1D(
        filters, kernel_size, padding="same", kernel_regularizer=regularizers.l2(L2_REG)
    )(inp)
    x = Activation("relu")(x)
    x = Conv1D(
        filters, kernel_size, padding="same", kernel_regularizer=regularizers.l2(L2_REG)
    )(x)
    x = Activation("relu")(x)
    x = LSTM(
        lstm_units,
        return_sequences=True,
        kernel_regularizer=regularizers.l2(L2_REG),
    )(x)
    x = Attention()(x)
    x = Dropout(rate)(x)
    out = Dense(1)(x)
    return Model(inp, out, name="attn_lstm_cnn_reg")


# ======================================================================
# 3. 전역 모델/데이터 로딩 (서버 시작 시 1번만)
# ======================================================================

MODEL_BUILDERS = {
    "gru_attention_reg":      build_gru_with_attention_reg,
    "lstm_attention_reg":     build_lstm_with_attention_reg,
    "transformer_reg":        build_transformer_model_reg,
    "tcn_reg":                build_tcn_model_reg,
    "patchtst_like_reg":      build_patchtst_model_reg,
    "tft_lite_reg":           build_tft_lite_model_reg,
    "attn_lstm_cnn_reg":      build_attn_lstm_cnn_model_reg,
}

_models = {}
_X_stream = None
_stream_idx = 0

def _load_step6_data():
    """
    step6_data.npz 에서 X_test 를 가져와 데모용 입력 시퀀스로 사용
    """
    global _X_stream
    if not os.path.exists(STEP6_PATH):
        raise FileNotFoundError(
            f"step6_data.npz 파일을 찾을 수 없습니다: {STEP6_PATH}\n"
            f"6단계(artifacts_golden)에서 생성된 파일을 backend/app 쪽으로 복사해 주세요."
        )
    data = np.load(STEP6_PATH)
    X_test = data["X_test"]
    _X_stream = X_test
    print(f"[model_runner] step6_data.npz 로드 완료, X_test shape={X_test.shape}")


def _build_and_load_models():
    """
    7개 모델을 input_shape 에 맞춰 생성 후 각각의 tmp_*.weights.h5 로부터 가중치 로드
    """
    global _models

    if _X_stream is None:
        _load_step6_data()

    input_shape = _X_stream.shape[1:]  # (seq_len, n_features)
    print(f"[model_runner] 모델 input_shape={input_shape}")

    for name, builder in MODEL_BUILDERS.items():
        print(f"[model_runner] 빌드 및 가중치 로드: {name}")
        model = builder(input_shape)
        weights_path = WEIGHT_FILES.get(name)
        if weights_path and os.path.exists(weights_path):
            try:
                model.load_weights(weights_path)
                print(f"  → 가중치 로드 완료: {weights_path}")
            except Exception as e:
                print(f"  ⚠️ 가중치 로드 실패 ({name}): {e}")
        else:
            print(f"  ⚠️ 가중치 파일 없음, 랜덤 초기화 상태로 사용: {weights_path}")
        _models[name] = model

# 서버 시작 시 1번 실행
try:
    _load_step6_data()
    _build_and_load_models()
except Exception as e:
    print(f"[model_runner] 초기 로딩 중 오류: {e}")


# ======================================================================
# 4. run_models() – FastAPI에서 호출하는 핵심 함수
# ======================================================================

def _scaled_to_signal(y_scaled: float) -> float:
    """
    MinMaxScaler 로 0~1 범위에 있는 y_scaled 를
    대략 [-1, 1] 범위의 '방향성 signal' 로 변환하는 간단한 함수.
    (정교한 역스케일링을 쓰고 싶으면 scaler.pkl 기반으로 확장 가능)
    """
    signal = (y_scaled - 0.5) * 2.0  # 0.5 → 0, 0→-1, 1→+1
    return float(max(-1.0, min(1.0, signal)))


def _signal_to_confidence(signal: float) -> float:
    """
    signal 절대값이 클수록 confidence 를 높게 주는 간단한 규칙.
    (기본 0.6 ~ 0.98 사이로 클램프)
    """
    base = 0.6 + 0.4 * abs(signal)  # 0.6~1.0
    return float(max(0.6, min(0.98, base)))


def run_models():
    """
    FastAPI /predict 에서 사용하는 엔트리 포인트.

    반환 형식:
    {
        "timestamp": str,
        "symbol": "KOSPI200",
        "regime": "bull" | "bear" | "neutral",
        "score": float,          # 최종 앙상블 시그널 [-1,1]
        "confidence": float,     # 0~1 (간단 규칙 기반)
        "models": [
            {"name": str, "signal": float, "confidence": float}, ...
        ]
    }
    """
    global _stream_idx

    if _X_stream is None or len(_X_stream) == 0:
        raise RuntimeError("X_test 스트림 데이터가 없습니다. step6_data.npz 를 확인하세요.")

    if not _models:
        _build_and_load_models()

    # 순차적으로 X_test에서 하나씩 사용 (루프)
    idx = _stream_idx % len(_X_stream)
    _stream_idx += 1
    x_seq = _X_stream[idx]          # (seq_len, n_features)
    x_batch = np.expand_dims(x_seq, axis=0)  # (1, seq_len, n_features)

    model_outputs = []
    weighted_sum = 0.0
    weight_total = 0.0

    for name, model in _models.items():
        # 예측 (스케일된 Price)
        y_scaled = float(model.predict(x_batch, verbose=0).flatten()[0])
        signal = _scaled_to_signal(y_scaled)
        conf = _signal_to_confidence(signal)

        model_outputs.append(
            {
                "name": name,
                "signal": signal,
                "confidence": conf,
            }
        )

        weighted_sum += signal * conf
        weight_total += conf

    if weight_total > 0:
        ensemble_score = weighted_sum / weight_total
    else:
        ensemble_score = 0.0

    # regime 단순 규칙: > 0.2 bull, < -0.2 bear, 나머지 neutral
    if ensemble_score > 0.2:
        regime = "bull"
    elif ensemble_score < -0.2:
        regime = "bear"
    else:
        regime = "neutral"

    from datetime import datetime, timezone, timedelta
    KST = timezone(timedelta(hours=9))

    result = {
        "timestamp": datetime.now(tz=KST).isoformat(),
        "symbol": "KOSPI200",
        "regime": regime,
        "score": float(max(-1.0, min(1.0, ensemble_score))),
        "confidence": float(min(0.99, max(0.5, abs(ensemble_score) + 0.5))),
        "models": model_outputs,
    }
    return result
