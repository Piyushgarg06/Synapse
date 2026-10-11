import DefaultTheme from 'vitepress/theme'
import './custom.css'
import TerminalPlayer from './components/TerminalPlayer.vue'
import InteractiveGraph from './components/InteractiveGraph.vue'
import PipelineDiagram from './components/PipelineDiagram.vue'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }: { app: any }) {
    app.component('TerminalPlayer', TerminalPlayer)
    app.component('InteractiveGraph', InteractiveGraph)
    app.component('PipelineDiagram', PipelineDiagram)
  },
}
