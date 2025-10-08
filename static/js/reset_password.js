/* ===============================
   RegenArdhi - Reset Password JavaScript
   =============================== */

// Form elements
const resetForm = document.getElementById('resetForm');
const emailInput = document.getElementById('email');
const emailError = document.getElementById('emailError');

// Validation function
function validateEmail() {
  const value = emailInput.value.trim();
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  
  if (value === '') {
    showError(emailError, 'Email is required');
    return false;
  }
  if (!emailRegex.test(value)) {
    showError(emailError, 'Please enter a valid email address');
    return false;
  }
  hideError(emailError);
  return true;
}

// Helper functions
function showError(element, message) {
  element.textContent = message;
  element.classList.add('active');
}

function hideError(element) {
  element.textContent = '';
  element.classList.remove('active');
}

// Real-time validation
emailInput.addEventListener('blur', validateEmail);

// Clear error on input
emailInput.addEventListener('input', () => {
  if (emailError.classList.contains('active')) {
    hideError(emailError);
  }
});

// Form submission
resetForm.addEventListener('submit', (e) => {
  const isEmailValid = validateEmail();
  
  if (!isEmailValid) {
    e.preventDefault();
    emailInput.focus();
  }
  // If valid, form will submit normally to the server
});

// Auto-dismiss flash messages after 5 seconds
const alerts = document.querySelectorAll('.alert');
alerts.forEach(alert => {
  setTimeout(() => {
    alert.style.opacity = '0';
    alert.style.transform = 'translateY(-20px)';
    setTimeout(() => {
      alert.remove();
    }, 300);
  }, 5000);
});