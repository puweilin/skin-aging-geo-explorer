<script setup>
defineProps({
  title: String,
  value: [String, Number],
  icon: String,
  color: String
})
</script>

<template>
  <div class="stats-card">
    <div class="stats-card__accent" :style="{ backgroundColor: color }"></div>
    <div class="flex items-center justify-between">
      <div>
        <div class="stats-card__label">{{ title }}</div>
        <div class="stats-card__value">{{ value }}</div>
      </div>
      <div
        class="stats-card__icon flex items-center justify-center"
        :style="{ backgroundColor: color + '12', borderColor: color + '26' }"
      >
        <el-icon :size="21" :style="{ color }">
          <component :is="icon" />
        </el-icon>
      </div>
    </div>
  </div>
</template>
