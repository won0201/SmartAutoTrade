import pandas as pd
from imblearn.over_sampling import SMOTE #소수 클래스 데이터 증강
from sklearn.preprocessing import StandardScaler
import numpy as np
import os

# ============================
# 3) 학습/테스트 데이터 준비
# ============================
os.environ["LOKY_MAX_CPU_COUNT"] = "4"  # 예: 4코어 사용
output_path = r"C:\Users\dbjin\DATA\svm_target_data.csv"
df = pd.read_csv(output_path)

def label_data(df, feature="pred_ES", quantile=0.97):
    labels = []

    for asset, g in df.groupby("asset"):
        g = g.copy()  # SettingWithCopyWarning 방지
        g["abs_ES"] = g[feature].abs()
        cutoff = g["abs_ES"].quantile(quantile)
        g["label"] = (g["abs_ES"] >= cutoff).astype(int)
        labels.append(g)

    df_labeled = pd.concat(labels).reset_index(drop=True)
    return df_labeled

features = ["pred_sharpe", "pred_ES"]


def split_train_test(df_labeled, features, train_ratio=0.65):
    train = df_labeled.groupby("asset").apply(lambda x: x.iloc[:int(len(x)*train_ratio)], include_groups=False).reset_index(drop=True)
    test  = df_labeled.groupby("asset").apply(lambda x: x.iloc[int(len(x)*train_ratio):], include_groups=False).reset_index(drop=True)

    X_train, y_train = train[features].values, train["label"].values
    X_test, y_test   = test[features].values, test["label"].values
    return X_train, y_train, X_test, y_test, train, test

# ============================
# 4) 스케일링
# ============================
def scale_data(X_train, X_test):
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled  = scaler.transform(X_test)
    return X_train_scaled, X_test_scaled, scaler

# ============================
# 5) SMOTE (불균형 해소)
# ============================
def apply_smote(X_train_scaled, y_train):
    sm = SMOTE(random_state=42)
    X_train_res, y_train_res = sm.fit_resample(X_train_scaled, y_train)

    return X_train_res, y_train_res

if __name__ == "__main__":
    features = ["pred_sharpe", "pred_ES"]

    # 1) 라벨링
    df_labeled = label_data(df, feature="pred_ES", quantile=0.97)

    # 2) 학습/테스트 분리
    X_train, y_train, X_test, y_test, train, test = split_train_test(df_labeled, features)

    # 3) 스케일링
    X_train_scaled, X_test_scaled, scaler = scale_data(X_train, X_test)

    # 4) SMOTE
    X_train_res, y_train_res = apply_smote(X_train_scaled, y_train)

    print("\n=== 학습 데이터 크기 ===")
    print("원본:", X_train.shape, "라벨 분포:", np.bincount(y_train))
    print("SMOTE:", X_train_res.shape, "라벨 분포:", np.bincount(y_train_res))

