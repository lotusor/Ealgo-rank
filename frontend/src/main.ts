import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { vSheen } from './directives/sheen'
// 令牌 → 基础层 → 组件层 → 纸本层：editorial.css 最后加载，
// 靠加载顺序覆盖同名规则，新增全局样式请放进对应一层而不是再开一份。
import './styles/tokens.css'
import './styles/base.css'
import './styles/components.css'
import './styles/editorial.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.directive('sheen', vSheen)
app.mount('#app')
