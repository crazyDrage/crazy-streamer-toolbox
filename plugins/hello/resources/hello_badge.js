export default {
  template: `
    <div style="display: flex; gap: 8px; align-items: center; cursor: pointer" title="click to refresh"
         @click="$emit('refresh')">
      <img :src="icon" width="28" height="28" alt="">
      <span>{{ count }} greeting{{ count === 1 ? "" : "s" }} so far</span>
    </div>`,
  props: { icon: String, count: Number },
};
