// Sidebar icon set for the reCamera panel.
//
// The namespace is `recamera_motion` rather than `recamera` so that it can be
// installed next to the reCamera Pro integration, which owns `recamera`.
window.customIconsets = window.customIconsets || {};
window.customIconsets.recamera_motion = async (iconName) => {
  const icons = {
    // Camera body with a dashed detection polygon inside.
    detect:
      "M3 7.5 11.5 2.6 21 7.9v8.4l-9.5 5.2L3 16.4V7.5m8.5-2.6-6.2 3.4 6.2 3.4 6.2-3.4-6.2-3.4M5 9.9v5.5l6.5 3.6v-5.6L5 9.9m8.5 3.5v5.6l5.5-3.1v-5.6l-5.5 3.1M8.6 12.2l2.6 1.6-1.1 2.4-2.7-1.4 1.2-2.6m5.4-1.1 2.6 1.3-1.2 2.6-2.6-1.5 1.2-2.4",
  };
  if (!icons[iconName]) return {};
  return { viewBox: "0 0 24 24", path: icons[iconName] };
};
window.dispatchEvent(new Event("iron-iconset-added"));
