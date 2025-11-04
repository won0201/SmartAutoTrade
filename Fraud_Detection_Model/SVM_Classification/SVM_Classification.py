from sklearn.preprocessing import StandardScaler #표준화 #값의 범위가 달라서 학습 성능 저하되는 경우 방지
from sklearn.svm import SVC
from imblearn.over_sampling import SMOTE #소수 클래스 데이터 증강
import pandas as pd
from Fraud_Detection_Model.SVM_Classification.ES_cutoff import label_by_es
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score

# ============================
# 6) SVM 모델 학습
# ============================
def train_svm_signals(df_labeled, features, test_ratio=0.3, smote_k=1, random_state=42):
    """
    df_labeled : SVM 학습용 데이터프레임, 'label' 컬럼 필수
    features   : 학습에 사용할 feature 컬럼 리스트
    test_ratio : 학습/테스트 비율
    smote_k    : SMOTE k_neighbors
    """
    results = []

    for asset, df_asset in df_labeled.groupby("asset"):
     # ---------------------
    # 1) Train/Test 분할
    # ---------------------
        train, test = stratified_train_test_split(df_asset, test_ratio=test_ratio)
        X_train, y_train = train[features].values, train["label"].values
        X_test, y_test = test[features].values, test["label"].values

    # ---------------------
    # 2) 스케일링 (train fit, test transform)
    # ---------------------
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_scaled_full = scaler.transform(df_asset[features].values)

    # ---------------------
    # 3) SMOTE (train only)
    # ---------------------
        sm = SMOTE(random_state=42, k_neighbors=1)
        X_train_res, y_train_res = sm.fit_resample(X_train_scaled, y_train)

    # ---------------------
    # 4) SVM 학습 (train only)
    # ---------------------
        svm = SVC(
        kernel="rbf",
        C=50.0,
        gamma=0.05,
        probability=True,
        class_weight="balanced",
        random_state=42,
    )
        svm.fit(X_train_res, y_train_res)

    # ---------------------
    # 5) 예측 (test only, SMOTE 적용 X) #SMOTE는 훈련 데이터만 적용하는 것이 원칙
    # ---------------------

        y_pred_full = svm.predict(X_scaled_full)
        y_prob_full = svm.predict_proba(X_scaled_full)[:, 1]

    # ---------------------
    # 6) 결과 저장
    # ---------------------
        df_out = df_asset.copy()
        df_out["svm_signal"] = y_pred_full
        df_out["svm_prob"] = y_prob_full
        results.append(df_out)

# 반복문 밖에서 SVM 결과 합치기
    df_svm_results = pd.concat(results).reset_index(drop=True)
    # 함수 반환
    return df_svm_results

# ============================
# 자산별 신호 집계 및 출력 함수
# ============================
def print_asset_signal_summary(df_svm_results):

    # 자산별 신호 집계
    df_count = df_svm_results.groupby("asset")["svm_signal"]\
                .value_counts()\
                .unstack(fill_value=0)

    # 열 순서 고정 (0 → 1)
    df_count = df_count.reindex(columns=[0, 1], fill_value=0)

    # 행 순서 알파벳 순
    df_count = df_count.sort_index()

    # 출력
    print("\n=== 자산별 매도(1) / 보유(0) 신호 개수 ===")
    print(df_count.to_string())

# ============================
# SVM 평가 함수
# ============================
def evaluate_svm(df_results):
    """
    df_results : df_svm_results 형태
                 반드시 'label', 'svm_signal' 컬럼 존재
                 (옵션) 'svm_prob' 컬럼 존재 시 ROC-AUC 계산
    """
    y_true = df_results["label"].values
    y_pred = df_results["svm_signal"].values
    y_prob = df_results["svm_prob"].values

    auc_score = roc_auc_score(y_true, y_prob)
    print("ROC-AUC:", auc_score)

    # 1) classification report
    print("\n=== Classification Report ===")
    print(classification_report(y_true, y_pred))

    # 2) confusion matrix
    print("=== Confusion Matrix ===")
    print(confusion_matrix(y_true, y_pred))

    # 3) ROC-AUC
    if "svm_prob" in df_results.columns:
        y_prob = df_results["svm_prob"].values
        auc_score = roc_auc_score(y_true, y_prob)
        print("\n=== ROC-AUC Score ===")
        print(auc_score)
    else:
        print("\n")

def stratified_train_test_split(df_asset, test_ratio=0.3):
    # label=1 샘플 추출
    pos = df_asset[df_asset["label"] == 1]
    neg = df_asset[df_asset["label"] == 0]

    n_test = int(len(df_asset) * test_ratio)

    # 최소 1개 label=1 샘플을 테스트셋에 넣기
    n_pos_test = min(len(pos), max(1, int(len(pos) * test_ratio)))
    n_neg_test = n_test - n_pos_test

    test = pd.concat([pos.iloc[:n_pos_test], neg.iloc[:n_neg_test]])
    train = df_asset.drop(test.index)

    return train, test

# ============================
# 2) 메인 실행 코드
# ============================
if __name__ == "__main__":
    # 1) CSV 불러오기
    input_path = r"C:\Users\dbjin\DATA\svm_ann_target_data.csv"
    df = pd.read_csv(input_path, parse_dates=["Date"])  # Date 컬럼을 datetime으로 읽기

    # 2) 자산별 ES 기반 라벨링
    df_labeled = label_by_es(df, q_level=0.8, show_plot=False)  # show_plot=True 하면 그래프 출력

    # 3) 학습에 사용할 feature
    features = ["pred_sharpe", "pred_ES"]  # 필요에 따라 수정 가능

    # 4) SVM 학습 + 신호 생성
    df_svm_results = train_svm_signals(df_labeled, features=features, test_ratio=0.2)

    # 5) 자산별 신호 집계 및 출력
    print_asset_signal_summary(df_svm_results)

    # 6) 평가
    evaluate_svm(df_svm_results)

    # 6) SVM 결과 CSV 저장
    output_path = r"C:\Users\dbjin\DATA\svm_signal_results.csv"
    df_svm_results[["Date", "asset", "svm_signal"]].to_csv(output_path, index=False)
    print(f"\n SVM signal results saved to {output_path}")
