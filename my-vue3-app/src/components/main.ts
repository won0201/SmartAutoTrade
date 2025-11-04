import { createApp } from 'vue'
import Toast from 'vue-toastification'
import 'vue-toastification/dist/index.css'
import App from "../App.vue";

const app = createApp(App)
app.use(Toast, {
  position: 'top-right',   // 위치: top-right, bottom-left 등
  timeout: 5000,           // 자동 종료 시간(ms)
  closeOnClick: true,
  pauseOnHover: true,
})
app.mount('#app')