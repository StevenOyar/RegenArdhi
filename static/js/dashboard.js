/* ===============================
   RegenArdhi - Dashboard JavaScript
   =============================== */

// ========== DOM Elements ==========
const userMenuBtn = document.getElementById('userMenuBtn');
const userDropdown = document.getElementById('userDropdown');
const notificationBtn = document.getElementById('notificationBtn');
const notificationDropdown = document.getElementById('notificationDropdown');
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const navLinks = document.getElementById('navLinks');
const alerts = document.querySelectorAll('.alert');

// ========== User Menu Toggle ==========
if (userMenuBtn && userDropdown) {
  userMenuBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    userDropdown.classList.toggle('active');
    userMenuBtn.classList.toggle('active');
    
    // Close notification dropdown if open
    if (notificationDropdown) {
      notificationDropdown.classList.remove('active');
    }
  });
}

// ========== Notification Menu Toggle ==========
if (notificationBtn && notificationDropdown) {
  notificationBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    notificationDropdown.classList.toggle('active');
    
    // Close user dropdown if open
    if (userDropdown) {
      userDropdown.classList.remove('active');
      userMenuBtn.classList.remove('active');
    }
  });
}

// ========== Mobile Menu Toggle ==========
if (mobileMenuBtn && navLinks) {
  mobileMenuBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    navLinks.classList.toggle('mobile-open');
    
    // Toggle icon
    const icon = mobileMenuBtn.querySelector('i');
    if (navLinks.classList.contains('mobile-open')) {
      icon.classList.remove('fa-bars');
      icon.classList.add('fa-times');
    } else {
      icon.classList.remove('fa-times');
      icon.classList.add('fa-bars');
    }
  });
}

// ========== Close Dropdowns on Outside Click ==========
document.addEventListener('click', (e) => {
  // Close user dropdown
  if (userDropdown && !userMenuBtn.contains(e.target) && !userDropdown.contains(e.target)) {
    userDropdown.classList.remove('active');
    userMenuBtn.classList.remove('active');
  }
  
  // Close notification dropdown
  if (notificationDropdown && !notificationBtn.contains(e.target) && !notificationDropdown.contains(e.target)) {
    notificationDropdown.classList.remove('active');
  }
  
  // Close mobile menu
  if (navLinks && !mobileMenuBtn.contains(e.target) && !navLinks.contains(e.target)) {
    navLinks.classList.remove('mobile-open');
    const icon = mobileMenuBtn.querySelector('i');
    icon.classList.remove('fa-times');
    icon.classList.add('fa-bars');
  }
});

// ========== Mark Notifications as Read ==========
const markReadBtn = document.querySelector('.mark-read-btn');
if (markReadBtn) {
  markReadBtn.addEventListener('click', (e) => {
    e.preventDefault();
    const unreadItems = document.querySelectorAll('.notification-item.unread');
    unreadItems.forEach(item => {
      item.classList.remove('unread');
    });
    
    // Update badge
    const badge = document.querySelector('.badge');
    if (badge) {
      badge.textContent = '0';
      setTimeout(() => {
        badge.style.display = 'none';
      }, 300);
    }
  });
}

// ========== Individual Notification Click ==========
const notificationItems = document.querySelectorAll('.notification-item');
notificationItems.forEach(item => {
  item.addEventListener('click', () => {
    item.classList.remove('unread');
    
    // Update badge count
    const badge = document.querySelector('.badge');
    if (badge) {
      const unreadCount = document.querySelectorAll('.notification-item.unread').length;
      badge.textContent = unreadCount;
      if (unreadCount === 0) {
        badge.style.display = 'none';
      }
    }
  });
});

// ========== Flash Messages Auto-Dismiss ==========
alerts.forEach(alert => {
  // Add close button functionality
  const closeBtn = alert.querySelector('.close-alert');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      dismissAlert(alert);
    });
  }
  
  // Auto-dismiss after 5 seconds
  setTimeout(() => {
    dismissAlert(alert);
  }, 5000);
});

function dismissAlert(alert) {
  alert.style.opacity = '0';
  alert.style.transform = 'translateX(100%)';
  setTimeout(() => {
    alert.remove();
  }, 300);
}

// ========== Animate Stats on Load ==========
const statNumbers = document.querySelectorAll('.stat-number');
const observerOptions = {
  threshold: 0.5,
  rootMargin: '0px'
};

const statsObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      animateStatNumber(entry.target);
      statsObserver.unobserve(entry.target);
    }
  });
}, observerOptions);

statNumbers.forEach(stat => {
  statsObserver.observe(stat);
});

function animateStatNumber(element) {
  const text = element.textContent;
  const hasPercent = text.includes('%');
  const hasUnit = element.querySelector('.unit');
  
  let targetValue = parseInt(text.replace(/[^0-9]/g, ''));
  
  if (isNaN(targetValue) || targetValue === 0) return;
  
  let currentValue = 0;
  const duration = 1500; // 1.5 seconds
  const increment = targetValue / (duration / 16); // 60fps
  
  const counter = setInterval(() => {
    currentValue += increment;
    
    if (currentValue >= targetValue) {
      currentValue = targetValue;
      clearInterval(counter);
    }
    
    const displayValue = Math.floor(currentValue);
    
    if (hasPercent) {
      element.textContent = displayValue + '%';
    } else if (hasUnit) {
      element.innerHTML = displayValue + element.querySelector('.unit').outerHTML;
    } else {
      element.textContent = displayValue;
    }
  }, 16);
}

// ========== Progress Ring Animation ==========
const progressRings = document.querySelectorAll('.progress-ring');

progressRings.forEach(ring => {
  const percentage = parseInt(ring.querySelector('span').textContent);
  const degrees = (percentage / 100) * 360;
  
  // Animate the conic gradient
  ring.style.background = `conic-gradient(
    var(--primary-green) ${degrees}deg,
    var(--border-color) ${degrees}deg
  )`;
});

// ========== Health Metrics Animation ==========
const metricFills = document.querySelectorAll('.metric-fill');

const metricsObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const fill = entry.target;
      const targetWidth = fill.style.width;
      fill.style.width = '0%';
      
      setTimeout(() => {
        fill.style.width = targetWidth;
      }, 100);
      
      metricsObserver.unobserve(fill);
    }
  });
}, observerOptions);

metricFills.forEach(fill => {
  metricsObserver.observe(fill);
});

// ========== Project Item Interactions ==========
const projectItems = document.querySelectorAll('.project-item');

projectItems.forEach(item => {
  item.addEventListener('click', function() {
    const projectName = this.querySelector('.project-info h3').textContent;
    console.log(`Clicked on project: ${projectName}`);
    // Here you would navigate to project details page
    // window.location.href = `/project/${projectId}`;
  });
});

// ========== Activity Item Interactions ==========
const activityItems = document.querySelectorAll('.activity-item');

activityItems.forEach(item => {
  item.addEventListener('click', function() {
    console.log('Activity item clicked');
    // Here you would show activity details
  });
});

// ========== Quick Action Buttons ==========
const actionButtons = document.querySelectorAll('.action-btn');

actionButtons.forEach(btn => {
  btn.addEventListener('click', function() {
    const actionName = this.querySelector('span').textContent;
    console.log(`Quick action clicked: ${actionName}`);
    
    // Add visual feedback
    this.style.transform = 'scale(0.95)';
    setTimeout(() => {
      this.style.transform = '';
    }, 150);
    
    // Here you would handle the specific action
    // For example:
    // if (actionName === 'Add Location') { showLocationModal(); }
  });
});

// ========== New Project Button ==========
const newProjectBtn = document.getElementById('newProjectBtn');

if (newProjectBtn) {
  newProjectBtn.addEventListener('click', () => {
    console.log('New project button clicked');
    // Here you would show new project modal or navigate to project creation page
    // showNewProjectModal();
  });
}

// ========== Smooth Scroll for Anchor Links ==========
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function(e) {
    const href = this.getAttribute('href');
    if (href !== '#' && document.querySelector(href)) {
      e.preventDefault();
      document.querySelector(href).scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    }
  });
});

// ========== Tooltip Functionality ==========
const tooltipIcons = document.querySelectorAll('.tooltip-icon');

tooltipIcons.forEach(icon => {
  icon.addEventListener('mouseenter', function() {
    const title = this.getAttribute('title');
    if (!title) return;
    
    // Create tooltip element
    const tooltip = document.createElement('div');
    tooltip.className = 'custom-tooltip';
    tooltip.textContent = title;
    tooltip.style.cssText = `
      position: absolute;
      background: rgba(0, 0, 0, 0.9);
      color: white;
      padding: 0.5rem 0.75rem;
      border-radius: 6px;
      font-size: 0.75rem;
      white-space: nowrap;
      z-index: 1000;
      pointer-events: none;
    `;
    
    document.body.appendChild(tooltip);
    
    // Position tooltip
    const rect = this.getBoundingClientRect();
    tooltip.style.top = `${rect.top - tooltip.offsetHeight - 8}px`;
    tooltip.style.left = `${rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2)}px`;
    
    // Store reference
    this.tooltipElement = tooltip;
    
    // Remove title to prevent default tooltip
    this.setAttribute('data-title', title);
    this.removeAttribute('title');
  });
  
  icon.addEventListener('mouseleave', function() {
    if (this.tooltipElement) {
      this.tooltipElement.remove();
      this.tooltipElement = null;
    }
    
    // Restore title
    const title = this.getAttribute('data-title');
    if (title) {
      this.setAttribute('title', title);
      this.removeAttribute('data-title');
    }
  });
});

// ========== Refresh Stats (Simulated) ==========
function refreshDashboardStats() {
  console.log('Refreshing dashboard stats...');
  // Here you would make an API call to get updated stats
  // fetch('/api/dashboard/stats')
  //   .then(response => response.json())
  //   .then(data => updateDashboard(data));
}

// Auto-refresh every 5 minutes
setInterval(refreshDashboardStats, 300000);

// ========== Initialize Dashboard ==========
function initDashboard() {
  console.log('Dashboard initialized');
  
  // Load any initial data
  // fetchDashboardData();
  
  // Set up event listeners for dynamic content
  // setupDynamicListeners();
}

// Run initialization when DOM is fully loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initDashboard);
} else {
  initDashboard();
}

// ========== Utility Functions ==========

// Format numbers with commas
function formatNumber(num) {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// Format date to relative time
function formatRelativeTime(date) {
  const now = new Date();
  const diff = now - new Date(date);
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  
  if (seconds < 60) return 'just now';
  if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
  if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  if (days < 30) return `${days} day${days > 1 ? 's' : ''} ago`;
  return new Date(date).toLocaleDateString();
}

// Export functions for use in other scripts if needed
window.dashboardUtils = {
  formatNumber,
  formatRelativeTime,
  refreshDashboardStats
};