// Simple scroll Reveal effect
document.addEventListener('DOMContentLoaded', () => {
    const observerOptions = {
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    const cards = document.querySelectorAll('.feature-card');
    cards.forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';
        card.style.transition = 'all 0.6s ease-out';
        observer.observe(card);
    });

    // Logo parallax effect on mouse move
    const heroImage = document.querySelector('.hero-image img');
    document.addEventListener('mousemove', (e) => {
        const x = (window.innerWidth / 2 - e.pageX) / 50;
        const y = (window.innerHeight / 2 - e.pageY) / 50;
        heroImage.style.transform = `rotateY(${x}deg) rotateX(${-y}deg)`;
    });

    // Contact Form Submission
    const contactForm = document.getElementById('contactForm');
    if (contactForm) {
        contactForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(contactForm);
            try {
                const response = await fetch('/api/contact', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                alert(result.message);
                contactForm.reset();
            } catch (error) {
                alert('Bir hata oluştu, lütfen tekrar deneyin.');
            }
        });
    }

    // Download Tracking
    const downloadBtns = document.querySelectorAll('.btn-download-nav, .btn-primary');
    downloadBtns.forEach(btn => {
        if (btn.innerText.includes('İNDİR') || btn.innerText.includes('DENEYİN')) {
            btn.addEventListener('click', async (e) => {
                try {
                    const response = await fetch('/api/download');
                    const result = await response.json();
                    console.log('Download stats updated:', result.message);
                    // In a real app, you'd trigger actual file download here
                } catch (error) {
                    console.error('Download tracking failed');
                }
            });
        }
    });
});
