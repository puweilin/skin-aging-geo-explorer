import { createApp } from 'vue'
import {
  ElButton,
  ElIcon,
  ElInput,
  ElOption,
  ElResult,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag
} from 'element-plus'
import 'element-plus/dist/index.css'
import {
  Collection,
  Connection,
  DataAnalysis,
  Document,
  Link,
  Loading,
  Location,
  MagicStick,
  RefreshLeft,
  Search
} from '@element-plus/icons-vue'
import './style.css'
import App from './App.vue'

const app = createApp(App)

const components = [
  ElButton,
  ElIcon,
  ElInput,
  ElOption,
  ElResult,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag
]

for (const component of components) {
  app.component(component.name, component)
}

const icons = {
  Collection,
  Connection,
  DataAnalysis,
  Document,
  Link,
  Loading,
  Location,
  MagicStick,
  RefreshLeft,
  Search
}

for (const [name, component] of Object.entries(icons)) {
  app.component(name, component)
}

app.mount('#app')
