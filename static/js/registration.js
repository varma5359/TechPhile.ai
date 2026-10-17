document.addEventListener('DOMContentLoaded', function() {
    // Initialize form and event listeners
    const form = document.getElementById('registrationForm');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }

    // Initialize role tabs and forms
    initializeRoleTabs();

    // Initialize password visibility toggles
    initializePasswordToggles();

    // Initialize file upload display
    initializeFileUpload();
});

function handleFormSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const submitButton = form.querySelector('button[type="submit"]');
    const originalButtonText = submitButton.innerHTML;
    
    // Show loading state
    submitButton.disabled = true;
    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';

    const formData = new FormData(form);
    
    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { throw err; });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Show success modal
            const successModal = new bootstrap.Modal(document.getElementById('successModal'));
            successModal.show();
            
            // Redirect after delay
            setTimeout(() => {
                window.location.href = data.redirect_url || "/login/";
            }, 3000);
        } else {
            // Display form errors
            displayFormErrors(data.errors || {});
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showError('An error occurred during registration. Please try again.');
    })
    .finally(() => {
        submitButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
    });
}

function initializeRoleTabs() {
    const roleRadios = document.querySelectorAll('input[name="user_type"]');
    const roleForms = document.querySelectorAll('.role-form');
    
    function updateForms() {
        const selectedRole = document.querySelector('input[name="user_type"]:checked')?.value?.toLowerCase();
        
        if (!selectedRole) return;
        
        // Hide all forms
        roleForms.forEach(form => form.style.display = 'none');
        
        // Show selected form
        const activeForm = document.getElementById(`${selectedRole}-form`);
        if (activeForm) activeForm.style.display = 'block';
        
        // Update active tab
        document.querySelectorAll('.role-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        
        const activeTab = document.querySelector(`.role-tab input[value="${selectedRole.toUpperCase()}"]`)?.parentElement;
        if (activeTab) activeTab.classList.add('active');
    }
    
    roleRadios.forEach(radio => {
        radio.addEventListener('change', updateForms);
    });
    
    // Initialize on page load
    updateForms();
}

function initializePasswordToggles() {
    document.querySelectorAll('.toggle-password').forEach(button => {
        button.addEventListener('click', function() {
            const input = this.parentElement.querySelector('input');
            const icon = this.querySelector('i');
            
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.replace('fa-eye', 'fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.replace('fa-eye-slash', 'fa-eye');
            }
        });
    });
}

function initializeFileUpload() {
    const fileInput = document.getElementById('id_profile_picture');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const label = this.nextElementSibling;
            if (this.files.length > 0) {
                label.querySelector('span').textContent = this.files[0].name;
            } else {
                label.querySelector('span').textContent = 'Choose a file';
            }
        });
    }
}

function displayFormErrors(errors) {
    // Clear previous errors
    document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    document.querySelectorAll('.error-message').forEach(el => el.remove());
    
    // Display user form errors
    if (errors.user_errors) {
        for (const [field, messages] of Object.entries(errors.user_errors)) {
            const input = document.querySelector(`[name="${field}"]`);
            if (input) {
                input.classList.add('is-invalid');
                const errorDiv = document.createElement('div');
                errorDiv.className = 'error-message';
                errorDiv.textContent = Array.isArray(messages) ? messages.join(' ') : messages;
                input.parentNode.appendChild(errorDiv);
            }
        }
    }
    
    // Display profile errors
    if (errors.profile_errors) {
        for (const [field, messages] of Object.entries(errors.profile_errors)) {
            const input = document.querySelector(`[name="${field}"]`);
            if (input) {
                input.classList.add('is-invalid');
                const errorDiv = document.createElement('div');
                errorDiv.className = 'error-message';
                errorDiv.textContent = Array.isArray(messages) ? messages.join(' ') : messages;
                input.parentNode.appendChild(errorDiv);
            }
        }
    }
    
    // Scroll to first error
    const firstError = document.querySelector('.is-invalid');
    if (firstError) {
        firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function showError(message) {
    const errorDisplay = document.getElementById('form-error-display');
    if (errorDisplay) {
        errorDisplay.textContent = message;
        errorDisplay.style.display = 'block';
        errorDisplay.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}