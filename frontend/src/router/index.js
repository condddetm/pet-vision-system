import { createRouter, createWebHistory } from 'vue-router'
import Intro from '../views/Intro.vue'
import Dataset from '../views/Dataset.vue'
import Predict from '../views/Predict.vue'
import Analysis from '../views/Analysis.vue'
import Extra from '../views/Extra.vue'

const routes = [
  { path: '/', name: 'intro', component: Intro },
  { path: '/dataset', name: 'dataset', component: Dataset },
  { path: '/predict', name: 'predict', component: Predict },
  { path: '/analysis', name: 'analysis', component: Analysis },
  { path: '/extra', name: 'extra', component: Extra }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
