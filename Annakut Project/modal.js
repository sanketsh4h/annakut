/* ============================================
   REUSABLE MODAL CLASS
   ============================================ */

/**
 * Reusable Modal Class
 * Creates an animated modal with language toggle support
 *
 * @example
 * // Simple usage with default options
 * const modal = new Modal({
 *   modalSelector: '#my-modal',
 *   backdropSelector: '#modal-backdrop',
 *   triggerSelector: '#my-hotspot'
 * });
 *
 * @example
 * // Advanced usage with language toggle
 * const modal = new Modal({
 *   modalSelector: '#my-modal',
 *   backdropSelector: '#modal-backdrop',
 *   triggerSelector: '#my-hotspot',
 *   languageToggle: {
 *     enabled: true,
 *     toggleSelector: '#lang-toggle',
 *     currentLangSelector: '#current-lang',
 *     altLangSelector: '#alt-lang',
 *     contentEnSelector: '#content-en',
 *     contentEsSelector: '#content-es'
 *   }
 * });
 */
class Modal {
    constructor(options = {}) {
      // Default configuration
      this.config = {
        modalSelector: options.modalSelector || '.modal',
        backdropSelector: options.backdropSelector || '.modal-backdrop',
        triggerSelector: options.triggerSelector || null,
        closeButtonSelector: options.closeButtonSelector || '.modal-close-btn',
        enableKeyboard: options.enableKeyboard !== false, // Default: true
        closeOnBackdropClick: options.closeOnBackdropClick !== false, // Default: true
        languageToggle: options.languageToggle || null,
        ...options,
      };
  
      // Get DOM elements
      this.modal = document.querySelector(this.config.modalSelector);
      this.backdrop = document.querySelector(this.config.backdropSelector);
      this.closeButton = this.modal?.querySelector(
        this.config.closeButtonSelector
      );
      // Also handle X close button if present
      this.xCloseButton = this.modal?.querySelector('.modal-close-x');
  
      // State management
      this.scrollPosition = 0;
      this.isAnimating = false;
  
      // Language toggle state (if enabled)
      this.isEnglish = true;
      if (this.config.languageToggle?.enabled) {
        this.initLanguageToggle();
      }
  
      // Initialize event listeners
      this.init();
    }
  
    /**
     * Initialize modal: set up event listeners
     */
    init() {
      if (!this.modal || !this.backdrop) {
        console.warn('Modal or backdrop element not found');
        return;
      }
  
      // Set up trigger button if specified
      if (this.config.triggerSelector) {
        const trigger = document.querySelector(this.config.triggerSelector);
        if (trigger) {
          this.setupTrigger(trigger);
        }
      }
  
      // Set up close button
      if (this.closeButton) {
        this.setupCloseButton(this.closeButton);
      }
  
      // Set up X close button
      if (this.xCloseButton) {
        this.setupCloseButton(this.xCloseButton);
      }
  
      // Set up backdrop click
      if (this.config.closeOnBackdropClick) {
        this.setupBackdrop();
      }
  
      // Set up keyboard (Escape key)
      if (this.config.enableKeyboard) {
        this.setupKeyboard();
      }
    }
  
    /**
     * Set up trigger button to open modal
     * @param {HTMLElement} trigger - Element that triggers modal opening
     */
    setupTrigger(trigger) {
      // Click event (mouse/trackpad)
      trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        this.open();
      });
  
      // Touch event (mobile)
      trigger.addEventListener(
        'touchstart',
        (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.open();
        },
        { passive: false }
      );
    }
  
    /**
     * Set up close button
     * @param {HTMLElement} button - Close button element
     */
    setupCloseButton(button) {
      // Click event
      button.addEventListener('click', (e) => {
        e.stopPropagation();
        this.close();
      });
  
      // Touch event
      button.addEventListener(
        'touchstart',
        (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.close();
        },
        { passive: false }
      );
    }
  
    /**
     * Set up backdrop click to close modal
     */
    setupBackdrop() {
      // Click event
      this.backdrop.addEventListener('click', () => {
        this.close();
      });
  
      // Touch event
      this.backdrop.addEventListener(
        'touchstart',
        (e) => {
          if (e.target === this.backdrop) {
            e.preventDefault();
            this.close();
          }
        },
        { passive: false }
      );
    }
  
    /**
     * Set up keyboard accessibility (Escape key)
     */
    setupKeyboard() {
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.modal.style.display === 'block') {
          this.close();
        }
      });
    }
  
    /**
     * Initialize language toggle functionality
     */
    initLanguageToggle() {
      const langConfig = this.config.languageToggle;
  
      this.langToggle = document.querySelector(langConfig.toggleSelector);
      this.contentEn = document.querySelector(langConfig.contentEnSelector);
      this.contentEs = document.querySelector(langConfig.contentEsSelector);
      this.currentLang = document.querySelector(langConfig.currentLangSelector);
      this.altLang = document.querySelector(langConfig.altLangSelector);
  
      if (this.langToggle) {
        this.langToggle.addEventListener('click', (e) => {
          e.stopPropagation();
          this.toggleLanguage();
        });
  
        this.langToggle.addEventListener(
          'touchstart',
          (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.toggleLanguage();
          },
          { passive: false }
        );
      }
    }
  
    /**
     * Opens the modal with smooth animation
     */
    open() {
      if (this.isAnimating) return;
  
      // Store current scroll position
      this.scrollPosition =
        window.pageYOffset || document.documentElement.scrollTop;
  
      // Lock body scroll
      document.body.style.overflow = 'hidden';
      document.body.style.position = 'fixed';
      document.body.style.top = `-${this.scrollPosition}px`;
      document.body.style.width = '100%';
  
      // Show modal and backdrop
      this.modal.style.display = 'block';
      this.backdrop.style.display = 'block';
  
      // Force reflow
      void this.modal.offsetHeight;
      void this.backdrop.offsetHeight;
  
      // Remove closing classes
      this.modal.classList.remove('modal-closing');
      this.backdrop.classList.remove('backdrop-closing');
  
      // Trigger opening animation
      requestAnimationFrame(() => {
        this.modal.classList.add('modal-open');
        this.backdrop.classList.add('backdrop-open');
        this.isAnimating = true;
  
        setTimeout(() => {
          this.isAnimating = false;
        }, 300);
      });
    }
  
    /**
     * Closes the modal with smooth animation
     */
    close() {
      if (this.isAnimating) return;
      this.isAnimating = true;
  
      // Remove opening classes
      this.modal.classList.remove('modal-open');
      this.backdrop.classList.remove('backdrop-open');
  
      // Force reflow
      void this.modal.offsetHeight;
  
      // Trigger closing animation
      requestAnimationFrame(() => {
        this.modal.classList.add('modal-closing');
        this.backdrop.classList.add('backdrop-closing');
      });
  
      // Wait for animation to complete
      setTimeout(() => {
        this.modal.style.display = 'none';
        this.backdrop.style.display = 'none';
  
        this.modal.classList.remove('modal-closing');
        this.backdrop.classList.remove('backdrop-closing');
  
        // Restore body scroll
        document.body.style.overflow = '';
        document.body.style.position = '';
        document.body.style.top = '';
        document.body.style.width = '';
        window.scrollTo(0, this.scrollPosition);
  
        this.isAnimating = false;
      }, 300);
    }
  
    /**
     * Toggles between languages (if language toggle is enabled)
     */
    toggleLanguage() {
      if (!this.config.languageToggle?.enabled) return;
  
      const currentContent = this.isEnglish ? this.contentEn : this.contentEs;
      const nextContent = this.isEnglish ? this.contentEs : this.contentEn;
  
      if (!currentContent || !nextContent) return;
  
      // Update language state
      this.isEnglish = !this.isEnglish;
  
      // Update language toggle button text
      if (this.currentLang && this.altLang) {
        if (this.isEnglish) {
          this.currentLang.textContent = 'EN';
          this.altLang.textContent = 'ES';
        } else {
          this.currentLang.textContent = 'ES';
          this.altLang.textContent = 'EN';
        }
      }
  
      // Prepare next content for fade-in
      nextContent.classList.remove('hidden');
      nextContent.classList.add('fade-in');
      void nextContent.offsetHeight;
  
      // Start fade-out for current content
      currentContent.classList.remove('visible');
      currentContent.classList.add('fade-out');
  
      // After fade-out completes, swap content
      setTimeout(() => {
        currentContent.classList.remove('fade-out');
        currentContent.classList.add('hidden');
  
        nextContent.classList.remove('fade-in');
        nextContent.classList.add('visible');
  
        // Animate content elements
        setTimeout(() => {
          const h2 = nextContent.querySelector('h2');
          const p = nextContent.querySelector('p');
  
          if (h2) {
            h2.style.opacity = '0';
            h2.style.transform = 'translateY(10px)';
  
            requestAnimationFrame(() => {
              h2.style.transition =
                'opacity 0.3s ease-out 0.1s, transform 0.3s ease-out 0.1s';
              h2.style.opacity = '1';
              h2.style.transform = 'translateY(0)';
            });
          }
  
          if (p) {
            p.style.opacity = '0';
            p.style.transform = 'translateY(10px)';
  
            requestAnimationFrame(() => {
              p.style.transition =
                'opacity 0.3s ease-out 0.2s, transform 0.3s ease-out 0.2s';
              p.style.opacity = '1';
              p.style.transform = 'translateY(0)';
            });
          }
        }, 50);
      }, 200);
    }
  }
  
  // Export for use in other files (if using modules)
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = Modal;
  }
  