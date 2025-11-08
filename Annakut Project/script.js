// Handles loading the events for <model-viewer>'s slotted progress bar
const onProgress = (event) => {
    const progressBar = event.target.querySelector('.progress-bar');
    const updatingBar = event.target.querySelector('.update-bar');
    updatingBar.style.width = `${event.detail.totalProgress * 100}%`;
    if (event.detail.totalProgress === 1) {
      progressBar.classList.add('hide');
      event.target.removeEventListener('progress', onProgress);
    } else {
      progressBar.classList.remove('hide');
    }
  };
  
  const modelViewer = document.querySelector('model-viewer');
  if (modelViewer) {
    modelViewer.addEventListener('progress', onProgress);
  
    // Adjust camera to zoom in on model load
    modelViewer.addEventListener('load', () => {
      // Get current camera orbit and adjust distance (zoom in)
      const cameraOrbit = modelViewer.cameraOrbit;
      if (cameraOrbit) {
        // Set a closer distance (lower value = closer/more zoomed in)
        modelViewer.cameraOrbit = `${cameraOrbit.theta}deg ${cameraOrbit.phi}deg 8m`;
      }
    });
  }
  
  // Handle orientation lock for mobile devices
  function handleOrientation() {
    const orientationMessage = document.getElementById('orientation-message');
    const isMobile = window.innerWidth <= 767;
    const isPortrait = window.matchMedia('(orientation: portrait)').matches;
  
    if (orientationMessage) {
      if (isMobile && isPortrait) {
        orientationMessage.classList.add('show');
        document.body.style.overflow = 'hidden';
      } else {
        orientationMessage.classList.remove('show');
        document.body.style.overflow = '';
      }
    }
  }
  
  // Check orientation on load and orientation change
  window.addEventListener('load', handleOrientation);
  window.addEventListener('orientationchange', () => {
    // Delay to ensure orientation change is complete
    setTimeout(handleOrientation, 100);
  });
  window.addEventListener('resize', handleOrientation);
  
  // Handle overlay message close
  function handleOverlayMessage() {
    const overlayMessage = document.getElementById('overlay-message');
    const closeBtn = document.querySelector('.overlay-close');
  
    if (overlayMessage && closeBtn) {
      // Show overlay message on load
      overlayMessage.classList.add('show');
  
      // Close button functionality
      closeBtn.addEventListener('click', () => {
        overlayMessage.classList.remove('show');
      });
  
      closeBtn.addEventListener('touchstart', (e) => {
        e.preventDefault();
        overlayMessage.classList.remove('show');
      });
    }
  }
  
  // Default language - make globally accessible
  window.currentLanguage = 'en';
  
  // Load modal data from JSON file
  async function loadModalData() {
    try {
      const version = window.APP_VERSION || '1.0.0';
      const response = await fetch(`./modal-data.json?v=${version}`);
      if (!response.ok) {
        throw new Error(`Failed to load modal data: ${response.statusText}`);
      }
      const data = await response.json();
      window.modalData = data;
      return data;
    } catch (error) {
      console.error('Error loading modal data:', error);
      return null;
    }
  }
  
  // Language switching function
  function setLanguage(lang) {
    window.currentLanguage = lang;
    updateModalContent();
  }
  window.setLanguage = setLanguage;
  
  // Update toggle button active state
  function updateToggleActiveState(toggleElement, lang) {
    if (!toggleElement) return;
  
    const enSpan = toggleElement.querySelector('.lang-en');
    const guSpan = toggleElement.querySelector('.lang-gu');
  
    if (lang === 'en') {
      enSpan.classList.add('active');
      guSpan.classList.remove('active');
    } else {
      enSpan.classList.remove('active');
      guSpan.classList.add('active');
    }
  
    toggleElement.setAttribute('data-lang', lang);
  }
  
  // Update single modal content
  function updateSingleModalContent(hotspotId, lang) {
    const modal = document.getElementById(`modal-${hotspotId}`);
    if (!modal || !window.modalData) return;
  
    const data = window.modalData[hotspotId];
    if (!data) return;
  
    // Update image alt
    const imageElement = modal.querySelector('img');
    if (imageElement && data.imageAlt && data.imageAlt[lang]) {
      imageElement.alt = data.imageAlt[lang];
    }
  
    // Update content
    const contentElement = modal.querySelector('.modal-text');
    if (contentElement && data.content && data.content[lang]) {
      contentElement.textContent = data.content[lang];
      // Add language class for font styling
      contentElement.className = 'modal-text';
      if (lang === 'gu') {
        contentElement.classList.add('gujarati-text');
      } else {
        contentElement.classList.remove('gujarati-text');
      }
    }
  }
  
  // Get sorted hotspot IDs in numerical order (hotspot-1, hotspot-2, ..., hotspot-10)
  function getSortedHotspotIds() {
    if (!window.modalData) return [];
    const hotspotIds = Object.keys(window.modalData);
    // Sort numerically: extract the number after "hotspot-" and sort by that
    return hotspotIds.sort((a, b) => {
      const numA = parseInt(a.replace('hotspot-', ''), 10);
      const numB = parseInt(b.replace('hotspot-', ''), 10);
      return numA - numB;
    });
  }
  
  // Update currently open modal to show different hotspot content
  function updateModalContentTo(newHotspotId) {
    if (!window.modalData || !window.modalData[newHotspotId]) return;
  
    // Find the currently open modal
    const openModal = document.querySelector('.modal.modal-open');
    if (!openModal) return;
  
    const newData = window.modalData[newHotspotId];
    const currentLang = window.currentLanguage || 'en';
    const hotspotIds = getSortedHotspotIds();
    const newIndex = hotspotIds.indexOf(newHotspotId);
  
    // Safety check: if hotspot not found in sorted list, return
    if (newIndex === -1) return;
  
    const hasPrevious = newIndex > 0;
    const hasNext = newIndex < hotspotIds.length - 1;
  
    // Update title
    const titleElement = openModal.querySelector('.modal-title');
    if (titleElement) {
      titleElement.textContent = newData.title || '';
    }
  
    // Update subtitle
    const subtitleElement = openModal.querySelector('.modal-subtitle');
    const titleHeader = openModal.querySelector('.modal-title-header');
  
    if (newData.subtitle) {
      if (!subtitleElement) {
        // Create subtitle if it doesn't exist
        const subtitle = document.createElement('h3');
        subtitle.className = 'modal-subtitle';
        subtitle.textContent = newData.subtitle;
  
        // Insert after title header
        if (titleHeader && titleHeader.parentNode) {
          titleHeader.parentNode.insertBefore(subtitle, titleHeader.nextSibling);
        }
      } else {
        subtitleElement.textContent = newData.subtitle;
      }
    } else {
      // Remove subtitle if it exists but new data doesn't have one
      if (subtitleElement) {
        subtitleElement.remove();
      }
    }
  
    // Update image
    const imageElement = openModal.querySelector('.modal-image');
    if (imageElement) {
      imageElement.src = newData.image;
      imageElement.alt =
        newData.imageAlt?.[currentLang] || newData.imageAlt?.en || '';
    }
  
    // Update text content
    const textElement = openModal.querySelector('.modal-text');
    if (textElement) {
      textElement.textContent =
        newData.content?.[currentLang] || newData.content?.en || '';
      textElement.className = 'modal-text';
      if (currentLang === 'gu') {
        textElement.classList.add('gujarati-text');
      }
    }
  
    // Update navigation buttons state
    const prevButton = openModal.querySelector('.modal-nav-prev');
    const nextButton = openModal.querySelector('.modal-nav-next');
  
    if (prevButton) {
      // Remove all existing event listeners by cloning the button
      const prevButtonClone = prevButton.cloneNode(true);
      prevButton.parentNode.replaceChild(prevButtonClone, prevButton);
      const newPrevButton = prevButtonClone;
  
      if (hasPrevious) {
        newPrevButton.disabled = false;
        newPrevButton.style.opacity = '1';
        newPrevButton.style.cursor = 'pointer';
        // Set new click handler for previous button
        newPrevButton.addEventListener('click', () => {
          const prevHotspotId = hotspotIds[newIndex - 1];
          updateModalContentTo(prevHotspotId);
        });
      } else {
        newPrevButton.disabled = true;
        newPrevButton.style.opacity = '0.5';
        newPrevButton.style.cursor = 'not-allowed';
      }
    }
  
    if (nextButton) {
      // Remove all existing event listeners by cloning the button
      const nextButtonClone = nextButton.cloneNode(true);
      nextButton.parentNode.replaceChild(nextButtonClone, nextButton);
      const newNextButton = nextButtonClone;
  
      if (hasNext) {
        newNextButton.disabled = false;
        newNextButton.style.opacity = '1';
        newNextButton.style.cursor = 'pointer';
        // Set new click handler for next button
        newNextButton.addEventListener('click', () => {
          const nextHotspotId = hotspotIds[newIndex + 1];
          updateModalContentTo(nextHotspotId);
        });
      } else {
        newNextButton.disabled = true;
        newNextButton.style.opacity = '0.5';
        newNextButton.style.cursor = 'not-allowed';
      }
    }
  
    // Update modal ID to match new hotspot
    openModal.id = `modal-${newHotspotId}`;
  
    // Scroll to top of modal content
    const modalContent = openModal.querySelector('.modal-content');
    if (modalContent) {
      modalContent.scrollTop = 0;
    }
  }
  
  // Update all modal content based on current language
  function updateModalContent() {
    const currentLanguage = window.currentLanguage || 'en';
    if (!window.modalData) return;
  
    // Update font styling for all modals
    document.querySelectorAll('.modal-text').forEach((textElement) => {
      if (currentLanguage === 'gu') {
        textElement.classList.add('gujarati-text');
      } else {
        textElement.classList.remove('gujarati-text');
      }
    });
  
    Object.keys(window.modalData).forEach((hotspotId) => {
      updateSingleModalContent(hotspotId, currentLanguage);
  
      // Update toggle button active state
      const modal = document.getElementById(`modal-${hotspotId}`);
      if (modal) {
        const langToggle = modal.querySelector('.modal-lang-toggle');
        if (langToggle) {
          updateToggleActiveState(langToggle, currentLanguage);
        }
      }
    });
  }
  window.updateModalContent = updateModalContent;
  
  // Create modals dynamically from modal-data.json
  function createModalsFromData() {
    const modalBackdrop = document.querySelector('.modal-backdrop');
  
    if (!modalBackdrop || !window.modalData) {
      console.error('Modal backdrop or modal data not found');
      return;
    }
  
    // Create modal elements from data
    Object.keys(window.modalData).forEach((hotspotId) => {
      const data = window.modalData[hotspotId];
      const hotspotNumber = hotspotId.replace('hotspot-', '');
  
      // Create modal element
      const modal = document.createElement('div');
      modal.className = 'modal';
      modal.id = `modal-${hotspotId}`;
  
      // Create modal content
      const modalContent = document.createElement('div');
      modalContent.className = 'modal-content';
  
      // Create title header with X close button
      const titleHeader = document.createElement('div');
      titleHeader.className = 'modal-title-header';
  
      const title = document.createElement('h2');
      title.className = 'modal-title';
      title.textContent = data.title || '';
  
      // Create X close button
      const xCloseBtn = document.createElement('button');
      xCloseBtn.className = 'modal-close-x';
      xCloseBtn.setAttribute('aria-label', 'Close modal');
  
      titleHeader.appendChild(title);
      titleHeader.appendChild(xCloseBtn);
  
      // Create subtitle (if available)
      let subtitle = null;
      if (data.subtitle) {
        subtitle = document.createElement('h3');
        subtitle.className = 'modal-subtitle';
        subtitle.textContent = data.subtitle;
      }
  
      // Create language toggle button (pill-shaped with both languages)
      const langToggle = document.createElement('button');
      langToggle.className = 'modal-lang-toggle';
      langToggle.setAttribute('aria-label', 'Switch language');
      langToggle.setAttribute('data-lang', window.currentLanguage || 'en');
  
      // Create EN span
      const enSpan = document.createElement('span');
      enSpan.className = 'lang-option lang-en';
      enSpan.textContent = 'English';
  
      // Create pipe separator
      const arrowSpan = document.createElement('span');
      arrowSpan.className = 'lang-arrow';
      arrowSpan.textContent = '|';
  
      // Create Gujarati span
      const guSpan = document.createElement('span');
      guSpan.className = 'lang-option lang-gu';
      guSpan.textContent = 'ગુજરાતી';
  
      // Append to toggle button
      langToggle.appendChild(enSpan);
      langToggle.appendChild(arrowSpan);
      langToggle.appendChild(guSpan);
  
      // Update active state
      updateToggleActiveState(langToggle, window.currentLanguage || 'en');
  
      // Add click and touch handlers for language toggle
      const handleLanguageToggle = (e) => {
        e.preventDefault();
        e.stopPropagation();
  
        const currentLang = window.currentLanguage || 'en';
        const newLang = currentLang === 'en' ? 'gu' : 'en';
        window.currentLanguage = newLang;
  
        // Update the currently open modal's content
        // Get the currently displayed hotspot ID from modal ID
        const openModal = document.querySelector('.modal.modal-open');
        if (openModal) {
          const currentHotspotId = openModal.id.replace('modal-', '');
          const data = window.modalData && window.modalData[currentHotspotId];
  
          if (data) {
            // Update image alt
            const imageElement = openModal.querySelector('.modal-image');
            if (imageElement) {
              imageElement.alt =
                data.imageAlt?.[newLang] || data.imageAlt?.en || '';
            }
  
            // Update text content
            const textElement = openModal.querySelector('.modal-text');
            if (textElement && data.content) {
              textElement.textContent =
                data.content[newLang] || data.content.en || '';
              textElement.className = 'modal-text';
              if (newLang === 'gu') {
                textElement.classList.add('gujarati-text');
              } else {
                textElement.classList.remove('gujarati-text');
              }
            }
          }
        } else {
          // Fallback to original hotspot ID if modal not found
          updateSingleModalContent(hotspotId, newLang);
        }
  
        // Update toggle button active state for all toggles
        const openModalForUpdate = document.querySelector('.modal.modal-open');
        if (openModalForUpdate) {
          const allLangToggles =
            openModalForUpdate.querySelectorAll('.modal-lang-toggle');
          allLangToggles.forEach((toggle) => {
            updateToggleActiveState(toggle, newLang);
          });
        } else {
          updateToggleActiveState(langToggle, newLang);
        }
      };
  
      langToggle.addEventListener('click', handleLanguageToggle);
      langToggle.addEventListener('touchstart', handleLanguageToggle, {
        passive: false,
      });
  
      // Create image
      const image = document.createElement('img');
      image.src = data.image;
      image.alt =
        data.imageAlt[window.currentLanguage || 'en'] || data.imageAlt.en || '';
      image.className = 'modal-image';
  
      // Create text content
      const text = document.createElement('p');
      const currentLang = window.currentLanguage || 'en';
      text.className = 'modal-text';
      if (currentLang === 'gu') {
        text.classList.add('gujarati-text');
      }
      text.textContent = data.content[currentLang] || data.content.en;
  
      // Append to modal content
      modalContent.appendChild(titleHeader);
      if (subtitle) {
        modalContent.appendChild(subtitle);
      }
      modalContent.appendChild(image);
      modalContent.appendChild(langToggle); // Language pill above text content
      modalContent.appendChild(text);
  
      // Create navigation buttons container
      const navContainer = document.createElement('div');
      navContainer.className = 'modal-navigation';
  
      // Get hotspot IDs in sorted numerical order
      const hotspotIds = getSortedHotspotIds();
      const currentIndex = hotspotIds.indexOf(hotspotId);
  
      // Safety check: if hotspot not found in sorted list, disable navigation
      const hasPrevious = currentIndex > 0 && currentIndex !== -1;
      const hasNext = currentIndex < hotspotIds.length - 1 && currentIndex !== -1;
  
      // Create Previous button
      const prevButton = document.createElement('button');
      prevButton.className = 'modal-nav-btn modal-nav-prev';
      prevButton.setAttribute('aria-label', 'Previous content');
      prevButton.innerHTML = '← Previous';
  
      if (hasPrevious) {
        const prevHotspotId = hotspotIds[currentIndex - 1];
        prevButton.addEventListener('click', () => {
          updateModalContentTo(prevHotspotId);
        });
      } else {
        prevButton.disabled = true;
        prevButton.style.opacity = '0.5';
        prevButton.style.cursor = 'not-allowed';
      }
  
      // Create Next button
      const nextButton = document.createElement('button');
      nextButton.className = 'modal-nav-btn modal-nav-next';
      nextButton.setAttribute('aria-label', 'Next content');
      nextButton.innerHTML = 'Next →';
  
      if (hasNext) {
        const nextHotspotId = hotspotIds[currentIndex + 1];
        nextButton.addEventListener('click', () => {
          updateModalContentTo(nextHotspotId);
        });
      } else {
        nextButton.disabled = true;
        nextButton.style.opacity = '0.5';
        nextButton.style.cursor = 'not-allowed';
      }
  
      // Append buttons to navigation container
      navContainer.appendChild(prevButton);
      navContainer.appendChild(nextButton);
  
      // Append navigation container to modal content
      modalContent.appendChild(navContainer);
  
      // Append to modal
      modal.appendChild(modalContent);
  
      // Insert modal after backdrop
      modalBackdrop.after(modal);
    });
  }
  
  // Initialize modals for each hotspot button - automatically detects all hotspots
  document.addEventListener('DOMContentLoaded', async () => {
    // Check orientation on DOM ready
    handleOrientation();
  
    // Initialize overlay message
    handleOverlayMessage();
  
    // Load modal data from JSON file
    await loadModalData();
  
    // Create modals from data file
    createModalsFromData();
  
    // Wait a bit for modals to be created, then initialize
    setTimeout(() => {
      // Automatically find and initialize all hotspots
      const allHotspotButtons = document.querySelectorAll(
        'button[slot^="hotspot-"]'
      );
  
      allHotspotButtons.forEach((hotspotButton) => {
        const slotName = hotspotButton.getAttribute('slot');
        const modalSelector = `#modal-${slotName}`;
        const modalElement = document.querySelector(modalSelector);
  
        // Only initialize if corresponding modal exists
        if (modalElement) {
          new Modal({
            modalSelector: modalSelector,
            backdropSelector: '.modal-backdrop',
            triggerSelector: `button[slot="${slotName}"]`,
          });
        } else {
          console.warn(
            `Modal not found for ${slotName}. Expected: ${modalSelector}`
          );
        }
      });
  
      // Initial content update
      if (window.updateModalContent) {
        updateModalContent();
      }
  
      // Add numbering to hotspots
      addHotspotNumbers();
    }, 100);
  });
  
  // Add maroon colored numbers to each hotspot
  function addHotspotNumbers() {
    const hotspotButtons = document.querySelectorAll(
      'button.Hotspot[slot^="hotspot-"]'
    );
  
    hotspotButtons.forEach((hotspot) => {
      const slot = hotspot.getAttribute('slot');
      // Extract number from slot (e.g., "hotspot-1" -> "1")
      const number = slot.replace('hotspot-', '');
  
      // Check if number already exists (avoid duplicates)
      if (hotspot.querySelector('.hotspot-number')) {
        return;
      }
  
      // Create number span
      const numberSpan = document.createElement('span');
      numberSpan.className = 'hotspot-number';
      numberSpan.textContent = number;
  
      // Insert number as first child of hotspot
      hotspot.insertBefore(numberSpan, hotspot.firstChild);
    });
  }
  