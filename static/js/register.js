/* ===============================
   RegenArdhi - Register Page JavaScript
   =============================== */

// Form elements
const registerForm = document.getElementById('registerForm');
const gpsBtn = document.getElementById('gpsBtn');
const locationInput = document.getElementById('location');
const locationStatus = document.getElementById('locationStatus');

// Input fields
const firstName = document.getElementById('firstName');
const lastName = document.getElementById('lastName');
const email = document.getElementById('email');
const age = document.getElementById('age');
const password = document.getElementById('password');
const confirmPassword = document.getElementById('confirmPassword');
const terms = document.getElementById('terms');

// Error message elements
const firstNameError = document.getElementById('firstNameError');
const lastNameError = document.getElementById('lastNameError');
const emailError = document.getElementById('emailError');
const ageError = document.getElementById('ageError');
const locationError = document.getElementById('locationError');
const passwordError = document.getElementById('passwordError');
const confirmPasswordError = document.getElementById('confirmPasswordError');
const termsError = document.getElementById('termsError');

// Validation functions
function validateFirstName() {
  const value = firstName.value.trim();
  if (value === '') {
    showError(firstNameError, 'First name is required');
    return false;
  }
  if (value.length < 2) {
    showError(firstNameError, 'First name must be at least 2 characters');
    return false;
  }
  if (!/^[a-zA-Z\s-]+$/.test(value)) {
    showError(firstNameError, 'First name can only contain letters');
    return false;
  }
  hideError(firstNameError);
  return true;
}

function validateLastName() {
  const value = lastName.value.trim();
  if (value === '') {
    showError(lastNameError, 'Last name is required');
    return false;
  }
  if (value.length < 2) {
    showError(lastNameError, 'Last name must be at least 2 characters');
    return false;
  }
  if (!/^[a-zA-Z\s-]+$/.test(value)) {
    showError(lastNameError, 'Last name can only contain letters');
    return false;
  }
  hideError(lastNameError);
  return true;
}

function validateEmail() {
  const value = email.value.trim();
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

function validateAge() {
  const value = age.value;
  const ageNum = parseInt(value);
  
  if (value === '') {
    showError(ageError, 'Age is required');
    return false;
  }
  if (isNaN(ageNum) || ageNum < 13) {
    showError(ageError, 'You must be at least 13 years old');
    return false;
  }
  if (ageNum > 120) {
    showError(ageError, 'Please enter a valid age');
    return false;
  }
  hideError(ageError);
  return true;
}

function validateLocation() {
  const value = locationInput.value.trim();
  if (value === '') {
    showError(locationError, 'Location is required');
    return false;
  }
  if (value.length < 3) {
    showError(locationError, 'Location must be at least 3 characters');
    return false;
  }
  hideError(locationError);
  return true;
}

function validatePassword() {
  const value = password.value;
  
  if (value === '') {
    showError(passwordError, 'Password is required');
    return false;
  }
  if (value.length < 8) {
    showError(passwordError, 'Password must be at least 8 characters');
    return false;
  }
  if (!/[A-Z]/.test(value)) {
    showError(passwordError, 'Password must contain at least one uppercase letter');
    return false;
  }
  if (!/[a-z]/.test(value)) {
    showError(passwordError, 'Password must contain at least one lowercase letter');
    return false;
  }
  if (!/[0-9]/.test(value)) {
    showError(passwordError, 'Password must contain at least one number');
    return false;
  }
  hideError(passwordError);
  return true;
}

function validateConfirmPassword() {
  const value = confirmPassword.value;
  
  if (value === '') {
    showError(confirmPasswordError, 'Please confirm your password');
    return false;
  }
  if (value !== password.value) {
    showError(confirmPasswordError, 'Passwords do not match');
    return false;
  }
  hideError(confirmPasswordError);
  return true;
}

function validateTerms() {
  if (!terms.checked) {
    showError(termsError, 'You must agree to the terms and conditions');
    return false;
  }
  hideError(termsError);
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
firstName.addEventListener('blur', validateFirstName);
lastName.addEventListener('blur', validateLastName);
email.addEventListener('blur', validateEmail);
age.addEventListener('blur', validateAge);
locationInput.addEventListener('blur', validateLocation);
password.addEventListener('blur', validatePassword);
confirmPassword.addEventListener('blur', validateConfirmPassword);
terms.addEventListener('change', validateTerms);

// Password match validation on typing
confirmPassword.addEventListener('input', () => {
  if (confirmPassword.value.length > 0) {
    validateConfirmPassword();
  }
});

// GPS Location functionality
if (gpsBtn) {
  gpsBtn.addEventListener('click', getGPSLocation);
}

function getGPSLocation() {
  if (!navigator.geolocation) {
    locationStatus.textContent = 'GPS not supported by your browser';
    locationStatus.style.color = '#f44336';
    return;
  }

  // Show loading state
  gpsBtn.classList.add('loading');
  gpsBtn.disabled = true;
  locationStatus.textContent = 'Getting your location...';
  locationStatus.style.color = '#2e7d32';

  navigator.geolocation.getCurrentPosition(
    // Success callback
    async (position) => {
      const lat = position.coords.latitude;
      const lon = position.coords.longitude;

      try {
        // Use reverse geocoding to get location name
        const response = await fetch(
          `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`
        );
        const data = await response.json();

        // Format location string
        const locationParts = [];
        if (data.address.city) locationParts.push(data.address.city);
        else if (data.address.town) locationParts.push(data.address.town);
        else if (data.address.village) locationParts.push(data.address.village);
        
        if (data.address.state) locationParts.push(data.address.state);
        if (data.address.country) locationParts.push(data.address.country);

        const locationString = locationParts.join(', ') || `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
        
        locationInput.value = locationString;
        locationStatus.textContent = '✓ Location obtained successfully';
        locationStatus.style.color = '#4caf50';
        
        hideError(locationError);
      } catch (error) {
        // If reverse geocoding fails, use coordinates
        locationInput.value = `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
        locationStatus.textContent = '✓ Coordinates obtained';
        locationStatus.style.color = '#4caf50';
      }

      gpsBtn.classList.remove('loading');
      gpsBtn.disabled = false;
    },
    // Error callback
    (error) => {
      let errorMessage = '';
      switch (error.code) {
        case error.PERMISSION_DENIED:
          errorMessage = 'Location access denied. Please enable location permissions.';
          break;
        case error.POSITION_UNAVAILABLE:
          errorMessage = 'Location information unavailable.';
          break;
        case error.TIMEOUT:
          errorMessage = 'Location request timed out.';
          break;
        default:
          errorMessage = 'An error occurred while getting location.';
      }
      
      locationStatus.textContent = errorMessage;
      locationStatus.style.color = '#f44336';
      gpsBtn.classList.remove('loading');
      gpsBtn.disabled = false;
    },
    // Options
    {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0
    }
  );
}

// Form submission
registerForm.addEventListener('submit', (e) => {
  // Prevent default submission first
  e.preventDefault();

  // Validate all fields
  const isFirstNameValid = validateFirstName();
  const isLastNameValid = validateLastName();
  const isEmailValid = validateEmail();
  const isAgeValid = validateAge();
  const isLocationValid = validateLocation();
  const isPasswordValid = validatePassword();
  const isConfirmPasswordValid = validateConfirmPassword();
  const areTermsValid = validateTerms();

  // Check if all validations passed
  if (
    isFirstNameValid &&
    isLastNameValid &&
    isEmailValid &&
    isAgeValid &&
    isLocationValid &&
    isPasswordValid &&
    isConfirmPasswordValid &&
    areTermsValid
  ) {
    // All validations passed, submit the form to backend
    console.log('Form is valid, submitting to backend...');
    registerForm.submit();
  } else {
    // Scroll to first error
    const firstError = document.querySelector('.error-message.active');
    if (firstError) {
      firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }
});

// Clear location status after 5 seconds
let locationStatusTimeout;
locationInput.addEventListener('input', () => {
  clearTimeout(locationStatusTimeout);
  locationStatusTimeout = setTimeout(() => {
    locationStatus.textContent = '';
  }, 5000);
});

// Prevent form submission on Enter key in input fields (except submit button)
const inputs = registerForm.querySelectorAll('input:not([type="submit"])');
inputs.forEach((input, index) => {
  input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      // Move to next input or submit if last input
      const formElements = Array.from(registerForm.elements);
      const currentIndex = formElements.indexOf(e.target);
      const nextElement = formElements[currentIndex + 1];
      
      if (nextElement && nextElement.tagName === 'INPUT') {
        nextElement.focus();
      }
    }
  });
});

// Auto-capitalize first and last name
firstName.addEventListener('input', (e) => {
  e.target.value = e.target.value.replace(/\b\w/g, l => l.toUpperCase());
});

lastName.addEventListener('input', (e) => {
  e.target.value = e.target.value.replace(/\b\w/g, l => l.toUpperCase());
});

// Trim whitespace on blur for all text inputs
const textInputs = registerForm.querySelectorAll('input[type="text"], input[type="email"]');
textInputs.forEach(input => {
  input.addEventListener('blur', () => {
    input.value = input.value.trim();
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

