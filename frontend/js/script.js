// API Base URL - adjust this to match your backend
const API_BASE_URL = 'http://localhost:8025';

// ── Toast notifications ───────────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 3500) {
    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span class="toast-icon">${icons[type]}</span><span class="toast-msg">${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('toast-out');
        setTimeout(() => toast.remove(), 280);
    }, duration);
}

// Global variables
let selectedTheme = '';
let currentStory = null;
let allStories = []; // store for search/filter
let selectedGender = 'boy';
let selectedLength = 'medium';
let currentThemeFilter = 'all';

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Kids Story Generator - Frontend Loaded');
    
    // Always redirect to home page on load/reload
    window.history.replaceState(null, '', window.location.pathname);
    
    // Hide all sections except home initially
    showSection('home');
    
    // Set up form submission
    const storyForm = document.getElementById('storyForm');
    if (storyForm) {
        storyForm.addEventListener('submit', handleStoryGeneration);
        console.log('✅ Story form event listener added');
    } else {
        console.error('❌ Story form not found');
    }
    
    // Load recent stories
    loadRecentStories();
    
    // Load gallery stats
    loadGalleryStats();
    computeStreak();
    
    // Set up navigation
    setupNavigation();
    
    // Test API connection
    testAPIConnection();
    
    // Test owl immediately on page load
    setTimeout(() => {
        console.log('🦉 Testing owl on page load...');
        showCharacterMessage("🦉 Hello! I'm your story helper owl. Welcome to Kids Story Generator!");
        
        setTimeout(() => {
            hideCharacterMessage();
        }, 5000);
    }, 2000);
});

// Test API connection
async function testAPIConnection() {
    try {
        console.log('🔌 Testing API connection to:', API_BASE_URL);
        const response = await fetch(`${API_BASE_URL}/api`);
        console.log('📡 Response status:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('✅ API connection successful:', data);
            setOnlineMode(true);
        } else {
            console.error('❌ API connection failed:', response.status, response.statusText);
            setOnlineMode(false);
        }
    } catch (error) {
        console.error('❌ API connection error:', error);
        setOnlineMode(false);
    }
}

// Track online/offline state
window.isOffline = false;

function setOnlineMode(online) {
    window.isOffline = !online;

    // Remove existing banner if any
    const existing = document.getElementById('offlineBanner');
    if (existing) existing.remove();

    if (!online) {
        // Show offline banner
        const banner = document.createElement('div');
        banner.id = 'offlineBanner';
        banner.innerHTML = `
            <span>📴 Offline mode — You can browse and read saved stories. New story creation is disabled.</span>
        `;
        Object.assign(banner.style, {
            position: 'fixed', bottom: '0', left: '0', right: '0',
            background: '#1e293b', color: '#f1f5f9',
            padding: '12px 24px', textAlign: 'center',
            fontSize: '0.9rem', fontFamily: "'Nunito', sans-serif",
            zIndex: '9999', borderTop: '3px solid #f59e0b',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px'
        });
        document.body.appendChild(banner);

        // Disable the create form submit button
        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = '📴 Offline — Cannot Create';
            submitBtn.style.background = '#64748b';
            submitBtn.style.cursor = 'not-allowed';
        }

        // Show offline notice on create section
        const createSection = document.getElementById('create');
        if (createSection) {
            let notice = document.getElementById('offlineCreateNotice');
            if (!notice) {
                notice = document.createElement('div');
                notice.id = 'offlineCreateNotice';
                notice.innerHTML = `
                    <div style="text-align:center; padding: 20px; background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.4); border-radius: 12px; margin-bottom: 20px; color: #fef3c7; font-family: 'Nunito', sans-serif;">
                        📴 <strong>You're offline.</strong> Story creation needs an internet connection.<br>
                        <span style="font-size:0.85rem; opacity:0.8;">You can still read all your saved stories from the Gallery.</span>
                    </div>
                `;
                createSection.insertBefore(notice, createSection.firstChild);
            }
        }

        console.log('📴 App running in offline/read-only mode');
    } else {
        // Remove offline notice from create section if it exists
        const notice = document.getElementById('offlineCreateNotice');
        if (notice) notice.remove();

        // Re-enable submit button
        validateProfessionalForm();
        console.log('🌐 App running in online mode');
    }
}

// Navigation setup
function setupNavigation() {
    const navLinks = document.querySelectorAll('nav a[href^="#"]');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const sectionId = link.getAttribute('href').substring(1);
            showSection(sectionId);
        });
    });
    
    const getStartedBtn = document.getElementById('getStartedBtn');
    if (getStartedBtn) {
        getStartedBtn.addEventListener('click', () => showSection('create'));
    }
}

// Show specific section
function showSection(sectionId) {
    console.log('🔄 showSection called with:', sectionId);
    
    // Hide all sections
    const sections = ['home', 'create', 'gallery', 'favorites', 'register', 'login', 'storyView', 'about'];
    sections.forEach(id => {
        const section = document.getElementById(id);
        if (section) {
            section.classList.add('section-hidden');
            console.log('  ➖ Hiding section:', id);
        }
    });
    
    // Show the requested section
    const targetSection = document.getElementById(sectionId);
    if (targetSection) {
        targetSection.classList.remove('section-hidden');
        targetSection.classList.remove('section-fade');
        void targetSection.offsetWidth; // force reflow
        targetSection.classList.add('section-fade');
        console.log('  ✅ Showing section:', sectionId);
        
        // Scroll to top of the section
        targetSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
        console.error('  ❌ Section not found:', sectionId);
    }
    
    // Update navigation active state
    const navLinks = document.querySelectorAll('nav a');
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === `#${sectionId}`) {
            link.classList.add('active');
        }
    });
}

// Theme selection
function selectTheme(element) {
    console.log('🎨 Theme selected:', element.dataset.theme);
    
    // Remove selected class from all themes
    document.querySelectorAll('.theme-option').forEach(option => {
        option.classList.remove('selected');
    });
    
    // Add selected class to clicked theme
    element.classList.add('selected');
    selectedTheme = element.dataset.theme;
    
    console.log('✅ Selected theme:', selectedTheme);
    
    // Show owl encouragement for theme selection
    const themeMessages = {
        'adventure': "🗺️ Adventure theme! Get ready for exciting journeys and brave heroes!",
        'fantasy': "🧙‍♀️ Fantasy theme! Magic, dragons, and enchanted worlds await!",
        'friendship': "👫 Friendship theme! Stories about kindness and caring friends!",
        'animals': "🐾 Animal theme! Cute creatures and furry friends will star in your story!",
        'space': "🚀 Space theme! Blast off to the stars and explore the galaxy!",
        'ocean': "🌊 Ocean theme! Dive deep into underwater adventures with sea creatures and mermaids!",
        'custom': "✨ Custom theme! Your imagination is the limit - let's create something unique!"
    };
    
    if (themeMessages[selectedTheme]) {
        showCharacterMessage(themeMessages[selectedTheme]);
        setTimeout(() => {
            hideCharacterMessage();
        }, 3000);
    }
    
    // Show/hide custom theme input
    const customThemeGroup = document.getElementById('customThemeGroup');
    if (selectedTheme === 'custom') {
        customThemeGroup.classList.remove('hidden');
        console.log('📝 Custom theme input shown');
    } else {
        customThemeGroup.classList.add('hidden');
    }
}

// New theme selection function with animations
function selectThemeNew(element) {
    // Remove active state from all themes
    document.querySelectorAll('.theme-option-new').forEach(opt => {
        opt.style.borderColor = 'transparent';
        opt.style.transform = 'scale(1)';
        opt.style.boxShadow = 'none';
    });
    
    // Add active state to selected theme
    element.style.borderColor = 'white';
    element.style.transform = 'scale(1.05)';
    element.style.boxShadow = '0 8px 25px rgba(0,0,0,0.3)';
    
    selectedTheme = element.dataset.theme;
    updateProgress();
    
    // Show owl encouragement
    const themeMessages = {
        'adventure': "🗺️ Adventure theme! Get ready for exciting journeys!",
        'fantasy': "🧙‍♀️ Fantasy theme! Magic and enchanted worlds await!",
        'friendship': "👫 Friendship theme! Stories about kindness!",
        'animals': "🐾 Animal theme! Cute creatures will star in your story!",
        'space': "🚀 Space theme! Blast off to the stars!",
        'ocean': "🌊 Ocean theme! Dive into underwater adventures!"
    };
    
    if (themeMessages[selectedTheme]) {
        showCharacterMessage(themeMessages[selectedTheme]);
        setTimeout(() => hideCharacterMessage(), 2500);
    }
    
    console.log('Selected theme:', selectedTheme);
}

// Update progress bar
function updateProgress() {
    const name = document.getElementById('characterName').value;
    const age = document.getElementById('characterAge').value;
    const hasTheme = selectedTheme !== null;
    
    let progress = 0;
    if (name) progress += 33;
    if (age) progress += 33;
    if (hasTheme) progress += 34;
    
    const progressBar = document.getElementById('progressBar');
    const progressPercent = document.getElementById('progressPercent');
    
    if (progressBar && progressPercent) {
        progressBar.style.width = progress + '%';
        progressPercent.textContent = progress + '%';
    }
    
    // Update name preview
    const namePreview = document.getElementById('namePreview');
    if (namePreview) {
        if (name) {
            namePreview.textContent = `✨ Your hero: ${name}`;
        } else {
            namePreview.textContent = '';
        }
    }
}

// Get age emoji based on age value
function getAgeEmoji(age) {
    age = parseInt(age);
    if (age <= 3) return '👶';
    if (age <= 6) return '🧒';
    if (age <= 9) return '👦';
    if (age <= 12) return '🧑';
    return '👨';
}

// Professional form functions
let selectedAge = null;
let professionalSelectedTheme = null;

// Select age button
function selectAge(age) {
    selectedAge = age;
    document.getElementById('characterAge').value = age;
    
    // Update UI
    document.querySelectorAll('.age-btn').forEach(btn => {
        btn.classList.remove('selected');
        btn.style.borderColor = 'rgba(167,139,250,0.4)';
        btn.style.background = 'rgba(118,75,162,0.25)';
        btn.style.color = '#ffffff';
        btn.style.boxShadow = 'none';
        btn.style.transform = 'scale(1)';
    });
    
    const selectedBtn = document.querySelector(`.age-btn[data-age="${age}"]`);
    if (selectedBtn) {
        selectedBtn.classList.add('selected');
        selectedBtn.style.borderColor = '#a78bfa';
        selectedBtn.style.background = 'rgba(167,139,250,0.5)';
        selectedBtn.style.color = '#ffffff';
        selectedBtn.style.boxShadow = '0 4px 12px rgba(167,139,250,0.6)';
        selectedBtn.style.transform = 'scale(1.05)';
    }
    
    validateProfessionalForm();
}

// Select theme card
function selectTheme(element) {
    professionalSelectedTheme = element.dataset.theme;
    selectedTheme = professionalSelectedTheme; // Keep compatibility with existing code
    
    // Update UI
    document.querySelectorAll('.theme-card').forEach(card => {
        card.classList.remove('selected');
        card.style.borderColor = 'rgba(167,139,250,0.4)';
        card.style.background = 'rgba(118,75,162,0.25)';
        card.style.boxShadow = 'none';
        card.style.transform = 'translateY(0)';
    });
    
    element.classList.add('selected');
    element.style.borderColor = '#a78bfa';
    element.style.background = 'rgba(167,139,250,0.5)';
    element.style.boxShadow = '0 8px 24px rgba(167,139,250,0.6)';
    element.style.transform = 'translateY(-4px)';
    
    // Show owl encouragement for theme selection
    const themeMessages = {
        'adventure': "🗺️ Adventure theme! Get ready for exciting journeys and brave heroes!",
        'fantasy': "🧙‍♀️ Fantasy theme! Magic, dragons, and enchanted worlds await!",
        'friendship': "👫 Friendship theme! Stories about kindness and caring friends!",
        'animals': "🐾 Animal theme! Cute creatures and furry friends will star in your story!",
        'space': "🚀 Space theme! Blast off to the stars and explore the galaxy!",
        'ocean': "🌊 Ocean theme! Dive deep into underwater adventures!",
        'custom': "✨ Custom theme! Your imagination is the limit - let's create something unique!"
    };
    
    if (themeMessages[professionalSelectedTheme]) {
        showCharacterMessage(themeMessages[professionalSelectedTheme]);
        setTimeout(() => {
            hideCharacterMessage();
        }, 3000);
    }
    
    // Show/hide custom theme input
    const customThemeInput = document.getElementById('customThemeInput');
    if (professionalSelectedTheme === 'custom') {
        if (customThemeInput) {
            customThemeInput.style.display = 'block';
        }
    } else {
        if (customThemeInput) {
            customThemeInput.style.display = 'none';
        }
    }

    // Always show extra details box once a theme is picked
    const storyDetailsInput = document.getElementById('storyDetailsInput');
    if (storyDetailsInput) {
        storyDetailsInput.style.display = 'block';
    }
    
    validateProfessionalForm();
}

// Validate professional form
function validateProfessionalForm() {
    const name = document.getElementById('characterName').value.trim();
    const submitBtn = document.getElementById('submitBtn');

    let themeValid = false;
    if (professionalSelectedTheme === 'custom') {
        const customTheme = document.getElementById('customTheme');
        themeValid = customTheme && customTheme.value.trim() !== '';
    } else {
        themeValid = professionalSelectedTheme !== null;
    }

    const isValid = name && selectedAge && themeValid;

    if (submitBtn) {
        // Keep visual disabled state but never set disabled=true so clicks still register
        submitBtn.style.background = isValid
            ? 'linear-gradient(135deg, #8b6eea 0%, #9d5fb8 100%)'
            : '#cbd5e1';
        submitBtn.style.cursor = isValid ? 'pointer' : 'not-allowed';
        submitBtn.style.opacity = isValid ? '1' : '0.7';
        submitBtn.dataset.valid = isValid ? 'true' : 'false';
    }
}

// Add input listener for character name
document.addEventListener('DOMContentLoaded', function() {
    const characterNameInput = document.getElementById('characterName');
    if (characterNameInput) {
        characterNameInput.addEventListener('input', validateProfessionalForm);
        
        // Add focus/blur effects
        characterNameInput.addEventListener('focus', function() {
            this.style.borderColor = '#a78bfa';
            this.style.boxShadow = '0 0 0 3px rgba(167,139,250,0.3)';
            this.style.transform = 'translateY(-1px)';
        });
        
        characterNameInput.addEventListener('blur', function() {
            this.style.borderColor = 'rgba(167,139,250,0.4)';
            this.style.boxShadow = 'none';
            this.style.transform = 'translateY(0)';
        });
    }
    
    // Add input listener for custom theme
    const customThemeInput = document.getElementById('customTheme');
    if (customThemeInput) {
        customThemeInput.addEventListener('input', validateProfessionalForm);
        
        // Add focus/blur effects
        customThemeInput.addEventListener('focus', function() {
            this.style.borderColor = '#a78bfa';
            this.style.boxShadow = '0 0 0 3px rgba(167,139,250,0.3)';
            this.style.transform = 'translateY(-1px)';
        });
        
        customThemeInput.addEventListener('blur', function() {
            this.style.borderColor = 'rgba(167,139,250,0.4)';
            this.style.boxShadow = 'none';
            this.style.transform = 'translateY(0)';
        });
    }

    // Focus/blur effects for story details textarea
    const storyDetailsEl = document.getElementById('storyDetails');
    if (storyDetailsEl) {
        storyDetailsEl.addEventListener('focus', function() {
            this.style.borderColor = '#a78bfa';
            this.style.boxShadow = '0 0 0 3px rgba(167,139,250,0.3)';
        });
        storyDetailsEl.addEventListener('blur', function() {
            this.style.borderColor = 'rgba(167,139,250,0.4)';
            this.style.boxShadow = 'none';
        });
        // typing in extra details should never affect button state
        storyDetailsEl.addEventListener('input', validateProfessionalForm);
    }
    
    // Add hover effects to age buttons
    document.querySelectorAll('.age-btn').forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            if (!this.classList.contains('selected')) {
                this.style.borderColor = 'rgba(167,139,250,0.6)';
                this.style.background = 'rgba(118,75,162,0.35)';
                this.style.transform = 'translateY(-2px)';
            }
        });
        
        btn.addEventListener('mouseleave', function() {
            if (!this.classList.contains('selected')) {
                this.style.borderColor = 'rgba(167,139,250,0.4)';
                this.style.background = 'rgba(118,75,162,0.25)';
                this.style.transform = 'translateY(0)';
            }
        });
    });
    
    // Add hover effects to theme cards
    document.querySelectorAll('.theme-card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            if (!this.classList.contains('selected')) {
                this.style.borderColor = 'rgba(167,139,250,0.6)';
                this.style.transform = 'translateY(-4px) scale(1.02)';
                this.style.boxShadow = '0 8px 20px rgba(0,0,0,0.3)';
            }
            
            const icon = this.querySelector('span');
            if (icon) {
                icon.style.transform = 'scale(1.2) rotate(5deg)';
            }
        });
        
        card.addEventListener('mouseleave', function() {
            if (!this.classList.contains('selected')) {
                this.style.borderColor = 'rgba(167,139,250,0.4)';
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = 'none';
            }
            
            const icon = this.querySelector('span');
            if (icon) {
                icon.style.transform = 'scale(1) rotate(0deg)';
            }
        });
    });
    
    // Add hover effect to submit button
    const submitBtn = document.getElementById('submitBtn');
    if (submitBtn) {
        submitBtn.addEventListener('mouseenter', function() {
            if (!this.disabled) {
                this.style.background = 'linear-gradient(135deg, #7c5dd9 0%, #8e4fa7 100%)';
                this.style.boxShadow = '0 6px 20px rgba(139,110,234,0.6)';
                this.style.transform = 'translateY(-2px)';
            }
        });
        
        submitBtn.addEventListener('mouseleave', function() {
            if (!this.disabled) {
                this.style.background = 'linear-gradient(135deg, #8b6eea 0%, #9d5fb8 100%)';
                this.style.boxShadow = '0 4px 15px rgba(139,110,234,0.4)';
                this.style.transform = 'translateY(0)';
            }
        });
        
        submitBtn.addEventListener('mousedown', function() {
            if (!this.disabled) {
                this.style.transform = 'translateY(0)';
            }
        });
    }
    
    // Initialize form validation
    validateProfessionalForm();
    
    // Set default gender and length selections
    selectGender('boy');
    selectLength('medium');
});

// Handle story generation
async function handleStoryGeneration(e) {
    e.preventDefault();
    console.log('📝 Story generation started');

    // Check if form is valid (we removed disabled so need to check here)
    const submitBtn = e.target.querySelector('button[type="submit"]');
    if (submitBtn && submitBtn.dataset.valid !== 'true') {
        const name = document.getElementById('characterName').value.trim();
        if (!name) { showToast('Enter a character name first', 'warning'); return; }
        if (!selectedAge) { showToast('Select an age', 'warning'); return; }
        showToast('Select a theme to continue', 'warning');
        return;
    }

    if (window.isOffline) {
        showToast('You are offline. Connect to the internet to create stories.', 'warning');
        return;
    }
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn ? submitBtn.textContent : 'Generate Story';
    
    try {
        // Get form data
        const name = document.getElementById('characterName').value.trim();
        const age = parseInt(document.getElementById('characterAge').value);
        let theme = selectedTheme;
        
        console.log('📋 Form data:', { name, age, theme });
        
        if (!name || !age || !theme) {
            showToast('Please fill in all fields and select a theme.', 'warning');
            return;
        }
        
        // Track if this is a custom theme
        let isCustomTheme = false;
        let customCoverNumber = null;
        if (theme === 'custom') {
            const customTheme = document.getElementById('customTheme').value.trim();
            if (!customTheme) {
                showToast('Please enter a custom theme name.', 'warning');
                return;
            }
            isCustomTheme = true;
            // Pick random cover number once (1-12)
            customCoverNumber = Math.floor(Math.random() * 12) + 1;
            theme = customTheme;
        }
        
        // Store custom theme flag and cover number
        window.isCustomTheme = isCustomTheme;
        window.customCoverNumber = customCoverNumber;
        
        // Show loading state immediately
        submitBtn.classList.add('btn-loading');
        submitBtn.textContent = 'Creating Story...';
        submitBtn.disabled = true;
        
        // Show character helper immediately with multiple encouraging messages
        showCharacterMessage("🎨 Hold on tight! I'm preparing your magical story...");
        
        // Show different encouraging messages during generation
        setTimeout(() => {
            showCharacterMessage("✨ Sprinkling some magic dust on your story...");
        }, 2000);
        
        setTimeout(() => {
            showCharacterMessage("📚 Adding colorful characters and exciting adventures...");
        }, 4000);
        
        setTimeout(() => {
            showCharacterMessage("🌟 Almost ready! Your story is going to be amazing!");
        }, 6000);
        
        // Hide any previous results
        const storyResult = document.getElementById('storyResult');
        if (storyResult) {
            storyResult.classList.add('hidden');
        }
        
        const requestData = { name, age, theme, gender: selectedGender, length: selectedLength };
        
        // Add extra story details if provided
        const storyDetailsEl = document.getElementById('storyDetails');
        if (storyDetailsEl && storyDetailsEl.value.trim()) {
            requestData.extra_details = storyDetailsEl.value.trim();
        }
        console.log('🚀 Sending request to:', `${API_BASE_URL}/generate-story`);
        console.log('📋 Request data:', requestData);
        console.log('🌐 Using fetch with full URL and headers...');
        
        // Make API call with explicit headers and longer timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout
        
        const response = await fetch(`${API_BASE_URL}/generate-story`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            body: JSON.stringify(requestData),
            mode: 'cors',
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        console.log('📡 Response received:', response.status, response.statusText);
        console.log('📡 Response headers:', [...response.headers.entries()]);
        console.log('📡 Response ok:', response.ok);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ API Error:', errorText);
            let errorMessage;
            try {
                const errorData = JSON.parse(errorText);
                errorMessage = errorData.detail || 'Failed to generate story';
            } catch {
                errorMessage = `Server error: ${response.status}`;
            }
            throw new Error(errorMessage);
        }
        
        const storyData = await response.json();
        console.log('✅ Story generated:', storyData);
        console.log('📌 Full response data:', JSON.stringify(storyData, null, 2));
        currentStory = storyData;
        showToast(`"${storyData.title}" is ready!`, 'success');
        
        // Add custom cover number to story data BEFORE saving
        if (window.isCustomTheme && window.customCoverNumber) {
            storyData.customCoverNumber = window.customCoverNumber;
            storyData.isCustomTheme = true;
            console.log('✅ Added custom cover number to story:', window.customCoverNumber);
        }
        
        // Store the story_id in window.currentStoryData for favorites
        window.currentStoryData = storyData;
        
        if (storyData.story_id) {
            console.log('✅ Story ID received:', storyData.story_id);
            console.log('✅ Story automatically saved to database!');
            
            // Update the story in database with cover number
            if (window.isCustomTheme && window.customCoverNumber) {
                await updateStoryWithCoverNumber(storyData.story_id, window.customCoverNumber);
            }
        } else {
            console.error('❌ ERROR: No story_id in response!');
            console.error('❌ Response keys:', Object.keys(storyData));
            showToast('Story may not have saved properly.', 'warning');
        }
        
        // Display the story in the full storyView page
        window._storyViewSource = 'create';
        showSection('storyView');
        setTimeout(() => displayStoryInView(storyData), 100);
        
        // Refresh the gallery to show the new story
        loadRecentStories();
        loadGalleryStats();
        
        // Show owl helper for story completion
        setTimeout(() => {
            showCharacterMessage(`🎉 Hooray! Your story "${storyData.title}" is ready! Click below to read it!`);
        }, 500);
        
        // Hide character helper after showing the button
        setTimeout(() => {
            hideCharacterMessage();
        }, 4000);
        
        // Note: Removed automatic recent stories reload to improve performance
        
    } catch (error) {
        console.error('❌ Error generating story:', error);
        
        // More specific error messages
        let errorMessage = 'Unknown error occurred';
        if (error.name === 'AbortError') {
            errorMessage = 'Story generation timed out. The AI is taking too long to respond. Please try again.';
        } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
            errorMessage = `Cannot connect to server at ${API_BASE_URL}. Please check if the server is running.`;
        } else if (error.name === 'SyntaxError') {
            errorMessage = 'Server returned invalid response. Check server logs.';
        } else {
            errorMessage = error.message;
        }
        
        showToast('Error: ' + errorMessage, 'error', 5000);
        hideCharacterMessage();
    } finally {
        // Reset button state
        submitBtn.classList.remove('btn-loading');
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
}

// Update story with custom cover number
async function updateStoryWithCoverNumber(storyId, coverNumber) {
    try {
        console.log(`🔄 Updating story ${storyId} with cover number ${coverNumber}`);
        
        // Fetch the full story
        const response = await fetch(`${API_BASE_URL}/stories/${storyId}`);
        if (!response.ok) return;
        
        const storyData = await response.json();
        
        // Add cover number
        storyData.customCoverNumber = coverNumber;
        storyData.isCustomTheme = true;
        
        // Update via PUT endpoint (we'll create this)
        const updateResponse = await fetch(`${API_BASE_URL}/stories/${storyId}/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                customCoverNumber: coverNumber,
                isCustomTheme: true
            })
        });
        
        if (updateResponse.ok) {
            console.log('✅ Story updated with cover number');
        }
    } catch (error) {
        console.error('❌ Error updating story with cover number:', error);
    }
}

// Render story into the dedicated storyView section (gallery/favorites flow)
function displayStoryInView(storyData) {
    const container = document.getElementById('storyViewContent');
    if (!container) return;
    // Temporarily swap storyText target so displayStory renders there
    const _orig = document.getElementById('storyText');
    // Create a fake storyResult + storyText inside storyViewContent
    container.innerHTML = '<div id="storyViewResult"><div id="storyViewText"></div></div>';
    // Patch displayStory to use our container by temporarily overriding getElementById
    const _origGetEl = document.getElementById.bind(document);
    const patchMap = { storyResult: 'storyViewResult', storyText: 'storyViewText' };
    document._patchedGetEl = true;
    const origFn = document.getElementById;
    document.getElementById = function(id) {
        return origFn.call(document, patchMap[id] || id);
    };
    displayStory(storyData);
    document.getElementById = origFn;
}

function goBackFromStory() {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    ttsActive = false; ttsPaused = false; autoReadMode = false;
    const src = window._storyViewSource || 'gallery';
    if (src === 'favoritesModal') {
        showSection('gallery');
        showFavorites();
    } else {
        showSection(src); // 'gallery' or 'create'
    }
}

// Display generated story as a picture book with INLINE STYLES (bypasses CSS conflicts)
function displayStory(storyData) {
    totalPages = storyData.pages.length;
    currentPage = 0;
    
    const storyResult = document.getElementById('storyResult');
    const storyText = document.getElementById('storyText');
    
    if (!storyResult || !storyText) return;
    
    // Preserve story_id and custom cover number if they exist
    if (!storyData.story_id && window.currentStoryData && window.currentStoryData.story_id) {
        storyData.story_id = window.currentStoryData.story_id;
    }
    
    // Save custom cover number with story data if this is a custom theme
    if (window.isCustomTheme && window.customCoverNumber) {
        storyData.customCoverNumber = window.customCoverNumber;
        storyData.isCustomTheme = true;
    }
    
    window.currentStoryData = storyData;
    console.log('📌 Current story data:', window.currentStoryData);
    console.log('📌 Story ID:', window.currentStoryData.story_id);
    
    showCharacterMessage("📖 Your beautiful book is ready!");
    
    const pageEmojis = ['🏔️', '🗺️', '🌲', '🦊', '🌉', '⭐', '🎨', '🌈'];
    
    // Using inline styles to avoid CSS conflicts
    let bookHTML = `
        <div style="max-width: 1100px; margin: 0 auto; position: relative;">
            <!-- Top action buttons: Back left, Favorite right -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px;">
                <button onclick="goBackFromStory()" style="display: inline-flex; align-items: center; gap: 8px; padding: 10px 20px; background: #667eea; border: none; border-radius: 50px; color: white; font-size: 0.88rem; font-weight: 600; cursor: pointer; font-family: 'Nunito', sans-serif; transition: all 0.2s ease; box-shadow: 0 4px 12px rgba(102,126,234,0.3);" onmouseover="this.style.background='#5a6fd6'" onmouseout="this.style.background='#667eea'">
                    ← Back
                </button>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <!-- Star Rating -->
                    <div style="display: flex; align-items: center; gap: 4px; background: rgba(0,0,0,0.25); border-radius: 30px; padding: 6px 14px;">
                        ${[1,2,3,4,5].map(i => `<span id="star-${i}" onclick="rateStory(${i})" style="font-size: 1.3rem; cursor: pointer; color: rgba(255,255,255,0.3); transition: color 0.15s; user-select: none;" onmouseover="hoverStars(${i})" onmouseout="resetStars()">★</span>`).join('')}
                        <span id="ratingLabel" style="font-size: 0.72rem; color: rgba(255,255,255,0.55); margin-left: 4px; white-space: nowrap;"></span>
                    </div>
                    <button id="favoriteBtn" onclick="toggleFavorite()" style="background: linear-gradient(135deg, #ec4899 0%, #be185d 100%); border: none; border-radius: 50px; padding: 10px 22px; display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 0.9rem; font-weight: 700; transition: all 0.3s ease; box-shadow: 0 4px 12px rgba(236,72,153,0.4); color: white; font-family: 'Nunito', sans-serif;">
                        <span id="favoriteIcon" style="font-size: 1.2rem;">🤍</span>
                        <span id="favoriteText">Add to Favorites</span>
                    </button>
                </div>
            </div>

            <!-- Open Book Container -->
            <div style="position: relative; height: 620px; overflow: hidden; border-radius: 4px; border: 6px solid #8b6f47; box-shadow: 0 0 0 2px #d4a574, 0 0 0 4px #8b6f47, 0 40px 100px rgba(0,0,0,0.6), inset 0 0 30px rgba(139,111,71,0.15);">
                <!-- Progress bar -->
                <div style="position: absolute; top: 0; left: 0; right: 0; height: 4px; background: rgba(0,0,0,0.15); z-index: 50; overflow: hidden;">
                    <div id="storyProgressBar" style="height: 100%; width: 0%; background: linear-gradient(90deg, #667eea, #a78bfa); transition: width 0.5s ease;"></div>
                </div>

                <!-- Cover Page -->
                <div id="coverPage" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #1a202c; overflow: hidden; color: white; text-align: center;">
                    <img id="coverImage" src="" alt="" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; z-index: 1; display: none;">
                    <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(to bottom, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.55) 100%); z-index: 2;"></div>
                    <div style="position: relative; z-index: 3; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px;">
                        <h1 style="font-family: 'Nunito', sans-serif; font-size: 2.8rem; font-weight: 900; margin-bottom: 12px; text-shadow: 3px 3px 12px rgba(0,0,0,0.7); line-height: 1.2; color: white;">${storyData.title}</h1>
                        <p style="font-size: 1.2rem; margin-bottom: 36px; opacity: 0.85; color: white; font-weight: 600;">✨ A Magical Story</p>
                        <button onclick="startReading()" style="background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%); color: white; border: none; padding: 14px 40px; font-size: 1rem; font-weight: 800; border-radius: 50px; cursor: pointer; font-family: 'Nunito', sans-serif; box-shadow: 0 8px 24px rgba(251,191,36,0.5); text-transform: uppercase; letter-spacing: 1.5px; transition: all 0.3s ease; display: flex; align-items: center; gap: 10px;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                            <span style="font-size: 1.2rem;">📖</span> START READING
                        </button>
                    </div>
                </div>
    `;
    
    // Add story pages - open book layout
    storyData.pages.forEach((page, index) => {
        const emoji = pageEmojis[index] || '📖';
        const isLessonPage = page.text.includes('What') && page.text.includes('Learned');

        if (isLessonPage) {
            // Lesson page — full-width cream paper, centered text
            bookHTML += `
                <div id="page${page.page_number}" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: none; align-items: center; justify-content: center; background: #fdf6e3; overflow: hidden;">
                    <div style="position: absolute; top: 12px; right: 22px; font-size: 1rem; color: #8b6f47; font-weight: 700; opacity: 0.6;">${page.page_number}</div>
                    <div style="max-width: 700px; padding: 50px 60px; text-align: center;">
                        <div style="font-size: 1.15rem; line-height: 2; color: #3d2b1f; font-weight: 500; white-space: pre-line;">${page.text}</div>
                    </div>
                </div>
            `;
        } else {
            // Open-book: left = illustration panel, right = cream paper text
            const gradients = [
                'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
                'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
                'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
                'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)',
                'linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 100%)',
            ];
            const imgBg = gradients[index % gradients.length];
            bookHTML += `
                <div id="page${page.page_number}" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: none; overflow: hidden;">
                    <div style="display: flex; width: 100%; height: 100%;">
                        <!-- Left page: illustration -->
                        <div id="illus-${page.page_number}" style="width: 48%; flex-shrink: 0; background: ${imgBg}; display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden;">
                            <!-- Placeholder while image loads -->
                            <div id="illus-placeholder-${page.page_number}" style="display:flex; flex-direction:column; align-items:center; gap:12px; z-index:1;">
                                <div style="font-size: 5rem; filter: drop-shadow(0 8px 24px rgba(0,0,0,0.3));">${emoji}</div>
                                <div style="color:rgba(255,255,255,0.7); font-size:0.8rem; font-weight:600; font-family:'Nunito',sans-serif;">Generating art...</div>
                                <div style="width:40px; height:4px; background:rgba(255,255,255,0.3); border-radius:2px; overflow:hidden;"><div style="width:100%; height:100%; background:white; border-radius:2px; animation: shimmer 1.2s infinite;"></div></div>
                            </div>
                            <!-- Generated image (hidden until loaded) -->
                            <img id="illus-img-${page.page_number}" src="" alt="Story illustration" style="position:absolute; top:0; left:0; width:100%; height:100%; object-fit:cover; display:none; z-index:1;">
                            <!-- deep spine shadow — right edge of left page -->
                            <div style="position: absolute; right: 0; top: 0; width: 40px; height: 100%; background: linear-gradient(to right, transparent 0%, rgba(0,0,0,0.25) 70%, rgba(0,0,0,0.55) 100%); z-index: 2;"></div>
                        </div>
                        <!-- Right page: cream paper -->
                        <div style="flex: 1; background: #fdf6e3; background-image: url('img/paper-texture.jpg'); background-size: cover; display: flex; flex-direction: column; justify-content: center; padding: 44px 40px 44px 50px; position: relative; overflow-y: auto;">
                            <!-- deep spine shadow — left edge of right page -->
                            <div style="position: absolute; left: 0; top: 0; width: 40px; height: 100%; background: linear-gradient(to right, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0.18) 50%, transparent 100%); z-index: 2;"></div>
                            <!-- spine crease highlight line -->
                            <div style="position: absolute; left: 2px; top: 0; width: 1px; height: 100%; background: linear-gradient(to bottom, transparent, rgba(255,255,255,0.18) 30%, rgba(255,255,255,0.18) 70%, transparent); z-index: 3;"></div>
                            <div style="position: absolute; top: 14px; right: 18px; font-size: 0.95rem; color: #8b6f47; font-weight: 700; opacity: 0.55; z-index: 4;">${page.page_number}</div>
                            <p style="font-size: 1.15rem; line-height: 2; color: #3d2b1f; font-weight: 500; margin: 0; position: relative; z-index: 1;">${page.text}</p>
                        </div>
                    </div>
                </div>
            `;
        }
    });
    
    // Close book container, navigation, and audio bar
    bookHTML += `
            </div>

            <!-- Page dots centered below book -->
            <div id="pageIndicator" style="display: flex; gap: 8px; align-items: center; justify-content: center; margin-top: 16px;">
                <div class="page-dot" style="width: 10px; height: 10px; border-radius: 50%; background: #667eea; transform: scale(1.2); box-shadow: 0 0 8px rgba(102,126,234,0.6);"></div>
                ${storyData.pages.map(() => '<div class="page-dot" style="width: 8px; height: 8px; border-radius: 50%; background: rgba(255,255,255,0.35);"></div>').join('')}
            </div>

            <!-- Navigation -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 14px;">
                <button id="prevBtn" onclick="previousPage()" disabled style="background: #667eea; color: white; border: none; padding: 11px 26px; font-size: 0.95rem; font-weight: bold; border-radius: 50px; cursor: not-allowed; font-family: 'Nunito', sans-serif; transition: all 0.3s ease; opacity: 0.5; display: flex; align-items: center; gap: 8px; box-shadow: 0 4px 12px rgba(102,126,234,0.3);">
                    <span>←</span><span>PREVIOUS</span>
                </button>
                <button id="nextBtn" onclick="nextPage()" style="background: #667eea; color: white; border: none; padding: 11px 26px; font-size: 0.95rem; font-weight: bold; border-radius: 50px; cursor: pointer; font-family: 'Nunito', sans-serif; transition: all 0.3s ease; display: flex; align-items: center; gap: 8px; box-shadow: 0 4px 12px rgba(102,126,234,0.3);">
                    <span>NEXT</span><span>→</span>
                </button>
            </div>
        </div>

        <!-- ===== YouTube-style Dark Audio Bar ===== -->
        <div id="audioBar" style="max-width: 1100px; margin: 18px auto 0; background: #1e1b4b; border-radius: 16px; padding: 14px 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.4); font-family: 'Nunito', sans-serif; overflow: hidden;">
            <!-- Main bar row -->
            <div style="display: flex; align-items: center; gap: 16px;">
                <!-- Play/Pause button -->
                <button id="readAloudBtn" onclick="toggleReadAloud()" style="flex-shrink: 0; width: 48px; height: 48px; border-radius: 50%; border: none; background: linear-gradient(135deg, #6366f1, #4f46e5); color: white; font-size: 1.3rem; cursor: pointer; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 14px rgba(99,102,241,0.5); transition: all 0.2s ease;">🔊</button>
                <!-- Title + status -->
                <div style="flex: 1; min-width: 0;">
                    <div style="color: white; font-weight: 700; font-size: 0.95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${storyData.title}</div>
                    <div id="audioStatus" style="color: #a5b4fc; font-size: 0.78rem; margin-top: 2px;">Press play to listen</div>
                </div>
                <!-- Settings gear -->
                <button onclick="toggleAudioSettings()" style="flex-shrink: 0; width: 40px; height: 40px; border-radius: 50%; border: 1px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.08); color: #a5b4fc; font-size: 1.1rem; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s ease;" title="Audio settings">⚙️</button>
                <!-- Auto-read toggle -->
                <button id="autoReadBtn" onclick="toggleAutoRead()" style="flex-shrink: 0; display: flex; align-items: center; gap: 6px; padding: 8px 14px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.08); color: #a5b4fc; font-size: 0.78rem; font-weight: 600; cursor: pointer; font-family: 'Nunito', sans-serif; transition: all 0.2s ease; white-space: nowrap;" title="Auto-advance pages when reading">
                    <span style="font-size:0.9rem">▶▶</span> Auto
                </button>
            </div>

            <!-- Slide-down settings panel (hidden by default) -->
            <div id="audioSettingsPanel" style="max-height: 0; overflow: hidden; transition: max-height 0.35s ease, opacity 0.3s ease; opacity: 0;">
                <div style="border-top: 1px solid rgba(255,255,255,0.1); margin-top: 14px; padding-top: 14px; display: flex; flex-wrap: wrap; gap: 20px; align-items: flex-start;">
                    <!-- Voice accents -->
                    <div>
                        <div style="color: #a5b4fc; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 8px;">Voice Accent</div>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            <button onclick="selectVoicePreset('us')"   id="vpill-us"   class="vpill vpill-active" style="padding: 6px 14px; border-radius: 8px; border: 1px solid #6366f1; background: #6366f1; color: white; font-size: 0.82rem; font-weight: 600; cursor: pointer; font-family: inherit; transition: all 0.15s;">🇺🇸 US</button>
                            <button onclick="selectVoicePreset('uk')"   id="vpill-uk"   class="vpill"             style="padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.2); background: rgba(255,255,255,0.07); color: #c4b5fd; font-size: 0.82rem; font-weight: 600; cursor: pointer; font-family: inherit; transition: all 0.15s;">🇬🇧 UK</button>
                            <button onclick="selectVoicePreset('in')"   id="vpill-in"   class="vpill"             style="padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.2); background: rgba(255,255,255,0.07); color: #c4b5fd; font-size: 0.82rem; font-weight: 600; cursor: pointer; font-family: inherit; transition: all 0.15s;">🇮🇳 IN</button>
                            <button onclick="selectVoicePreset('au')"   id="vpill-au"   class="vpill"             style="padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.2); background: rgba(255,255,255,0.07); color: #c4b5fd; font-size: 0.82rem; font-weight: 600; cursor: pointer; font-family: inherit; transition: all 0.15s;">🇦🇺 AU</button>
                            <button onclick="selectVoicePreset('kids')" id="vpill-kids" class="vpill"             style="padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.2); background: rgba(255,255,255,0.07); color: #c4b5fd; font-size: 0.82rem; font-weight: 600; cursor: pointer; font-family: inherit; transition: all 0.15s;">🧒 Kids</button>
                        </div>
                    </div>
                    <!-- Divider -->
                    <div style="width: 1px; background: rgba(255,255,255,0.1); align-self: stretch; display: none;" class="audio-divider"></div>
                    <!-- Speed -->
                    <div>
                        <div style="color: #a5b4fc; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 8px;">Speed</div>
                        <div style="display: flex; gap: 0; border-radius: 8px; overflow: hidden; border: 1px solid rgba(255,255,255,0.15);">
                            <button onclick="selectSpeed(0.7,  this)" id="spd-slow"   style="padding: 6px 16px; border: none; background: rgba(255,255,255,0.07); color: #c4b5fd; font-size: 0.82rem; font-weight: 600; cursor: pointer; font-family: inherit; transition: all 0.15s; border-right: 1px solid rgba(255,255,255,0.1);">Slow</button>
                            <button onclick="selectSpeed(0.9,  this)" id="spd-normal" style="padding: 6px 16px; border: none; background: #6366f1; color: white; font-size: 0.82rem; font-weight: 600; cursor: pointer; font-family: inherit; transition: all 0.15s; border-right: 1px solid rgba(255,255,255,0.1);">Normal</button>
                            <button onclick="selectSpeed(1.15, this)" id="spd-fast"   style="padding: 6px 16px; border: none; background: rgba(255,255,255,0.07); color: #c4b5fd; font-size: 0.82rem; font-weight: 600; cursor: pointer; font-family: inherit; transition: all 0.15s;">Fast</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    storyText.innerHTML = bookHTML;

    // Load cover image with longer delay to ensure DOM is ready
    setTimeout(() => {
        console.log('🖼️ Attempting to load cover for theme:', storyData.theme);
        const coverImg = document.getElementById('coverImage');
        console.log('🖼️ Cover image element found:', !!coverImg);
        if (coverImg) {
            console.log('🖼️ Cover image element display:', coverImg.style.display);
        }
        // Use 'custom' as theme if this was a custom theme
        const themeForCover = (window.isCustomTheme || storyData.isCustomTheme) ? 'custom' : storyData.theme;
        console.log('🖼️ Using theme for cover:', themeForCover);
        // Pass the saved cover number if available
        const coverNumber = storyData.customCoverNumber || window.customCoverNumber;
        loadCoverImage(themeForCover, coverNumber);

        // Kick off AI image generation for all story pages
        generateAllPageImages(storyData);
    }, 300);
    
    storyResult.classList.remove('hidden');
    storyResult.scrollIntoView({ behavior: 'smooth' });
    
    setTimeout(() => hideCharacterMessage(), 3000);
    console.log('✅ Book displayed with inline styles - CSS conflicts bypassed!');
    
    // Check if this story is already favorited and update button
    setTimeout(() => {
        updateFavoriteButton();
        initStarRating();
    }, 100);
}

// Track which cover was used last for each theme (alternates between 1 and 2)
let lastCoverUsed = {};

// Generate AI images for all story pages (sequential to avoid rate limits)
async function generateAllPageImages(storyData) {
    const pages = storyData.pages.filter(p => {
        // skip lesson page
        return !(p.text.includes('What') && p.text.includes('Learned'));
    });

    const charName = storyData.title
        ? storyData.title.replace(/['']s .*/i, '').replace(/^(The |A |An )/i, '').trim()
        : '';

    // char_desc comes from backend — fixed physical description for visual consistency
    const charDesc = storyData.char_desc || '';

    // Generate one at a time — sequential so we don't hammer the API
    for (const page of pages) {
        await generatePageImage(page, storyData.story_id, charName, charDesc);
    }
}

async function generatePageImage(page, storyId, charName, charDesc) {
    const text = page.text || '';
    if (!text.trim()) return;

    const img = document.getElementById(`illus-img-${page.page_number}`);
    const placeholder = document.getElementById(`illus-placeholder-${page.page_number}`);

    // ── Check disk cache first via /story-image endpoint ──────────────────────
    if (storyId && page.page_number) {
        try {
            const cacheRes = await fetch(`${API_BASE_URL}/story-image/${storyId}/${page.page_number}`);
            if (cacheRes.ok) {
                const blob = await cacheRes.blob();
                const url = URL.createObjectURL(blob);
                if (img) {
                    img.src = url;
                    img.onload = () => {
                        img.style.display = 'block';
                        if (placeholder) placeholder.style.display = 'none';
                    };
                }
                console.log(`💾 Page ${page.page_number}: loaded from disk cache`);
                return;
            }
        } catch (e) {
            // cache miss, fall through to generate
        }
    }

    // ── Not cached — generate fresh ───────────────────────────────────────────
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 90000); // 90s max

        const res = await fetch(`${API_BASE_URL}/generate-image`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text,
                story_id: storyId || null,
                page_num: page.page_number,
                char_name: charName || '',
                char_desc: charDesc || ''
            }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            const msg = errData.detail || `HTTP ${res.status}`;
            // Show quota error clearly to user
            if (res.status === 429) {
                if (placeholder) {
                    placeholder.innerHTML = '⛔ GPU quota exceeded<br><small>Try again in ~1 hour or change IMAGE_MODE in .env</small>';
                    placeholder.style.fontSize = '12px';
                }
            } else {
                if (placeholder) placeholder.innerHTML = '❌ Image failed';
            }
            console.warn(`⚠️ Image gen failed page ${page.page_number}: ${msg}`);
            return;
        }

        const data = await res.json();
        if (!data.image) return;

        console.log(`✅ Page ${page.page_number}: generated via ${data.backend}`);

        if (img) {
            img.src = data.image;
            img.onload = () => {
                img.style.display = 'block';
                if (placeholder) placeholder.style.display = 'none';
            };
        }
    } catch (e) {
        if (e.name === 'AbortError') {
            console.warn(`⏱️ Image gen timed out for page ${page.page_number}`);
            if (placeholder) placeholder.innerHTML = '⏱️ Timed out';
        } else {
            console.warn(`⚠️ Image gen failed for page ${page.page_number}:`, e.message);
        }
    }
}

// Function to load cover image based on theme
function loadCoverImage(theme, savedCoverNumber) {
    console.log('🎨 loadCoverImage called with theme:', theme, 'savedCoverNumber:', savedCoverNumber);
    
    let imageNumber;
    
    // Special handling for custom theme
    if (theme && theme.toLowerCase() === 'custom') {
        // Use saved cover number if available, otherwise pick random
        if (savedCoverNumber) {
            imageNumber = savedCoverNumber;
            console.log('✨ Using saved custom cover:', imageNumber);
        } else {
            imageNumber = Math.floor(Math.random() * 12) + 1; // Random number 1-12
            console.log('✨ Custom theme detected - using random cover:', imageNumber);
        }
    } else {
        // Alternate between cover 1 and 2 for other themes
        if (!lastCoverUsed[theme]) {
            lastCoverUsed[theme] = 1;
        } else {
            lastCoverUsed[theme] = lastCoverUsed[theme] === 1 ? 2 : 1;
        }
        imageNumber = lastCoverUsed[theme];
        console.log('🎨 Using cover number:', imageNumber, 'for theme:', theme);
    }
    
    const coverImage = document.getElementById('coverImage');
    
    if (!coverImage) {
        console.error('❌ Cover image element not found!');
        return;
    }
    
    console.log('✅ Cover image element found');
    
    // Normalize theme name (lowercase, trim spaces)
    const normalizedTheme = theme ? theme.toLowerCase().trim() : 'adventure';
    
    // Try PNG first, then JPG
    const extensions = ['png', 'jpg', 'jpeg'];
    
    function tryLoadImage(extIndex) {
        if (extIndex >= extensions.length) {
            // No image found, show gradient fallback
            console.log('⚠️ Cover image not found, using gradient fallback');
            coverImage.style.display = 'none';
            // Change background to gradient instead of black
            const coverPage = document.getElementById('coverPage');
            if (coverPage) {
                coverPage.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
            }
            return;
        }
        
        const imagePath = `img/covers/${normalizedTheme}-${imageNumber}.${extensions[extIndex]}`;
        console.log('🔍 Trying to load:', imagePath);
        const img = new Image();
        
        img.onload = function() {
            // Image exists, show it
            coverImage.src = imagePath;
            coverImage.style.display = 'block';
            console.log('✅ Cover image loaded successfully:', imagePath);
        };
        
        img.onerror = function() {
            console.log('❌ Failed to load:', imagePath);
            // Try next extension
            tryLoadImage(extIndex + 1);
        };
        
        img.src = imagePath;
    }
    
    tryLoadImage(0);
}

// Function to open the picture book with animation
function openPictureBook() {
    const storyData = window.currentStoryData;
    if (!storyData) return;
    
    const storyText = document.getElementById('storyText');
    
    // Show owl helper
    showCharacterMessage("📖 Your beautiful book is ready!");
    
    // Create book HTML matching test_book_ui.html structure
    let bookHTML = `
        <div class="animated-book-container">
            <div class="book-opening">
                <div class="story-pages-container">
                    <div class="book-wrapper">
                        <!-- Cover Page -->
                        <div class="book-page book-cover active" id="coverPage">
                            <!-- Cover Image (loaded dynamically) -->
                            <img class="cover-image-bg" id="coverImage" src="" alt="" style="display: none;">
                            <!-- Overlay for text readability -->
                            <div class="cover-overlay"></div>
                            <!-- Cover Content -->
                            <div class="cover-content">
                                <h1 class="book-title">${storyData.title}</h1>
                                <p class="book-subtitle">A Magical Story</p>
                                <button class="start-reading-btn" onclick="startReading()">
                                    📖 START READING
                                </button>
                                <div class="book-author">Created with ❤️</div>
                            </div>
                        </div>
    `;
    
    // Add story pages with emojis
    const pageEmojis = ['🏔️', '🗺️', '🌲', '🦊', '🌉', '⭐', '🎨', '🌈'];
    storyData.pages.forEach((page, index) => {
        const emoji = pageEmojis[index] || '📖';
        bookHTML += `
            <div class="book-page story-page" id="page${page.page_number}">
                <div class="page-image">${emoji}</div>
                <div class="page-number">${page.page_number}</div>
                <div class="page-text">${page.text}</div>
            </div>
        `;
    });
    
    // Add navigation
    bookHTML += `
                        <!-- Navigation -->
                        <div class="book-navigation">
                            <button class="nav-button" id="prevBtn" onclick="previousPage()" disabled>
                                ← Previous
                            </button>
                            <div class="page-indicator" id="pageIndicator">
                                <div class="page-dot active"></div>
                                ${storyData.pages.map(() => '<div class="page-dot"></div>').join('')}
                            </div>
                            <button class="nav-button" id="nextBtn" onclick="nextPage()">
                                Next →
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    storyText.innerHTML = bookHTML;
    
    // Load the cover image based on theme (alternates between cover 1 and 2)
    loadCoverImage(storyData.theme);
    
    // Hide owl helper
    setTimeout(() => {
        hideCharacterMessage();
    }, 2000);
    
    console.log('✅ Picture book displayed with polished UI and alternating cover!');
}

// No image generation - removed for clean text-only book experience

// Load recent stories
async function loadRecentStories() {
    console.log('📚 Loading recent stories from:', `${API_BASE_URL}/stories`);

    // Show skeleton loaders while fetching
    const storiesList = document.getElementById('recent-stories-list');
    if (storiesList) {
        storiesList.innerHTML = Array(6).fill(0).map(() => `
            <div class="skeleton-card">
                <div class="skeleton" style="height:140px; border-radius:10px;"></div>
                <div class="skeleton" style="height:18px; width:70%;"></div>
                <div class="skeleton" style="height:14px; width:45%;"></div>
                <div style="display:flex; gap:8px; margin-top:4px;">
                    <div class="skeleton" style="height:28px; width:60px; border-radius:20px;"></div>
                    <div class="skeleton" style="height:28px; width:60px; border-radius:20px;"></div>
                </div>
            </div>
        `).join('');
    }

    try {
        const response = await fetch(`${API_BASE_URL}/stories`);
        console.log('📡 Gallery response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`Failed to load stories: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('📖 Stories data received:', data);
        allStories = data.stories;
        // Update count badge
        const countEl = document.getElementById('galleryCount');
        if (countEl) countEl.textContent = `${allStories.length} ${allStories.length === 1 ? 'story' : 'stories'}`;
        displayRecentStories(allStories);
        
    } catch (error) {
        console.error('❌ Error loading recent stories:', error);
        const storiesList = document.getElementById('recent-stories-list');
        if (storiesList) {
            storiesList.innerHTML = `
                <div style="text-align: center; padding: 40px;">
                    <p style="color: #e74c3c; font-size: 1.2rem; margin-bottom: 15px;">⚠️ Error loading stories</p>
                    <p style="color: #666; margin-bottom: 20px;">${error.message}</p>
                    <p style="color: #666;">Make sure the server is running on port 8025 and you've generated at least one story.</p>
                    <button onclick="loadRecentStories()" class="btn btn-primary" style="margin-top: 20px;">🔄 Try Again</button>
                </div>
            `;
        }
    }
}

// Select gender
function selectGender(gender) {
    selectedGender = gender;
    document.querySelectorAll('.gender-btn').forEach(btn => {
        const isSelected = btn.dataset.gender === gender;
        btn.style.borderColor = isSelected ? '#a78bfa' : 'rgba(167,139,250,0.4)';
        btn.style.background = isSelected ? 'rgba(167,139,250,0.5)' : 'rgba(118,75,162,0.25)';
        btn.style.boxShadow = isSelected ? '0 4px 12px rgba(167,139,250,0.6)' : 'none';
        btn.style.transform = isSelected ? 'scale(1.05)' : 'scale(1)';
    });
}

// Select story length
function selectLength(length) {
    selectedLength = length;
    document.querySelectorAll('.length-btn').forEach(btn => {
        const isSelected = btn.dataset.length === length;
        btn.style.borderColor = isSelected ? '#a78bfa' : 'rgba(167,139,250,0.4)';
        btn.style.background = isSelected ? 'rgba(167,139,250,0.5)' : 'rgba(118,75,162,0.25)';
        btn.style.boxShadow = isSelected ? '0 4px 12px rgba(167,139,250,0.6)' : 'none';
        btn.style.transform = isSelected ? 'scale(1.05)' : 'scale(1)';
    });
}

// Load gallery stats
async function loadGalleryStats() {
    try {
        const res = await fetch(`${API_BASE_URL}/stats`);
        if (!res.ok) return;
        const data = await res.json();
        const ts = document.getElementById('statTotalStories');
        const tf = document.getElementById('statFavorites');
        if (ts) ts.textContent = data.total_stories;
        if (tf) tf.textContent = data.total_favorites;
    } catch (e) { /* silent */ }
}

// Compute reading streak from localStorage
function computeStreak() {
    const today = new Date().toDateString();
    const stored = JSON.parse(localStorage.getItem('readStreak') || '{"streak":0,"lastDate":""}');
    const yesterday = new Date(Date.now() - 86400000).toDateString();
    let streak = stored.streak || 0;
    if (stored.lastDate === today) {
        // already counted today
    } else if (stored.lastDate === yesterday) {
        streak += 1;
        localStorage.setItem('readStreak', JSON.stringify({ streak, lastDate: today }));
    } else if (stored.lastDate !== today) {
        streak = 1;
        localStorage.setItem('readStreak', JSON.stringify({ streak, lastDate: today }));
    }
    const el = document.getElementById('statStreak');
    if (el) el.textContent = streak + (streak >= 2 ? ' 🔥' : '');
}

// Set theme filter for gallery
function setThemeFilter(filter, btn) {
    currentThemeFilter = filter;
    document.querySelectorAll('.theme-filter-pill').forEach(p => {
        p.style.borderColor = 'rgba(167,139,250,0.25)';
        p.style.background = 'transparent';
        p.style.color = 'rgba(229,241,251,0.7)';
    });
    if (btn) {
        btn.style.borderColor = '#a78bfa';
        btn.style.background = 'rgba(167,139,250,0.2)';
        btn.style.color = '#e5f1fb';
    }
    filterGallery();
}

// Rate a story (1-5 stars)
async function rateStory(stars) {
    if (!window.currentStoryData?.story_id) return;
    try {
        const res = await fetch(`${API_BASE_URL}/stories/${window.currentStoryData.story_id}/rate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rating: stars })
        });
        if (!res.ok) return;
        window.currentStoryData.rating = stars;
        // Update star UI
        for (let i = 1; i <= 5; i++) {
            const s = document.getElementById(`star-${i}`);
            if (s) s.style.color = i <= stars ? '#fbbf24' : 'rgba(255,255,255,0.3)';
        }
        const ratingLabel = document.getElementById('ratingLabel');
        if (ratingLabel) ratingLabel.textContent = `You rated this ${stars}/5 ⭐`;
    } catch (e) { /* silent */ }
}

function hoverStars(n) {
    for (let i = 1; i <= 5; i++) {
        const s = document.getElementById(`star-${i}`);
        if (s) s.style.color = i <= n ? '#fde68a' : 'rgba(255,255,255,0.3)';
    }
}

function resetStars() {
    const saved = window.currentStoryData?.rating || 0;
    for (let i = 1; i <= 5; i++) {
        const s = document.getElementById(`star-${i}`);
        if (s) s.style.color = i <= saved ? '#fbbf24' : 'rgba(255,255,255,0.3)';
    }
}

function initStarRating() {
    const saved = window.currentStoryData?.rating || 0;
    resetStars();
    const ratingLabel = document.getElementById('ratingLabel');
    if (ratingLabel) ratingLabel.textContent = saved ? `You rated this ${saved}/5 ⭐` : 'Rate this story';
}

// Filter and sort gallery
let currentSort = 'newest';

function setSort(sort) {
    currentSort = sort;
    // Update button styles
    const newestBtn = document.getElementById('sortNewest');
    const oldestBtn = document.getElementById('sortOldest');
    if (newestBtn && oldestBtn) {
        if (sort === 'newest') {
            newestBtn.style.borderColor = '#a78bfa';
            newestBtn.style.background = 'rgba(167,139,250,0.2)';
            newestBtn.style.color = '#e5f1fb';
            oldestBtn.style.borderColor = 'rgba(167,139,250,0.25)';
            oldestBtn.style.background = 'transparent';
            oldestBtn.style.color = 'rgba(229,241,251,0.6)';
        } else {
            oldestBtn.style.borderColor = '#a78bfa';
            oldestBtn.style.background = 'rgba(167,139,250,0.2)';
            oldestBtn.style.color = '#e5f1fb';
            newestBtn.style.borderColor = 'rgba(167,139,250,0.25)';
            newestBtn.style.background = 'transparent';
            newestBtn.style.color = 'rgba(229,241,251,0.6)';
        }
    }
    filterGallery();
}

function filterGallery() {
    const query = (document.getElementById('gallerySearch')?.value || '').toLowerCase();

    let filtered = allStories.filter(s => {
        const matchesSearch = s.title.toLowerCase().includes(query) ||
            s.name.toLowerCase().includes(query) ||
            s.theme.toLowerCase().includes(query);
        const knownThemes = ['adventure', 'fantasy', 'friendship', 'animals', 'space', 'ocean'];
        const isCustom = s.isCustomTheme || !knownThemes.includes(s.theme.toLowerCase());
        const matchesTheme = currentThemeFilter === 'all' ||
            (currentThemeFilter === 'custom' ? isCustom : s.theme.toLowerCase() === currentThemeFilter);
        return matchesSearch && matchesTheme;
    });

    if (currentSort === 'oldest') {
        filtered = filtered.slice().sort((a, b) => new Date(a.date) - new Date(b.date));
    } else {
        filtered = filtered.slice().sort((a, b) => new Date(b.date) - new Date(a.date));
    }

    // Update count badge
    const countEl = document.getElementById('galleryCount');
    if (countEl) {
        countEl.textContent = filtered.length === allStories.length
            ? `${allStories.length} ${allStories.length === 1 ? 'story' : 'stories'}`
            : `${filtered.length} of ${allStories.length} stories`;
    }

    displayRecentStories(filtered);
}

// Display recent stories
function displayRecentStories(stories) {
    const storiesList = document.getElementById('recent-stories-list');
    if (!storiesList) {
        console.error('❌ recent-stories-list element not found');
        return;
    }
    
    console.log('📚 Displaying', stories.length, 'stories');
    
    if (stories.length === 0) {
        storiesList.innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <p style="font-size: 1.2rem; color: #666; margin-bottom: 15px;">📚 No stories created yet</p>
                <p style="color: #999; margin-bottom: 20px;">Create your first magical story to see it here!</p>
                <button onclick="showSection('create')" class="btn btn-primary">✨ Create Story</button>
            </div>
        `;
        return;
    }
    
    // Beautiful grid layout with cover images like the reference
    let html = '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 25px; padding: 20px;">';
    
    // Known theme list
    const knownThemes = ['adventure', 'fantasy', 'friendship', 'animals', 'space', 'ocean'];
    
    stories.forEach(story => {
        const date = new Date(story.date).toLocaleDateString();
        
        // Check if theme is custom (not in known themes list) or has isCustomTheme flag
        const isCustomTheme = story.isCustomTheme || !knownThemes.includes(story.theme.toLowerCase());
        
        // For custom theme, use saved cover number or pick random, otherwise use cover 1
        let coverImage;
        if (isCustomTheme) {
            const coverNum = story.customCoverNumber || Math.floor(Math.random() * 12) + 1;
            coverImage = `img/covers/custom-${coverNum}.png`;
            console.log(`📸 Custom story ${story.id}: using cover ${coverNum}, saved: ${story.customCoverNumber}`);
        } else {
            coverImage = `img/covers/${story.theme}-1.png`;
        }
        
        html += `
            <div style="cursor: pointer; background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1); transition: all 0.3s ease; position: relative;" onmouseover="this.style.transform='translateY(-5px)'; this.style.boxShadow='0 8px 25px rgba(0,0,0,0.15)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(0,0,0,0.1)'">
                <!-- Delete Button -->
                <button onclick="event.stopPropagation(); deleteStory(${story.id})" style="position: absolute; top: 10px; right: 10px; z-index: 10; background: rgba(239, 68, 68, 0.9); color: white; border: none; border-radius: 50%; width: 32px; height: 32px; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 16px; transition: all 0.2s ease; box-shadow: 0 2px 8px rgba(0,0,0,0.2);" onmouseover="this.style.background='rgba(220, 38, 38, 1)'; this.style.transform='scale(1.1)'" onmouseout="this.style.background='rgba(239, 68, 68, 0.9)'; this.style.transform='scale(1)'" title="Delete Story">🗑️</button>
                
                <!-- Cover Image -->
                <div onclick="viewStory(${story.id})" style="width: 100%; height: 250px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); position: relative; overflow: hidden;">
                    <img src="${coverImage}" alt="${story.title}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.style.display='none'; this.parentElement.innerHTML='<div style=\\'display: flex; align-items: center; justify-content: center; height: 100%; font-size: 3rem;\\'>📚</div>'">
                    <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(to bottom, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.3) 100%);"></div>
                </div>
                
                <!-- Story Info -->
                <div onclick="viewStory(${story.id})" style="padding: 15px;">
                    <h4 style="font-size: 1rem; color: #1f2937; margin: 0 0 8px 0; font-weight: 600; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">${story.title}</h4>
                    <p style="font-size: 0.85rem; color: #6b7280; margin: 0 0 5px 0;">by ${story.name}</p>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                        <span style="font-size: 0.75rem; color: #9ca3af; text-transform: capitalize;">${story.theme}</span>
                        <div style="display: flex; align-items: center; gap: 4px;">
                            ${story.rating ? `<span style="font-size: 0.78rem; color: #fbbf24; letter-spacing: 1px;">${'★'.repeat(story.rating)}${'☆'.repeat(5 - story.rating)}</span>` : `<span style="font-size: 0.72rem; color: #d1d5db;">Not rated</span>`}
                        </div>
                    </div>
                    <div style="font-size: 0.72rem; color: #9ca3af; margin-top: 4px; text-align: right;">${date}</div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    storiesList.innerHTML = html;
}

// Delete a story from the gallery
async function deleteStory(storyId) {
    // Confirm deletion
    if (!confirm('Are you sure you want to delete this story? This action cannot be undone.')) {
        return;
    }
    
    try {
        console.log('🗑️ Attempting to delete story ID:', storyId);
        showCharacterMessage("🗑️ Deleting story...");
        
        const response = await fetch(`${API_BASE_URL}/stories/${storyId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        console.log('📡 Delete response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ Delete failed with status:', response.status, 'Error:', errorText);
            throw new Error(`Failed to delete story: ${response.status} - ${errorText}`);
        }
        
        const result = await response.json();
        console.log('✅ Delete result:', result);
        
        // Show success message
        showCharacterMessage("✅ Story deleted successfully!");
        
        // Reload the gallery to reflect changes
        setTimeout(() => {
            loadRecentStories();
            hideCharacterMessage();
        }, 1500);
        
        console.log('✅ Story deleted:', storyId);
        
    } catch (error) {
        console.error('❌ Error deleting story:', error);
        console.error('❌ Error details:', error.message);
        showCharacterMessage("❌ Failed to delete story. Please try again.");
        setTimeout(hideCharacterMessage, 3000);
    }
}

// View a specific story
async function viewStory(storyId) {
    try {
        showCharacterMessage("📖 Loading your story...");
        
        const response = await fetch(`${API_BASE_URL}/stories/${storyId}`);
        if (!response.ok) {
            throw new Error('Failed to load story');
        }
        
        const storyData = await response.json();
        storyData.story_id = storyId;
        window.currentStoryData = storyData;
        window._storyViewSource = 'gallery';
        
        // Update reading streak
        computeStreak();
        
        showSection('storyView');
        
        setTimeout(() => {
            displayStoryInView(storyData);
            hideCharacterMessage();
        }, 100);
        
    } catch (error) {
        console.error('Error loading story:', error);
        showCharacterMessage("❌ Error loading story. Please try again.");
        setTimeout(() => hideCharacterMessage(), 2000);
    }
}

// Open story modal
function openStoryModal(storyData) {
    const modal = document.getElementById('storyModal');
    const modalTitle = document.getElementById('modalStoryTitle');
    const modalText = document.getElementById('modalStoryText');
    
    if (!modal || !modalTitle || !modalText) return;
    
    // Set story content
    modalTitle.textContent = storyData.title;
    
    let formattedStory = '';
    storyData.pages.forEach(page => {
        formattedStory += `<div class="story-page-modal">`;
        formattedStory += `<h4>Page ${page.page_number}</h4>`;
        formattedStory += `<p>${page.text}</p>`;
        formattedStory += `</div>`;
    });
    
    modalText.innerHTML = formattedStory;
    
    // Show modal
    modal.classList.remove('hidden');
    
    // Prevent body scroll
    document.body.style.overflow = 'hidden';
}

// Close story modal
function closeStoryModal() {
    const modal = document.getElementById('storyModal');
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
    }
}

// Character helper functions
function showCharacterMessage(message) {
    console.log('🦉 showCharacterMessage called with:', message);
    
    const container = document.getElementById('characterContainer');
    const messageEl = document.getElementById('characterMessage');
    
    console.log('🦉 Elements found:', {
        container: !!container,
        messageEl: !!messageEl,
        containerClasses: container ? container.className : 'not found',
        containerStyle: container ? container.style.cssText : 'not found'
    });
    
    if (container && messageEl) {
        messageEl.textContent = message;
        container.classList.remove('hidden');
        
        // Force visibility
        container.style.display = 'flex';
        container.style.opacity = '1';
        container.style.transform = 'translateY(0)';
        container.style.zIndex = '9999';
        
        console.log('🦉 Owl should be visible now!');
        console.log('🦉 Container classes after show:', container.className);
    } else {
        console.error('🦉 Could not find owl elements!');
    }
}

function hideCharacterMessage() {
    console.log('🦉 hideCharacterMessage called');
    
    const container = document.getElementById('characterContainer');
    if (container) {
        container.classList.add('hidden');
        console.log('🦉 Owl hidden');
    }
}

// Mobile menu toggle
function toggleMenu() {
    const nav = document.querySelector('nav');
    if (nav) {
        nav.classList.toggle('mobile-active');
    }
}

// Placeholder functions for features not implemented in backend
function markAsFavorite(button) {
    showToast('Favorites coming soon!', 'info');
}

function shareStory() {
    if (currentStory) {
        const shareText = `Check out this amazing story: "${currentStory.title}"`;
        if (navigator.share) {
            navigator.share({
                title: currentStory.title,
                text: shareText,
                url: window.location.href
            });
        } else {
            // Fallback - copy to clipboard
            navigator.clipboard.writeText(shareText + '\n\n' + window.location.href);
            showToast('Story link copied!', 'success');
        }
    }
}

function showMainAppView() {
    showSection('gallery');
}

// Close modal when clicking outside
document.addEventListener('click', function(e) {
    const modal = document.getElementById('storyModal');
    if (e.target === modal) {
        closeStoryModal();
    }
});

// Close modal with Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeStoryModal();
    }
    
    // Arrow key navigation for book pages
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        // Only navigate if we're viewing a story
        if (totalPages > 0 && !isAnimating) {
            nextPage();
        }
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        // Only navigate if we're viewing a story
        if (totalPages > 0 && !isAnimating) {
            previousPage();
        }
    }
});

// ============================================
// ============================================
// TEXT-TO-SPEECH ENGINE (Web Speech API)
// ============================================
let ttsUtterance = null;
let ttsActive = false;
let ttsPaused = false;
let autoReadMode = false;
let ttsAllVoices = [];
let ttsRate = 0.9;
let ttsSelectedVoice = null;
let currentPreset = 'us';
let currentPitch = 1.0;

const VOICE_PRESETS = {
    us:   { langs: ['en-US'], keywords: ['aria','jenny','guy','zira','david','mark'], pitch: 1.0  },
    uk:   { langs: ['en-GB'], keywords: ['hazel','george','susan','ryan','sonia'],    pitch: 1.0  },
    in:   { langs: ['en-IN'], keywords: ['heera','ravi','neerja'],                    pitch: 1.05 },
    au:   { langs: ['en-AU'], keywords: ['catherine','james','karen'],                pitch: 1.0  },
    kids: { langs: ['en-US','en-GB'], keywords: [],                                   pitch: 1.4  },
};

function loadVoices() {
    ttsAllVoices = window.speechSynthesis.getVoices();
    applyVoicePreset(currentPreset);
}

if (window.speechSynthesis) {
    window.speechSynthesis.onvoiceschanged = loadVoices;
    loadVoices();
}

function selectVoicePreset(preset) {
    currentPreset = preset;
    document.querySelectorAll('.vpill').forEach(p => {
        p.style.background = 'rgba(255,255,255,0.07)';
        p.style.color = '#c4b5fd';
        p.style.borderColor = 'rgba(255,255,255,0.2)';
    });
    const active = document.getElementById('vpill-' + preset);
    if (active) { active.style.background = '#6366f1'; active.style.color = 'white'; active.style.borderColor = '#6366f1'; }
    applyVoicePreset(preset);
}

function applyVoicePreset(preset) {
    const cfg = VOICE_PRESETS[preset];
    if (!cfg) return;
    currentPitch = cfg.pitch;
    let voice = null;
    for (const lang of cfg.langs) {
        for (const kw of cfg.keywords) {
            voice = ttsAllVoices.find(v => v.lang.startsWith(lang) && v.name.toLowerCase().includes(kw));
            if (voice) break;
        }
        if (voice) break;
    }
    if (!voice) {
        for (const lang of cfg.langs) {
            voice = ttsAllVoices.find(v => v.lang.startsWith(lang));
            if (voice) break;
        }
    }
    if (!voice) voice = ttsAllVoices.find(v => v.lang.startsWith('en'));
    ttsSelectedVoice = voice || null;
}

function selectSpeed(rate, btn) {
    ttsRate = rate;
    ['spd-slow','spd-normal','spd-fast'].forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        el.style.background = 'rgba(255,255,255,0.07)';
        el.style.color = '#c4b5fd';
    });
    if (btn) {
        btn.style.background = '#6366f1';
        btn.style.color = 'white';
    }
}

function getCurrentPageText() {
    if (currentPage === 0) {
        const title = window.currentStoryData?.title || '';
        return `${title}. A Magical Story.`;
    }
    const pageEl = document.getElementById(`page${currentPage}`);
    if (!pageEl) return '';
    let text = pageEl.innerText || pageEl.textContent || '';
    text = text.replace(/[\u{1F300}-\u{1FAFF}]/gu, '');
    text = text.replace(/\s+/g, ' ').trim();
    return text;
}

function toggleReadAloud() {
    if (!window.speechSynthesis) {
        showToast('TTS not supported. Try Chrome or Edge.', 'warning');
        return;
    }
    if (ttsActive && !ttsPaused) {
        window.speechSynthesis.pause();
        ttsPaused = true;
        updateTTSButton('paused');
        return;
    }
    if (ttsActive && ttsPaused) {
        window.speechSynthesis.resume();
        ttsPaused = false;
        updateTTSButton('playing');
        return;
    }
    speakCurrentPage();
}

function speakCurrentPage() {
    stopReadAloud();
    updateTTSButton('preparing');
    const text = getCurrentPageText();
    if (!text.trim()) { updateTTSButton('idle'); return; }
    setTimeout(() => {
        ttsUtterance = new SpeechSynthesisUtterance(text);
        ttsUtterance.rate   = ttsRate;
        ttsUtterance.pitch  = currentPitch;
        ttsUtterance.volume = 1;
        if (ttsSelectedVoice) ttsUtterance.voice = ttsSelectedVoice;
        ttsUtterance.onstart = () => { ttsActive = true;  ttsPaused = false; updateTTSButton('playing'); };
        ttsUtterance.onend   = () => {
            ttsActive = false; ttsPaused = false; updateTTSButton('idle');
            if (autoReadMode && currentPage < totalPages) {
                // small pause before flipping so it feels natural
                setTimeout(() => {
                    nextPage();
                    setTimeout(() => speakCurrentPage(), 800);
                }, 600);
            }
        };
        ttsUtterance.onerror = () => { ttsActive = false; ttsPaused = false; updateTTSButton('idle'); };
        window.speechSynthesis.speak(ttsUtterance);
    }, 150);
}

function stopReadAloud() {
    window.speechSynthesis.cancel();
    ttsActive = false;
    ttsPaused = false;
    updateTTSButton('idle');
}

function toggleAudioSettings() {
    const panel = document.getElementById('audioSettingsPanel');
    if (!panel) return;
    const isOpen = panel.style.maxHeight !== '0px' && panel.style.maxHeight !== '';
    if (isOpen) {
        panel.style.maxHeight = '0';
        panel.style.opacity = '0';
    } else {
        panel.style.maxHeight = '200px';
        panel.style.opacity = '1';
    }
}

function toggleAutoRead() {
    autoReadMode = !autoReadMode;
    const btn = document.getElementById('autoReadBtn');
    if (!btn) return;
    if (autoReadMode) {
        btn.style.background = '#6366f1';
        btn.style.color = 'white';
        btn.style.borderColor = '#6366f1';
        btn.title = 'Auto-read ON — pages turn automatically';
    } else {
        btn.style.background = 'rgba(255,255,255,0.08)';
        btn.style.color = '#a5b4fc';
        btn.style.borderColor = 'rgba(255,255,255,0.15)';
        btn.title = 'Auto-read OFF';
    }
}

function updateTTSButton(state) {
    const btn = document.getElementById('readAloudBtn');
    const statusEl = document.getElementById('audioStatus');
    const map = {
        idle:      { icon: '🔊', label: 'Read Aloud', status: 'Press play to listen',   bg: 'linear-gradient(135deg,#6366f1,#4f46e5)', shadow: 'rgba(99,102,241,0.5)' },
        preparing: { icon: '⏳', label: 'Preparing…',  status: 'Loading voice…',          bg: 'linear-gradient(135deg,#8b5cf6,#7c3aed)', shadow: 'rgba(139,92,246,0.5)' },
        playing:   { icon: '⏸', label: 'Pause',        status: 'Now reading…',            bg: 'linear-gradient(135deg,#f59e0b,#d97706)', shadow: 'rgba(245,158,11,0.5)'  },
        paused:    { icon: '▶️', label: 'Resume',       status: 'Paused — tap to resume',  bg: 'linear-gradient(135deg,#10b981,#059669)', shadow: 'rgba(16,185,129,0.5)'  },
    };
    const s = map[state] || map.idle;
    if (btn) {
        btn.innerHTML = `<span style="font-size:1.3rem">${s.icon}</span>`;
        btn.style.background = s.bg;
        btn.style.boxShadow  = `0 4px 14px ${s.shadow}`;
    }
    if (statusEl) statusEl.textContent = s.status;
}

// Picture Book Navigation Functions
let currentPage = 0; // 0 = cover, 1+ = story pages
let totalPages = 0;
let isAnimating = false; // Prevent rapid clicks during animation

function startReading() {
    console.log('📖 START READING clicked!');
    showCharacterMessage("📚 Great choice! Let's start this amazing adventure together!");
    
    setTimeout(() => {
        hideCharacterMessage();
    }, 3000);
    
    totalPages = window.currentStoryData ? window.currentStoryData.pages.length : 0;
    
    // Get cover and first page
    const coverPage = document.getElementById('coverPage');
    const firstPage = document.getElementById('page1');
    
    if (coverPage && firstPage) {
        // Animate cover page flip out
        coverPage.style.animation = 'pageFlipOut 0.6s ease-in-out';
        
        setTimeout(() => {
            // Hide cover
            coverPage.style.display = 'none';
            coverPage.style.animation = '';
            
            // Show first page with flip in animation
            currentPage = 1;
            firstPage.style.display = 'flex';
            firstPage.style.animation = 'pageFlipIn 0.6s ease-in-out';
            
            // Update navigation
            updateNavigation();
            
            setTimeout(() => {
                firstPage.style.animation = '';
            }, 600);
        }, 600);
    }
    
    console.log('✅ Started reading - showing page 1');
}

function nextPage() {
    // Prevent multiple clicks during animation
    if (isAnimating) {
        console.log('Animation in progress, ignoring click');
        return;
    }
    
    // Check bounds
    if (currentPage >= totalPages) {
        console.log('Already at last page');
        return;
    }
    
    // Get current and next page elements
    const currentPageEl = document.getElementById(currentPage === 0 ? 'coverPage' : `page${currentPage}`);
    const nextPageEl = document.getElementById(`page${currentPage + 1}`);
    
    if (!currentPageEl || !nextPageEl) {
        console.error('Page elements not found');
        return;
    }
    
    // Set animating flag
    isAnimating = true;
    console.log('Starting next page animation');
    
    // Disable buttons during animation
    updateNavigation();
    
    // Add page flip out animation to current page
    currentPageEl.style.animation = 'pageFlipOut 0.6s ease-in-out';
    
    setTimeout(() => {
        // Hide current page
        currentPageEl.style.display = 'none';
        currentPageEl.style.animation = '';
        
        // Show next page with flip in animation
        currentPage++;
        nextPageEl.style.display = 'flex';
        nextPageEl.style.animation = 'pageFlipIn 0.6s ease-in-out';
        
        setTimeout(() => {
            nextPageEl.style.animation = '';
            isAnimating = false; // Reset flag after FULL animation completes
            updateNavigation(); // Re-enable buttons after animation
            console.log('Animation complete, buttons re-enabled');
        }, 600);
    }, 600);
}

function previousPage() {
    // Prevent multiple clicks during animation
    if (isAnimating) {
        console.log('Animation in progress, ignoring click');
        return;
    }
    
    // Check bounds
    if (currentPage <= 0) {
        console.log('Already at first page');
        return;
    }
    
    // Get current and previous page elements
    const currentPageEl = document.getElementById(currentPage === 0 ? 'coverPage' : `page${currentPage}`);
    const prevPageEl = document.getElementById(currentPage - 1 === 0 ? 'coverPage' : `page${currentPage - 1}`);
    
    if (!currentPageEl || !prevPageEl) {
        console.error('Page elements not found');
        return;
    }
    
    // Set animating flag
    isAnimating = true;
    console.log('Starting previous page animation');
    
    // Disable buttons during animation
    updateNavigation();
    
    // Add page flip back animation to current page
    currentPageEl.style.animation = 'pageFlipBackOut 0.6s ease-in-out';
    
    setTimeout(() => {
        // Hide current page
        currentPageEl.style.display = 'none';
        currentPageEl.style.animation = '';
        
        // Show previous page with flip back in animation
        currentPage--;
        prevPageEl.style.display = 'flex';
        prevPageEl.style.animation = 'pageFlipBackIn 0.6s ease-in-out';
        
        setTimeout(() => {
            prevPageEl.style.animation = '';
            isAnimating = false; // Reset flag after FULL animation completes
            updateNavigation(); // Re-enable buttons after animation
            console.log('Animation complete, buttons re-enabled');
        }, 600);
    }, 600);
}

function updateNavigation() {
    // Stop TTS when page changes manually (not during auto-read)
    if (!autoReadMode) stopReadAloud();

    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const dots = document.querySelectorAll('.page-dot');
    
    // Validate current page is within bounds
    if (currentPage < 0) currentPage = 0;
    if (currentPage > totalPages) currentPage = totalPages;
    
    // Update prev button
    if (prevBtn) {
        if (currentPage === 0 || isAnimating) {
            prevBtn.disabled = true;
            prevBtn.style.opacity = '0.5';
            prevBtn.style.cursor = 'not-allowed';
        } else {
            prevBtn.disabled = false;
            prevBtn.style.opacity = '1';
            prevBtn.style.cursor = 'pointer';
        }
    }
    
    // Update next button
    if (nextBtn) {
        if (currentPage >= totalPages || isAnimating) {
            nextBtn.disabled = true;
            nextBtn.style.opacity = '0.5';
            nextBtn.style.cursor = 'not-allowed';
        } else {
            nextBtn.disabled = false;
            nextBtn.style.opacity = '1';
            nextBtn.style.cursor = 'pointer';
        }
    }
    
    // Update page indicators
    if (dots && dots.length > 0) {
        dots.forEach((dot, index) => {
            if (index === currentPage) {
                dot.style.width = '10px';
                dot.style.height = '10px';
                dot.style.background = '#667eea';
                dot.style.transform = 'scale(1.2)';
                dot.style.boxShadow = '0 0 8px rgba(102,126,234,0.6)';
            } else {
                dot.style.width = '8px';
                dot.style.height = '8px';
                dot.style.background = '#ccc';
                dot.style.transform = 'scale(1)';
                dot.style.boxShadow = 'none';
            }
        });
    }

    // Update progress bar
    const bar = document.getElementById('storyProgressBar');
    if (bar && totalPages > 0) {
        const pct = currentPage === 0 ? 0 : Math.round((currentPage / totalPages) * 100);
        bar.style.width = pct + '%';
    }
}

// Favorite functionality - DATABASE VERSION
async function toggleFavorite() {
    console.log('💖 Toggle favorite clicked');
    console.log('📌 Current story data:', window.currentStoryData);
    
    if (!window.currentStoryData) {
        console.error('❌ No currentStoryData found!');
        showCharacterMessage("⚠️ Please generate a story first!");
        setTimeout(() => hideCharacterMessage(), 3000);
        return;
    }
    
    if (!window.currentStoryData.story_id) {
        console.error('❌ No story_id found in currentStoryData!');
        console.error('Available keys:', Object.keys(window.currentStoryData));
        showCharacterMessage("⚠️ Story was not saved properly. Please generate a new story.");
        setTimeout(() => hideCharacterMessage(), 3000);
        return;
    }
    
    try {
        const storyId = window.currentStoryData.story_id;
        console.log('📤 Sending favorite request for story ID:', storyId);
        
        const response = await fetch(`${API_BASE_URL}/stories/${storyId}/favorite`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ Server error:', errorText);
            throw new Error('Failed to toggle favorite');
        }
        
        const data = await response.json();
        console.log('✅ Favorite response:', data);
        
        // Store the favorite status
        window.currentStoryData.is_favorite = data.is_favorite;
        
        if (data.is_favorite) {
            showCharacterMessage("❤️ Added to favorites!");
        } else {
            showCharacterMessage("💔 Removed from favorites");
        }
        
        await updateFavoriteButton();
        
        setTimeout(() => {
            hideCharacterMessage();
        }, 2000);
        
    } catch (error) {
        console.error('❌ Error toggling favorite:', error);
        showCharacterMessage("⚠️ Error updating favorite. Check console for details.");
        setTimeout(() => hideCharacterMessage(), 3000);
    }
}

async function updateFavoriteButton() {
    const favoriteBtn = document.getElementById('favoriteBtn');
    const favoriteIcon = document.getElementById('favoriteIcon');
    const favoriteText = document.getElementById('favoriteText');
    
    if (!favoriteBtn || !favoriteIcon || !favoriteText) {
        console.log('⚠️ Favorite button elements not found');
        return;
    }
    
    console.log('🔄 Updating favorite button...');
    console.log('📌 Current story data:', window.currentStoryData);
    
    // Check if story has been saved and has an ID
    if (!window.currentStoryData || !window.currentStoryData.story_id) {
        console.log('⚠️ No story_id - showing default state');
        // Show default state - ready to favorite
        favoriteIcon.textContent = '🤍';
        favoriteText.textContent = 'Add to Favorites';
        favoriteBtn.style.background = 'linear-gradient(135deg, #ec4899 0%, #be185d 100%)';
        favoriteBtn.style.borderColor = '#be185d';
        favoriteBtn.style.color = 'white';
        favoriteBtn.style.cursor = 'pointer';
        favoriteBtn.style.opacity = '1';
        return;
    }
    
    try {
        // Fetch current favorite status from database
        const storyId = window.currentStoryData.story_id;
        console.log('📤 Fetching favorite status for story ID:', storyId);
        
        const response = await fetch(`${API_BASE_URL}/stories/${storyId}`);
        
        if (response.ok) {
            const storyData = await response.json();
            const isFavorite = storyData.is_favorite || false;
            
            console.log('✅ Favorite status:', isFavorite);
            
            if (isFavorite) {
                // Already favorited - show red filled heart
                favoriteIcon.textContent = '❤️';
                favoriteText.textContent = 'Favorited!';
                favoriteBtn.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
                favoriteBtn.style.borderColor = '#dc2626';
                favoriteBtn.style.color = 'white';
                favoriteBtn.style.cursor = 'pointer';
                favoriteBtn.style.opacity = '1';
                favoriteBtn.style.boxShadow = '0 4px 12px rgba(239,68,68,0.4)';
            } else {
                // Not favorited - show white heart
                favoriteIcon.textContent = '🤍';
                favoriteText.textContent = 'Add to Favorites';
                favoriteBtn.style.background = 'linear-gradient(135deg, #ec4899 0%, #be185d 100%)';
                favoriteBtn.style.borderColor = '#be185d';
                favoriteBtn.style.color = 'white';
                favoriteBtn.style.cursor = 'pointer';
                favoriteBtn.style.opacity = '1';
                favoriteBtn.style.boxShadow = '0 4px 12px rgba(236,72,153,0.4)';
            }
        } else {
            console.error('❌ Failed to fetch story:', response.status);
        }
    } catch (error) {
        console.error('❌ Error checking favorite status:', error);
        // Default to not favorited
        favoriteIcon.textContent = '🤍';
        favoriteText.textContent = 'Add to Favorites';
        favoriteBtn.style.background = 'linear-gradient(135deg, #ec4899 0%, #be185d 100%)';
        favoriteBtn.style.borderColor = '#be185d';
        favoriteBtn.style.color = 'white';
        favoriteBtn.style.cursor = 'pointer';
        favoriteBtn.style.opacity = '1';
        favoriteBtn.style.boxShadow = '0 4px 12px rgba(236,72,153,0.4)';
    }
}

function getFavorites() {
    const favoritesJson = localStorage.getItem('favoriteStories');
    return favoritesJson ? JSON.parse(favoritesJson) : [];
}

function generateStoryId(storyData) {
    // Generate a unique ID based on title and first page text
    const str = storyData.title + (storyData.pages[0]?.text || '');
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }
    return 'story_' + Math.abs(hash);
}

// Show favorites from DATABASE
async function showFavorites() {
    try {
        const response = await fetch(`${API_BASE_URL}/favorites`);
        if (!response.ok) {
            throw new Error('Failed to load favorites');
        }
        
        const data = await response.json();
        const favorites = data.favorites;
        
        if (favorites.length === 0) {
            showCharacterMessage("💔 No favorites yet! Click the heart button on stories you love.");
            setTimeout(() => hideCharacterMessage(), 3000);
            return;
        }
        
        // Create beautiful favorites modal with purple gradient theme
        let favoritesHTML = `
            <div id="favoritesModal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 20px; overflow-y: auto;" onclick="closeFavoritesModal(event)">
                <!-- Sparkles background -->
                <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;">
                    <div style="position: absolute; width: 3px; height: 3px; background: white; border-radius: 50%; top: 10%; left: 20%; animation: twinkle 2s infinite;"></div>
                    <div style="position: absolute; width: 2px; height: 2px; background: white; border-radius: 50%; top: 30%; left: 80%; animation: twinkle 3s infinite;"></div>
                    <div style="position: absolute; width: 3px; height: 3px; background: white; border-radius: 50%; top: 60%; left: 10%; animation: twinkle 2.5s infinite;"></div>
                    <div style="position: absolute; width: 2px; height: 2px; background: white; border-radius: 50%; top: 80%; left: 70%; animation: twinkle 3.5s infinite;"></div>
                    <div style="position: absolute; width: 3px; height: 3px; background: white; border-radius: 50%; top: 20%; left: 50%; animation: twinkle 2.8s infinite;"></div>
                </div>
                
                <div style="background: rgba(255, 255, 255, 0.95); border-radius: 30px; padding: 40px; max-width: 900px; width: 100%; max-height: 85vh; overflow-y: auto; position: relative; box-shadow: 0 30px 80px rgba(0,0,0,0.4);" onclick="event.stopPropagation()">
                    <button onclick="closeFavoritesModal()" style="position: absolute; top: 20px; right: 20px; background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; border: none; width: 45px; height: 45px; border-radius: 50%; cursor: pointer; font-size: 1.5rem; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(239,68,68,0.4); transition: all 0.3s ease; font-weight: bold;">×</button>
                    
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h2 style="font-family: 'Caveat', cursive; font-size: 3rem; background: linear-gradient(135deg, #ec4899 0%, #be185d 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 10px;">❤️ Your Favorite Stories</h2>
                        <p style="color: #6b7280; font-size: 1.1rem;">${favorites.length} ${favorites.length === 1 ? 'story' : 'stories'} you love</p>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 25px;">
                        ${favorites.map(fav => {
                            // Known theme list
                            const knownThemes = ['adventure', 'fantasy', 'friendship', 'animals', 'space', 'ocean'];
                            const isCustomTheme = fav.isCustomTheme || !knownThemes.includes(fav.theme.toLowerCase());
                            
                            // Use saved cover number for custom themes
                            let coverImage;
                            if (isCustomTheme) {
                                const coverNum = fav.customCoverNumber || 1;
                                coverImage = `img/covers/custom-${coverNum}.png`;
                            } else {
                                coverImage = `img/covers/${fav.theme}-1.png`;
                            }
                            
                            return `
                            <div onclick='loadFavoriteStory("${fav.id}")' style="cursor: pointer; background: white; border-radius: 20px; overflow: hidden; box-shadow: 0 8px 25px rgba(0,0,0,0.2); transition: all 0.3s ease; position: relative;" onmouseover="this.style.transform='translateY(-8px) scale(1.02)'; this.style.boxShadow='0 15px 40px rgba(0,0,0,0.3)'" onmouseout="this.style.transform='translateY(0) scale(1)'; this.style.boxShadow='0 8px 25px rgba(0,0,0,0.2)'">
                                <!-- Cover Image -->
                                <div style="width: 100%; height: 280px; background: linear-gradient(135deg, #ec4899 0%, #be185d 100%); position: relative; overflow: hidden;">
                                    <img src="${coverImage}" alt="${fav.title}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.style.display='none'; this.parentElement.innerHTML='<div style=\\'display: flex; align-items: center; justify-content: center; height: 100%; font-size: 4rem;\\'>❤️</div>'">
                                    <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(to bottom, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.4) 100%);"></div>
                                    <!-- Favorite Badge -->
                                    <div style="position: absolute; top: 12px; right: 12px; background: rgba(239,68,68,0.95); color: white; padding: 6px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: bold; display: flex; align-items: center; gap: 5px; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
                                        <span>❤️</span>
                                        <span>Favorite</span>
                                    </div>
                                </div>
                                
                                <!-- Story Info -->
                                <div style="padding: 20px;">
                                    <h3 style="font-family: 'Caveat', cursive; font-size: 1.5rem; color: #1f2937; margin: 0 0 10px 0; font-weight: 600; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">${fav.title}</h3>
                                    
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                                        <span style="font-size: 0.85rem; color: #6b7280; text-transform: capitalize; background: #f3f4f6; padding: 4px 10px; border-radius: 12px; font-weight: 500;">${fav.theme}</span>
                                        <span style="font-size: 0.8rem; color: #9ca3af;">${new Date(fav.dateAdded).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                                    </div>
                                    
                                    <div style="display: flex; gap: 8px; margin-top: 15px;">
                                        <button onclick='event.stopPropagation(); loadFavoriteStory("${fav.id}")' style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; border: none; padding: 10px 16px; border-radius: 20px; cursor: pointer; font-weight: bold; flex: 1; font-size: 0.9rem; box-shadow: 0 4px 12px rgba(16,185,129,0.3); transition: all 0.3s ease; display: flex; align-items: center; justify-content: center; gap: 5px;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                            <span>📖</span>
                                            <span>Read</span>
                                        </button>
                                        <button onclick='event.stopPropagation(); removeFavorite("${fav.id}")' style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; border: none; padding: 10px 16px; border-radius: 20px; cursor: pointer; font-weight: bold; box-shadow: 0 4px 12px rgba(239,68,68,0.3); transition: all 0.3s ease; display: flex; align-items: center; justify-content: center;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                            <span style="font-size: 1.1rem;">🗑️</span>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        `}).join('')}
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', favoritesHTML);
        
    } catch (error) {
        console.error('Error loading favorites:', error);
        showCharacterMessage("⚠️ Error loading favorites");
        setTimeout(() => hideCharacterMessage(), 2000);
    }
}

function closeFavoritesModal(event) {
    if (!event || event.target.id === 'favoritesModal') {
        const modal = document.getElementById('favoritesModal');
        if (modal) modal.remove();
    }
}

// Load favorite story from database
async function loadFavoriteStory(storyId) {
    try {
        console.log('📖 Loading favorite story:', storyId);
        
        // Close the favorites modal
        closeFavoritesModal();
        
        // Fetch the story
        const response = await fetch(`${API_BASE_URL}/stories/${storyId}`);
        if (!response.ok) {
            throw new Error('Failed to load story');
        }
        
        const storyData = await response.json();
        storyData.story_id = storyId;
        
        console.log('✅ Story loaded:', storyData.title);
        
        // Set as current story
        window.currentStoryData = storyData;
        window._storyViewSource = 'favoritesModal';
        
        // Navigate to storyView section
        console.log('🔄 Navigating to storyView section');
        showSection('storyView');
        
        // Wait a moment for section to be visible, then display story
        setTimeout(() => {
            console.log('📚 Calling displayStoryInView');
            displayStoryInView(storyData);
        }, 300);
        
    } catch (error) {
        console.error('❌ Error loading favorite story:', error);
        showCharacterMessage("⚠️ Error loading story: " + error.message);
        setTimeout(() => hideCharacterMessage(), 3000);
    }
}

async function removeFavorite(storyId) {
    try {
        const response = await fetch(`${API_BASE_URL}/stories/${storyId}/favorite`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('Failed to remove favorite');
        }
        
        // Refresh the modal
        closeFavoritesModal();
        showFavorites();
        
        showCharacterMessage("💔 Removed from favorites");
        setTimeout(() => hideCharacterMessage(), 2000);
        
    } catch (error) {
        console.error('Error removing favorite:', error);
        showCharacterMessage("⚠️ Error removing favorite");
        setTimeout(() => hideCharacterMessage(), 2000);
    }
}

// Image generation removed - clean text-only experience

// Debug function to test connection
async function testConnection() {
    const debugResult = document.getElementById('debugResult');
    debugResult.style.display = 'block';
    debugResult.innerHTML = 'Testing connection...';
    debugResult.style.color = 'blue';
    
    try {
        console.log('🔧 Testing connection to:', API_BASE_URL);
        
        // Test basic API endpoint
        const response = await fetch(`${API_BASE_URL}/debug-cors`, {
            method: 'GET',
            mode: 'cors'
        });
        
        console.log('📡 Debug response:', response.status, response.statusText);
        
        if (response.ok) {
            const data = await response.json();
            debugResult.innerHTML = `✅ Connection OK: ${JSON.stringify(data)}`;
            debugResult.style.color = 'green';
        } else {
            debugResult.innerHTML = `❌ Connection failed: ${response.status} ${response.statusText}`;
            debugResult.style.color = 'red';
        }
    } catch (error) {
        console.error('❌ Debug test failed:', error);
        debugResult.innerHTML = `❌ Connection error: ${error.message}`;
        debugResult.style.color = 'red';
    }
}


// FAQ Toggle Function
function toggleFAQ(element) {
    console.log('🔄 FAQ clicked', element);
    
    try {
        const answer = element.querySelector('.faq-answer');
        if (!answer) {
            console.error('❌ FAQ answer not found');
            return;
        }
        
        // Find the icon span - it's the one with just + or - text
        const spans = element.querySelectorAll('span');
        let icon = null;
        for (let span of spans) {
            const text = span.textContent.trim();
            if (text === '+' || text === '−') {
                icon = span;
                break;
            }
        }
        
        if (!icon) {
            console.error('❌ FAQ icon not found');
            return;
        }
        
        // Toggle the answer
        if (answer.style.display === 'none' || answer.style.display === '') {
            answer.style.display = 'block';
            icon.textContent = '−';
            element.style.transform = 'scale(1.02)';
            console.log('✅ FAQ expanded');
        } else {
            answer.style.display = 'none';
            icon.textContent = '+';
            element.style.transform = 'scale(1)';
            console.log('✅ FAQ collapsed');
        }
    } catch (error) {
        console.error('❌ Error in toggleFAQ:', error);
    }
}

// Smooth scroll to How It Works section
function scrollToHowItWorks() {
    const section = document.getElementById('how-it-works');
    if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

