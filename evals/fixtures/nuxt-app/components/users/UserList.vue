<script lang="ts">
export default {
  data() {
    return {
      users: [] as any[],
      favorites: JSON.parse(window.localStorage.getItem("favorites") || "[]"),
    }
  },
  async created() {
    const response = await fetch("https://api.example.com/users")
    this.users = await response.json()
  },
  methods: {
    toggleFavorite(user: any) {
      this.favorites.push(user.id)
      window.localStorage.setItem("favorites", JSON.stringify(this.favorites))
    },
  },
}
</script>

<template>
  <ul>
    <li v-for="user in users" :key="user.id">
      <strong>{{ user.name }}</strong>
      <div v-html="user.bio" />
      <button @click="toggleFavorite(user)">В избранное</button>
    </li>
  </ul>
</template>
