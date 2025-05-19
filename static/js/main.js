// Main JavaScript file for Biolectures MSU website

document.addEventListener('DOMContentLoaded', function() {
    // Initialize any components that need JavaScript
    initializeImageGallery();
    enhanceFormValidation();
    
    // Add class to hero section if it has a background image
    const heroSection = document.querySelector('.hero-section');
    if (heroSection && heroSection.style.backgroundImage) {
        heroSection.classList.add('with-image');
    }
});

// Function to initialize image galleries
function initializeImageGallery() {
    // This would be implemented if we had image galleries
    // For now, it's just a placeholder
    const galleryItems = document.querySelectorAll('.gallery-item');
    if (galleryItems.length > 0) {
        console.log('Gallery initialized with ' + galleryItems.length + ' items');
        
        // Add click event listeners to gallery items
        galleryItems.forEach(item => {
            item.addEventListener('click', function(e) {
                // Prevent default link behavior
                e.preventDefault();
                
                // Get image source
                const imgSrc = this.getAttribute('href');
                
                // Here you would open a lightbox or modal with the image
                console.log('Opening gallery image: ' + imgSrc);
            });
        });
    }
}

// Function to enhance form validation
function enhanceFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Check if the form needs validation
            if (!form.classList.contains('needs-validation')) return;
            
            // Prevent form submission
            e.preventDefault();
            
            // Add validation class
            form.classList.add('was-validated');
            
            // Check if the form is valid
            if (form.checkValidity()) {
                // If valid, submit the form
                form.submit();
            } else {
                // If invalid, show error messages
                const invalidFields = form.querySelectorAll(':invalid');
                if (invalidFields.length > 0) {
                    // Focus the first invalid field
                    invalidFields[0].focus();
                }
            }
        });
    });
}

// Function to handle responsive navigation
function toggleMobileMenu() {
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    
    if (navbarToggler && navbarCollapse) {
        navbarToggler.addEventListener('click', function() {
            navbarCollapse.classList.toggle('show');
        });
    }
}