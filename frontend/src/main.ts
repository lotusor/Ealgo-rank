import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
// 旧令牌在 styles.css，新的深色设计系统放在 styles/ 下。
// 必须让 tokens.css 在 styles.css 之后加载，其 Legacy bridge 才能把
// --bg / --brand 等旧名覆盖成深色值，避免迁移期出现浅底深色撕裂。
import './styles.css'
import './styles/tokens.css'
import './styles/base.css'
import './styles/components.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
