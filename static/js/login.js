/* ===============================
   RegenArdhi - Login Page JavaScript
   =============================== */

// Form elements
const loginForm = document.getElementById('loginForm');
const togglePassword = document.getElementById('togglePassword');
const passwordInput = document.getElementById('password');
const emailInput = document.getElementById('email');

// Error message elements
const emailError = document.getElementById('emailError');
const passwordError = document.getElementById('passwordError');

// Toggle password visibility
togglePassword.addEventListener('click', () => {
  const type = passwordInput.type === 'password' ? 'text' : 'password';
  passwordInput.type = type;
  
  // Toggle icon
  const icon = togglePassword.querySelector('i');
  if (type === 'password') {
    icon.classList.remove('fa-eye-slash');
    icon.classList.add('fa-eye');
  } else {
    icon.classList.remove('fa-eye');
    icon.classList.add('fa-eye-slash');
  }
});

// Validation functions
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

function validatePassword() {
  const value = passwordInput.value;
  
  if (value === '') {
    showError(passwordError, 'Password is required');
    return false;
  }
  hideError(passwordError);
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
passwordInput.addEventListener('blur', validatePassword);

// Clear error on input
emailInput.addEventListener('input', () => {
  if (emailError.classList.contains('active')) {
    hideError(emailError);
  }
});

passwordInput.addEventListener('input', () => {
  if (passwordError.classList.contains('active')) {
    hideError(passwordError);
  }
});

// Form submission
loginForm.addEventListener('submit', (e) => {
  const isEmailValid = validateEmail();
  const isPasswordValid = validatePassword();
  
  if (!isEmailValid || !isPasswordValid) {
    e.preventDefault();
    
    // Scroll to first error
    const firstError = document.querySelector('.error-message.active');
    if (firstError) {
      firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }
  // If valid, form will submit normally to the server
});

// Enter key navigation
const inputs = loginForm.querySelectorAll('input:not([type="submit"])');
inputs.forEach((input, index) => {
  input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (index < inputs.length - 1) {
        inputs[index + 1].focus();
      } else {
        loginForm.requestSubmit();
      }
    }
  });
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

// Social login placeholders (you can implement these later)
const socialButtons = document.querySelectorAll('.btn-social');
socialButtons.forEach(button => {
  button.addEventListener('click', (e) => {
    e.preventDefault();
    alert('Social login will be implemented soon!');
  });
});