// ═══════════════════════════════════════════════════════════════════════════════
// SIWES Logbook Manager - Main JavaScript
// ═══════════════════════════════════════════════════════════════════════════════

// ─── Theme Toggle ─────────────────────────────────────────────────────────────
function toggleTheme() {
  const html = document.documentElement;
  const currentTheme = html.getAttribute('data-theme');
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
  
  html.setAttribute('data-theme', newTheme);
  localStorage.setItem('theme', newTheme);
  
  // Update button emoji
  const themeBtn = document.getElementById('themeToggle');
  if (themeBtn) {
    themeBtn.textContent = newTheme === 'dark' ? '☀️' : '🌙';
  }
}

// ─── Initialize Theme on Page Load ─────────────────────────────────────────────
function initializeTheme() {
  const html = document.documentElement;
  const savedTheme = localStorage.getItem('theme') || 'dark';
  html.setAttribute('data-theme', savedTheme);
  
  // Update button emoji
  const themeBtn = document.getElementById('themeToggle');
  if (themeBtn) {
    themeBtn.textContent = savedTheme === 'dark' ? '☀️' : '🌙';
  }
}

// ─── Sidebar Toggle (Mobile) ───────────────────────────────────────────────────
function openSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  if (sidebar) {
    sidebar.classList.add('open');
    overlay.classList.add('open');
  }
}

function closeSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  if (sidebar) {
    sidebar.classList.remove('open');
    overlay.classList.remove('open');
  }
}

// ─── Initialize on Page Load ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  initializeTheme();
});

// Export for use in other scripts
window.SIWES = {
  toggleTheme,
  initializeTheme,
  openSidebar,
  closeSidebar
};
