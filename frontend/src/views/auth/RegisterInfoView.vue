<script setup lang="ts">
import { useRouter } from 'vue-router'
import RegisterForm from '@/components/auth/RegisterForm.vue'
import type { UserMe } from '@/api/types'

const router = useRouter()
function onDone(_u: UserMe) {
  router.push({ name: 'register-admin' })
}
</script>

<template>
  <RegisterForm mode="create" @done="onDone" />
</template>
