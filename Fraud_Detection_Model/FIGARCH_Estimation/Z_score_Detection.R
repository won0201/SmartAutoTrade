# ===========================================
# R: Z_score_Detection.R (Rscript용 수정)
# ===========================================

library(fEGarch)
library(xts)
library(PerformanceAnalytics)
library(fracdiff)
library(stats4)
library(Rsolnp)
library(boot)
library(ggplot2)
library(dplyr)
library(readr)
library(openxlsx)
library(Metrics)

# 1) 데이터 불러오기
data <- read.csv("C:/Users/dbjin/DATA/Close.csv", header=TRUE, stringsAsFactors=FALSE)
data$Date <- as.Date(data$Date)

# Return 컬럼 없으면 로그수익률 계산
if(!("Return" %in% colnames(data))){
  data$Return <- NA  # 초기화
  tickers <- c("Samsung","Hyundai","SKHynix","KaKao","Naver")
  for(tkr in tickers){
    data[[paste0(tkr,"_Return")]] <- c(NA, diff(log(data[[tkr]])))
  }
}

# xts 변환
Samsungc_xts <- xts(data$Samsung, order.by=data$Date)
Hyundaic_xts <- xts(data$Hyundai, order.by=data$Date)
SKHynixc_xts <- xts(data$SKHynix, order.by=data$Date)
KaKaoc_xts <- xts(data$KaKao, order.by=data$Date)
Naverc_xts <- xts(data$Naver, order.by=data$Date)
prices_xts <- xts(data[, c("Samsung","Hyundai","SKHynix","KaKao","Naver")], order.by=data$Date)

# 2) 로그수익률 계산
ret <- na.omit(diff(log(prices_xts)))
returns_list <- lapply(prices_xts, function(x) na.omit(diff(log(x))))

# 3) FIGARCH variance 계산
figarch_variance <- function(params, data){
  omega <- params[1]
  phi <- params[2]
  beta <- params[3]
  d <- params[4]

  eps <- data - mean(data)
  sigma2 <- rep(var(data), length(data))

  for(t in 2:length(data)){
    frac_term <- 0
    for(j in 1:(t-1)){
      val <- tryCatch({
        term <- gamma(j-d)/(gamma(j+1)/gamma(-d)) * eps[t-j]^2
        if(is.finite(term) & term >=0) term else 0
      }, error=function(e) 0)
      frac_term <- frac_term + val
    }
    sigma2[t] <- max(1e-6, omega + beta*sigma2[t-1] + phi*frac_term)
  }
  return(sigma2)
}

# 4) FIGARCH 추정 함수
estimate_figarch_stable <- function(ret_xts){
  ret_vec <- as.numeric(ret_xts)
  ret_vec <- ret_vec - mean(ret_vec)
  ret_vec <- ret_vec[abs(ret_vec) < 5*sd(ret_vec)]

  loglik_transformed <- function(pars){
    omega <- exp(pars[1])
    phi <- 1/(1+exp(-pars[2]))
    beta <- 1/(1+exp(-pars[3]))
    d <- 1/(1+exp(-pars[4]))

    sigma2 <- tryCatch({
      figarch_variance(c(omega,phi,beta,d), ret_vec)
    }, error=function(e){
      warning("figarch_variance 실패: ", e$message)
      return(rep(NA, length(ret_vec)))
    })
    if(any(is.na(sigma2))) return(Inf)
    sigma2 <- pmax(sigma2, 1e-6)
    ll <- -0.5*sum(log(sigma2) + ret_vec^2/sigma2)
    return(-ll)
  }

  init_pars <- c(log(0.01), log(0.05/0.95), log(0.9/0.1), log(0.3/0.7))

  fit <- tryCatch({
    optim(par=init_pars, fn=loglik_transformed, method="BFGS",
          control=list(maxit=20000, reltol=1e-10))
  }, error=function(e){ warning("최적화 실패: ", e$message); return(NULL)})

  if(is.null(fit)) return(NULL)

  omega_hat <- exp(fit$par[1])
  phi_hat <- 1/(1+exp(-fit$par[2]))
  beta_hat <- 1/(1+exp(-fit$par[3]))
  d_hat <- 1/(1+exp(-fit$par[4]))

  sigma2_hat <- figarch_variance(c(omega_hat, phi_hat, beta_hat, d_hat), ret_vec)
  sigma_t <- sqrt(sigma2_hat)

  list(omega=omega_hat, phi=phi_hat, beta=beta_hat, d=d_hat, sigma_t=sigma_t)
}

# 5) Z-score 계산
compute_figarch_zscore <- function(df, sigma_t){
  df$Zscore <- df$Return / sigma_t
  df$Direction <- ifelse(df$Zscore>3,"Up",ifelse(df$Zscore< -3,"Down","Normal"))
  return(df)
}

# ===========================================
# 6) 종목별 FIGARCH 추정 및 Z-score 계산
# ===========================================
tickers <- c("Samsung","Hyundai","SKHynix","KaKao","Naver")
results <- list()

for(tkr in tickers){
  cat("\n==================\n📈", tkr, "FIGARCH 추정 중...\n")
  fit <- estimate_figarch_stable(returns_list[[tkr]])
  if(is.null(fit)) next

  ret_vec <- as.numeric(returns_list[[tkr]])
  sigma_t <- fit$sigma_t
  zscore <- ret_vec / sigma_t
  anomaly <- abs(zscore)>3

  results[[tkr]] <- data.frame(
    Date=index(returns_list[[tkr]]),
    Return=ret_vec,
    Sigma_t=sigma_t,
    Zscore=zscore,
    Anomaly=anomaly
  )

  cat("d 계수:", round(fit$d,4)," / 이상 탐지 비율:", round(mean(anomaly)*100,2),"%\n")
}

# ===========================================
# 7) CSV 저장
# ===========================================
save_path <- "C:/Users/dbjin/DATA/"
stats_list <- list()
for(tkr in names(results)){
  df <- results[[tkr]]
  sigma_t <- df$Sigma_t
  df <- compute_figarch_zscore(df, sigma_t)
  results[[tkr]] <- df

  # CSV 저장
  file_name <- paste0(save_path,tkr,"_Zscore.csv")
  write_csv(df,file_name)
}
