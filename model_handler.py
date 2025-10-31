# model_handler.py
import os
import joblib
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
import pandas as pd

from config import (
    SCALER_PATH, DL_MODEL_PATH, SEQUENCE_LENGTH,
    GOLDEN_FEATURES, ARIMA_FEATURE_NAME
)
# ★ 1. 신규 ConfidenceManager 임포트
from confidence_manager import ConfidenceManager

# (Colab 9단계 커스텀 레이어 정의: Attention, PositionalEncoding, TransformerEncoder ...)
# ===================================================================
try:
    from keras.saving import register_keras_serializable as _register_serializable
except Exception:
    from tensorflow.keras.utils import register_keras_serializable as _register_serializable

from tensorflow.keras.layers import (
    Layer, LayerNormalization, Dropout, Dense, GlobalAveragePooling1D,
    MultiHeadAttention, LSTM, GRU, Conv1D, Add, Activation,
    ZeroPadding1D, Reshape
)

@_register_serializable(package="Custom")
class Attention(Layer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    def build(self, input_shape):
        self.W = self.add_weight(name="att_weight", shape=(input_shape[-1], 1), initializer="glorot_uniform")
        self.b = self.add_weight(name="att_bias",   shape=(input_shape[1], 1), initializer="zeros")
        super().build(input_shape)
    def call(self, x):
        et = tf.squeeze(tf.tanh(tf.matmul(x, self.W) + self.b), axis=-1); at = tf.nn.softmax(et, axis=-1)
        at = tf.expand_dims(at, axis=-1); return tf.reduce_sum(x * at, axis=1)

@_register_serializable(package="Custom")
class PositionalEncoding(Layer):
    def __init__(self, position, d_model, **kwargs):
        super().__init__(**kwargs)
        self.position = int(position); self.d_model  = int(d_model)
        self.pos_encoding = self._positional_encoding(self.position, self.d_model)
    def get_config(self):
        cfg = super().get_config(); cfg.update({"position": self.position, "d_model": self.d_model}); return cfg
    def _get_angles(self, position, i, d_model):
        angle_rates = 1.0 / tf.pow(10000.0, (2 * (i // 2)) / tf.cast(d_model, tf.float32))
        return tf.cast(position, tf.float32) * angle_rates
    def _positional_encoding(self, position, d_model):
        angle_rads = self._get_angles(tf.range(position, dtype=tf.float32)[:, tf.newaxis], tf.range(d_model,   dtype=tf.float32)[tf.newaxis, :], d_model)
        sines = tf.math.sin(angle_rads[:, 0::2]); cosines = tf.math.cos(angle_rads[:, 1::2])
        return tf.concat([sines, cosines], axis=-1)[tf.newaxis, ...]
    def call(self, inputs):
        return inputs + self.pos_encoding[:, :tf.shape(inputs)[1], :]

@_register_serializable(package="Custom")
class TransformerEncoder(Layer):
    def __init__(self, d_model, num_heads, dff, rate=0.1, **kwargs):
        super().__init__(**kwargs)
        self.d_model, self.num_heads, self.dff, self.rate = int(d_model), int(num_heads), int(dff), float(rate)
        self.mha = MultiHeadAttention(key_dim=self.d_model, num_heads=self.num_heads)
        self.ffn = tf.keras.Sequential([Dense(self.dff, activation="relu"), Dense(self.d_model)])
        self.norm1 = LayerNormalization(epsilon=1e-6); self.norm2 = LayerNormalization(epsilon=1e-6)
        self.drop1 = Dropout(self.rate); self.drop2 = Dropout(self.rate)
    def get_config(self):
        cfg = super().get_config(); cfg.update({"d_model": self.d_model, "num_heads": self.num_heads, "dff": self.dff, "rate": self.rate}); return cfg
    def call(self, x, training=False):
        attn = self.mha(x, x, x); attn = self.drop1(attn, training=training); out1 = self.norm1(x + attn)
        ffn = self.ffn(out1); ffn = self.drop2(ffn, training=training); return self.norm2(out1 + ffn)
# ===================================================================


class PredictionModel:
    def __init__(self, mc_passes=40):
        print("모델 핸들러 초기화 중 (DL 챔피언 모드)...")
        
        self.scaler = joblib.load(SCALER_PATH)
        print("✅ 스케일러 로드 완료.")

        self.scaler_features = GOLDEN_FEATURES + [ARIMA_FEATURE_NAME]
        self.n_features = len(self.scaler_features)
        self.seq_len = SEQUENCE_LENGTH
        self.mc_passes = mc_passes
        self.price_idx = self.scaler_features.index('Price')
        
        # ★ 2. ConfidenceManager 인스턴스 생성
        self.confidence_manager = ConfidenceManager()

        try:
            self.dl_model = load_model(DL_MODEL_PATH)
            print(f"✅ 딥러닝 챔피언 모델({DL_MODEL_PATH}) 로드 완료.")
        except Exception as e:
            print(f"❌ 딥러닝 모델({DL_MODEL_PATH}) 로드 실패. 오류: {e}")
            raise
            
        print("✅ 모든 모델 로드 완료!")

    def _create_sequences(self, scaled_data_window):
        X_dl = scaled_data_window[-self.seq_len:].reshape(1, self.seq_len, self.n_features)
        return X_dl

    @tf.function 
    def _predict_train_tf(self, x):
        return self.dl_model(x, training=True)

    def _dl_predict_mc(self, X_dl_input):
        preds_scaled = []
        for _ in range(self.mc_passes):
            y_scaled_tensor = self._predict_train_tf(X_dl_input)
            preds_scaled.append(y_scaled_tensor.numpy()[0][0])
        return np.array(preds_scaled)

    def _invert_price(self, scaled_preds):
        dummy_array = np.zeros((len(scaled_preds), self.n_features))
        dummy_array[:, self.price_idx] = scaled_preds
        inversed_array = self.scaler.inverse_transform(dummy_array)
        return inversed_array[:, self.price_idx]

    def predict_with_strength(self, recent_processed_df: pd.DataFrame) -> dict:
        last_price = float(recent_processed_df['Price'].iloc[-1])

        scaled_data = self.scaler.transform(recent_processed_df[self.scaler_features].values)
        X_dl_input = self._create_sequences(scaled_data)

        final_preds_scaled = self._dl_predict_mc(X_dl_input)
        final_preds_unscaled = self._invert_price(final_preds_scaled)
        
        mu = float(np.mean(final_preds_unscaled))
        var = float(np.var(final_preds_unscaled) + 1e-12)

        # Strength 계산
        delta = (mu - last_price)
        sigma_price = np.sqrt(var)
        sigma_norm = sigma_price / max(last_price, 1e-8)
        # (100% 버그 수정) 분모가 0이 되지 않도록 최소값 보장
        ir_var = abs(delta / max(sigma_norm, 1e-12))

        # 'Volatility_20D' (0-100) -> 0-1 스케일로 변환
        rv20_x100 = recent_processed_df['Volatility_20D'].iloc[-1] 
        rv20 = rv20_x100 / 100.0
        rv20 = float(rv20) if pd.notna(rv20) else 0.0

        ir_rv = abs(delta / max(rv20, 1e-12)) # (100% 버그 수정) 최소값 보장
        strength = 0.5 * ir_var + 0.5 * ir_rv

        return {
            'mu': mu,
            'var': var,
            'last_price': last_price,
            'strength': float(strength),
            'ir_var': float(ir_var),
            'ir_rv': float(ir_rv),
            'vol_recent_std': rv20
        }