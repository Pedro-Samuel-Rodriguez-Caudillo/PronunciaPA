import './style.css';

// Envolver la lógica que interactúa con el DOM para asegurarnos que el DOM esté cargado
document.addEventListener('DOMContentLoaded', async () => {


  // ===== Mobile menu toggle =====
  const menuBtn = document.getElementById('menuBtn') as HTMLButtonElement | null;
  const mobileMenu = document.getElementById('mobileMenu') as HTMLElement | null;
  if (menuBtn && mobileMenu) {
    menuBtn.addEventListener('click', () => {
      mobileMenu.classList.toggle('is-hidden');
    });
  }

  // Smooth scroll for anchors
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
      e.preventDefault();
  const href = (anchor as HTMLAnchorElement).getAttribute('href');
      // Evitar querySelector con "#" (selector inválido) o href vacío
      if (!href || href === '#') return;
      const target = document.querySelector(href);
      if (target) {
        if (mobileMenu) mobileMenu.classList.add('is-hidden');
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
  successMessage.classList.remove('is-hidden');
        formContacto.reset();
        setTimeout(() => {
          successMessage.classList.add('is-hidden');
        }, 3000);
      } else {
        // Mostrar error inline en vez de alert
        const formError = document.getElementById('formError');
          if (formError) {
          formError.textContent = 'Por favor ingresa un correo electrónico válido.';
          formError.classList.remove('is-hidden');
          // esconder tras unos segundos
          setTimeout(() => { formError.classList.add('is-hidden'); }, 4000);
        } else {
          // fallback
          console.warn('Correo inválido y no se encontró contenedor de error');
        }
      }
    });
  }

  // ===== Plugins y análisis (migrado desde public/index.html) =====
  const API_BASE_URL = (window as any).PRONUNCIAPA_API_BASE || 'http://localhost:8000';
  const pluginList = document.getElementById('pluginList') as HTMLElement | null;
  const pluginLoading = document.getElementById('pluginLoading') as HTMLElement | null;
  const pluginError = document.getElementById('pluginError') as HTMLElement | null;

  const analysisForm = document.getElementById('analysisForm') as HTMLFormElement | null;
  const analysisStatus = document.getElementById('analysisStatus') as HTMLElement | null;
  const analysisError = document.getElementById('analysisError') as HTMLElement | null;
  const analysisResult = document.getElementById('analysisResult') as HTMLElement | null;
  const resultText = document.getElementById('resultText') as HTMLElement | null;
  const resultLang = document.getElementById('resultLang') as HTMLElement | null;
  const resultRefIpa = document.getElementById('resultRefIpa') as HTMLElement | null;
  const resultHypIpa = document.getElementById('resultHypIpa') as HTMLElement | null;
  const resultPer = document.getElementById('resultPer') as HTMLElement | null;
  const resultMatches = document.getElementById('resultMatches') as HTMLElement | null;
  const resultSubstitutions = document.getElementById('resultSubstitutions') as HTMLElement | null;
  const resultInsertions = document.getElementById('resultInsertions') as HTMLElement | null;
  const resultDeletions = document.getElementById('resultDeletions') as HTMLElement | null;
  const resultOps = document.getElementById('resultOps') as HTMLElement | null;
  const resultPerClass = document.getElementById('resultPerClass') as HTMLElement | null;

  async function loadPlugins() {
    if (!pluginList) return;
    try {
      let data: any = null;
      try {
        const resp = await fetch(`${API_BASE_URL}/api/plugins`);
        if (!resp.ok) throw new Error('Respuesta inesperada del servidor');
        data = await resp.json();
      } catch (apiErr) {
        console.warn('loadPlugins: fallo al contactar backend:', apiErr);
        // fallback local
        try {
          const fbResp = await fetch('/plugins-fallback.json');
            if (fbResp.ok) {
            data = await fbResp.json();
            if (pluginLoading) pluginLoading.classList.add('is-hidden');
            if (pluginError) {
              pluginError.textContent = 'Usando lista de plugins de fallback (backend no disponible).';
              pluginError.classList.remove('is-hidden');
            }
          } else {
            throw apiErr;
          }
        } catch (fbErr) {
          throw apiErr;
        }
      }
      const entries = Object.entries(data?.plugins || {});
      pluginList.innerHTML = '';
      if (!entries.length) {
        pluginList.innerHTML = '<li class="text-sm text-gray-600">No se encontraron plugins registrados.</li>';
      } else {
        entries.forEach(([group, names]) => {
          const item = document.createElement('li');
          item.className = 'bg-white rounded-xl px-4 py-3 shadow flex flex-col sm:flex-row sm:items-center sm:justify-between';
          const title = document.createElement('span');
          title.className = 'font-semibold text-gray-700 capitalize';
          title.textContent = String(group);
          const values = document.createElement('span');
          values.className = 'text-sm text-gray-500 mt-2 sm:mt-0';
          values.textContent = (Array.isArray(names) && names.length) ? (names as string[]).join(', ') : 'Sin plugins disponibles';
          item.appendChild(title);
          item.appendChild(values);
          pluginList.appendChild(item);
        });
      }
  if (pluginLoading) pluginLoading.classList.add('is-hidden');
  if (pluginError) pluginError.classList.add('is-hidden');
    } catch (error) {
      if (pluginLoading) pluginLoading.classList.add('is-hidden');
      if (pluginError) {
        pluginError.textContent = 'No se pudieron obtener los plugins: ' + (error instanceof Error ? error.message : String(error));
        pluginError.classList.remove('is-hidden');
      }
      console.error('loadPlugins error', error);
    }
  }

  function renderList(container: HTMLElement | null, items: any[], formatItem: (it: any) => string) {
    if (!container) return;
    container.innerHTML = '';
    if (!Array.isArray(items) || !items.length) {
      const empty = document.createElement('li');
      empty.className = 'text-sm text-gray-500';
      empty.textContent = 'Sin datos disponibles.';
      container.appendChild(empty);
      return;
    }
    items.slice(0, 10).forEach((item) => {
      const li = document.createElement('li');
      li.className = 'bg-white/60 border border-gray-200 rounded-lg px-3 py-2';
      li.textContent = formatItem(item);
      container.appendChild(li);
    });
  }

  function renderPerClassList(container: HTMLElement | null, perClass: Record<string, any>) {
    if (!container) return;
    container.innerHTML = '';
    const entries = Object.entries(perClass || {});
    if (!entries.length) {
      const empty = document.createElement('li');
      empty.className = 'text-sm text-gray-500';
      empty.textContent = 'Sin estadísticas registradas.';
      container.appendChild(empty);
      return;
    }
    entries.slice(0, 10).forEach(([phoneme, stats]) => {
      const li = document.createElement('li');
      li.className = 'bg-white/60 border border-gray-200 rounded-lg px-3 py-2 flex flex-wrap gap-3';
      const title = document.createElement('span');
      title.className = 'font-semibold text-gray-700';
      title.textContent = phoneme;
      const details = document.createElement('span');
      details.className = 'text-sm text-gray-500';
      details.textContent = `Aciertos ${stats.matches} · Sustituciones ${stats.substitutions} · Inserciones ${stats.insertions} · Eliminaciones ${stats.deletions}`;
      li.appendChild(title);
      li.appendChild(details);
      container.appendChild(li);
    });
  }

  function showAnalysisResult(payload: any) {
    if (!analysisResult) return;
    if (resultText) resultText.textContent = payload.text || '—';
    if (resultLang) resultLang.textContent = payload.lang || '—';
    if (resultRefIpa) resultRefIpa.textContent = payload.ref_ipa || '—';
    if (resultHypIpa) resultHypIpa.textContent = payload.hyp_ipa || '—';
    if (resultPer) resultPer.textContent = (typeof payload.per === 'number') ? `${(payload.per * 100).toFixed(2)} %` : '—';
    if (resultMatches) resultMatches.textContent = `✔︎ ${payload.matches ?? 0} aciertos`;
    if (resultSubstitutions) resultSubstitutions.textContent = `↺ ${payload.substitutions ?? 0} sustituciones`;
    if (resultInsertions) resultInsertions.textContent = `＋ ${payload.insertions ?? 0} inserciones`;
    if (resultDeletions) resultDeletions.textContent = `− ${payload.deletions ?? 0} eliminaciones`;

    renderList(resultOps, payload.ops || [], (item) => {
      const ref = item.ref || '∅';
      const hyp = item.hyp || '∅';
      return `${item.op}: ${ref} → ${hyp}`;
    });
    renderPerClassList(resultPerClass, payload.per_class || {});
    analysisResult.classList.remove('is-hidden');
  }

  if (analysisForm) {
    analysisForm.addEventListener('submit', async (event) => {
      event.preventDefault();
  if (analysisError) analysisError.classList.add('is-hidden');
  if (analysisStatus) { analysisStatus.textContent = 'Procesando audio...'; analysisStatus.classList.remove('is-hidden'); }
  if (analysisResult) analysisResult.classList.add('is-hidden');

      const formData = new FormData(analysisForm);
      try {
        const response = await fetch(`${API_BASE_URL}/api/analyze`, { method: 'POST', body: formData });
        if (!response.ok) {
          let message = 'No se pudo procesar el análisis.';
          try { const errorPayload = await response.json(); if (errorPayload?.detail) message = errorPayload.detail; } catch (e) { message = 'No se pudo interpretar la respuesta del servidor.'; }
          throw new Error(message);
        }
        const payload = await response.json();
        showAnalysisResult(payload);
      } catch (err) {
        if (analysisError) { analysisError.textContent = err instanceof Error ? err.message : 'Ocurrió un error inesperado.'; analysisError.classList.remove('is-hidden'); }
      } finally {
        if (analysisStatus) analysisStatus.classList.add('is-hidden');
      }
    });
  }

  // Inicializar carga de plugins al montar
  loadPlugins();
});