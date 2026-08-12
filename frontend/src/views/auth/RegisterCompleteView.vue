<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import RegisterForm from '@/components/auth/RegisterForm.vue'
import type { UserMe } from '@/api/types'

const router = useRouter()
const auth = useAuthStore()

function onDone(_u: UserMe) {
  router.push({ name: 'register-admin' })
}
</script>

<template>
  <RegisterForm mode="complete" :prefill="auth.user" @done="onDone" />
</template>
