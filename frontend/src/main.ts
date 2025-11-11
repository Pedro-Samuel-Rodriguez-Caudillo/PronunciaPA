import './style.css';
// Envolver la lógica que interactúa con el DOM para asegurarnos que el DOM esté cargado
document.addEventListener('DOMContentLoaded', () => {
  // Mobile menu toggle
  const menuBtn = document.getElementById('menuBtn') as HTMLButtonElement | null;
  const mobileMenu = document.getElementById('mobileMenu') as HTMLElement | null;
  if (menuBtn && mobileMenu) {
    menuBtn.addEventListener('click', () => {
      mobileMenu.classList.toggle('hidden');
    });
  }

  // Smooth scroll for anchors
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
      e.preventDefault();
      const href = (anchor as HTMLAnchorElement).getAttribute('href');
      if (!href) return;
      const target = document.querySelector(href);
      if (target) {
        if (mobileMenu) mobileMenu.classList.add('hidden');
        (target as HTMLElement).scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // Fade-in sections on view
  const observerOptions = { threshold: 0.1, rootMargin: '0px 0px -100px 0px' };
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        (entry.target as HTMLElement).style.opacity = '1';
        (entry.target as HTMLElement).style.transform = 'translateY(0)';
      }
    });
  }, observerOptions);

  document.querySelectorAll('section').forEach(section => {
    (section as HTMLElement).style.opacity = '0';
    (section as HTMLElement).style.transform = 'translateY(20px)';
    (section as HTMLElement).style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(section);
  });

  // Testimonials scroll functionality
  const container = document.getElementById('testimonialsContainer');
  const scrollLeftBtn = document.getElementById('scrollLeft') as HTMLButtonElement | null;
  const scrollRightBtn = document.getElementById('scrollRight') as HTMLButtonElement | null;

  if (container && scrollLeftBtn && scrollRightBtn) {
    const scContainer = container as HTMLElement;
    scrollRightBtn.addEventListener('click', () => {
      scContainer.scrollBy({ left: 300, behavior: 'smooth' });
    });
    scrollLeftBtn.addEventListener('click', () => {
      scContainer.scrollBy({ left: -300, behavior: 'smooth' });
    });

    function updateScrollButtons() {
      if (!scrollLeftBtn || !scrollRightBtn) return;
      scrollLeftBtn.disabled = scContainer.scrollLeft <= 0;
      scrollRightBtn.disabled = scContainer.scrollLeft >= scContainer.scrollWidth - scContainer.clientWidth - 10;
      // Sincronizar aria-disabled para accesibilidad
      try {
        scrollLeftBtn.setAttribute('aria-disabled', String(!!scrollLeftBtn.disabled));
        scrollRightBtn.setAttribute('aria-disabled', String(!!scrollRightBtn.disabled));
      } catch (e) {
        // noop
      }
    }
    scContainer.addEventListener('scroll', updateScrollButtons);
    updateScrollButtons();
  }

  // Eliminado: lógica de modales de descarga y su carga dinámica (modal.html)

  // Formulario de contacto: validación y mensaje de éxito
  const formContacto = document.getElementById('formContacto') as HTMLFormElement | null;
  const successMessage = document.getElementById('successMessage') as HTMLElement | null;
  const correoInput = document.getElementById('correoContacto') as HTMLInputElement | null;

  if (formContacto && successMessage && correoInput) {
    formContacto.addEventListener('submit', (event) => {
      event.preventDefault();

      let valid = true;
      const emailRegex = /^[^@]+@[^@]+\.[a-zA-Z]{2,}$/;
      const correo = correoInput.value.trim();

      if (correo === '' || !emailRegex.test(correo)) {
        valid = false;
      }

      if (valid) {
        successMessage.classList.remove('hidden');
        formContacto.reset();
        setTimeout(() => {
          successMessage.classList.add('hidden');
        }, 3000);
      } else {
        // Mostrar error inline en vez de alert
        const formError = document.getElementById('formError');
        if (formError) {
          formError.textContent = 'Por favor ingresa un correo electrónico válido.';
          formError.classList.remove('hidden');
          // esconder tras unos segundos
          setTimeout(() => { formError.classList.add('hidden'); }, 4000);
        } else {
          // fallback
          console.warn('Correo inválido y no se encontró contenedor de error');
        }
      }
    });
  }

  // Eliminado: lógica y carga dinámica del modal de micrófono (mic-modal.html)
});