// js/script.js

// --- Load recent stories on page load ---
// --- Check login status and set initial UI on page load ---
// --- Check login status and set initial UI on page load ---
document.addEventListener('DOMContentLoaded', () => {
    const storedUsername = localStorage.getItem('username');
    if (storedUsername) {
        console.log('User already logged in:', storedUsername);
        updateUIForLoggedInUser(storedUsername);
        fetchRecentStories(); // Fetch stories only if logged in
        // Show welcome back message (disappears after 5 secs)
        showCharacterMessage(`Welcome back, ${storedUsername}! Ready for a story?`, 5000);
    } else {
        updateUIForLoggedOutUser(); // Show welcome page if not logged in
        // Show initial welcome message (disappears after 5 secs)
        showCharacterMessage("Hello! Click 'Get Started' to create or read stories!", 5000);
    }
});
// --- END INITIAL LOAD LOGIC ---
// --- END INITIAL LOAD LOGIC ---
// --- Get Started Button Logic ---
// --- Get Started Button Logic ---
const getStartedBtn = document.getElementById('getStartedBtn');
const heroSection = document.getElementById('home');

if (getStartedBtn && heroSection) {
    getStartedBtn.addEventListener('click', () => {
        console.log("Get Started clicked!");
        // Hide hero section using class
        heroSection.classList.add('section-hidden');
        // Show Register and Login sections using class
        document.getElementById('register')?.classList.remove('section-hidden');
        document.getElementById('login')?.classList.remove('section-hidden');
    });
} else {
    console.warn("Get Started button or Hero section not found.");
}

async function fetchRecentStories() {
    const listElement = document.getElementById('recent-stories-list');
    try {
        // --- URL UPDATED ---
        const response = await fetch('http://127.0.0.1:8000/stories/recent');

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail);
        }
        const data = await response.json();

        if (data.stories && data.stories.length > 0) {
            listElement.innerHTML = '';
            data.stories.forEach(story => {
                const storyEl = document.createElement('div');
                storyEl.style = "display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid #eee;";
                const contentDiv = document.createElement('div');
                contentDiv.innerHTML = `
                    <p style="font-weight: 600; color: #a855f7; margin-bottom: 0;">
                        📖 ${story.name} - <span>(${story.theme})</span>
                    </p>
                    <p style="font-size: 0.9rem; color: #5a4a6a; margin-bottom: 0;">
                        ${story.date}
                    </p>
                `;
                const viewButton = document.createElement('button');
                viewButton.innerText = 'View Story';
                viewButton.style = "padding: 5px 10px; font-size: 0.9rem; cursor: pointer; background-color: #a855f7; color: white; border: none; border-radius: 5px;";
                viewButton.onclick = () => openStoryModal(story);
                storyEl.appendChild(contentDiv);
                storyEl.appendChild(viewButton);
                listElement.appendChild(storyEl);
            });
        } else {
            listElement.innerHTML = '<p>No stories saved yet. Create one!</p>';
        }
    } catch (error) {
        console.error("Real database error:", error.message);
        listElement.innerHTML = `<p style="color: red; font-weight: bold;">Error: ${error.message}</p>`;
    }
}

// --- Script variables ---
let selectedTheme = '';
let isTyping = false;
let currentTimeout;
let currentStoryId = null;

// --- UI Functions ---
function toggleMenu() {
    const nav = document.getElementById('mainNav');
    nav.classList.toggle('mobile-active');
}

function selectTheme(element) {
    selectedTheme = element.dataset.theme;
    document.querySelectorAll('.theme-option').forEach(option => option.classList.remove('selected'));
    element.classList.add('selected');
    const customThemeGroup = document.getElementById('customThemeGroup');
    customThemeGroup.classList.toggle('hidden', selectedTheme !== 'custom');
    if (selectedTheme === 'custom') document.getElementById('customTheme').focus();
}

function typeWriter(story, storyTextElement, storyActions) {
    let i = 0;
    const favoriteButton = storyActions?.querySelector('.btn-primary');
    if (favoriteButton) {
        favoriteButton.innerText = 'Mark as Favorite ❤️';
        favoriteButton.disabled = false;
    }
    function type() {
        if (i < story.length) {
            storyTextElement.innerText += story.charAt(i);
            i++;
            currentTimeout = setTimeout(type, 15);
        } else {
            isTyping = false;
            if(storyActions) storyActions.classList.add('is-visible');
            setTimeout(fetchRecentStories, 500); // Call function directly
        }
    }
    type();
}

// --- Form Submissions ---
const storyForm = document.getElementById('storyForm');
const submitBtn = storyForm?.querySelector('button[type="submit"]'); // Add optional chaining

if (storyForm && submitBtn) {
   storyForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    if (isTyping) return;

    const name = document.getElementById('characterName').value.trim();
    const age = document.getElementById('characterAge').value.trim();
    const customTheme = document.getElementById('customTheme').value.trim();

    if (!selectedTheme) return alert('Please select a theme!');
    const theme = selectedTheme === 'custom' ? customTheme : selectedTheme;
    if (!theme) return alert('Please enter your custom theme!');

    isTyping = true;
    currentStoryId = null;
    submitBtn.classList.add('btn-loading');

    const storyTextElement = document.getElementById('storyText');
    const storyResultElement = document.getElementById('storyResult');
    const storyActions = storyResultElement?.querySelector('.story-actions');

    storyTextElement.innerText = '';
    clearTimeout(currentTimeout);
    if(storyActions) storyActions.classList.remove('is-visible');
    storyResultElement.classList.remove('hidden');
    storyResultElement.scrollIntoView({ behavior: 'smooth' });

    // --- NEW: Show character message ---
    showCharacterMessage(`Hold on tight, ${name}! We're creating your magical ${theme} story... ✨`);
    // --- END NEW ---

    try {
            // --- CORRECTED FETCH CALL ---
            const response = await fetch('http://127.0.0.1:8000/stories/generate', {
                method: 'POST', // <-- Make sure this is INSIDE the {}
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name, age: parseInt(age), theme: theme })
            }); // <-- The closing parenthesis ')' should be AFTER the body
            // --- END CORRECTION ---

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error ${response.status}`);
            }
            const data = await response.json();
            currentStoryId = data.story_id;
            console.log("--- DEBUG INFO FROM GOOGLE ---", data.debug_feedback);

            // --- Show success message via character ---
            showCharacterMessage("Your story is ready!", 3000);

            typeWriter(data.story, storyTextElement, storyActions);

        } catch (error) {
            console.error('Error fetching story:', error.message);
            storyTextElement.innerText = `Error: ${error.message}`;
            // --- Show error message via character ---
            showCharacterMessage(`Oops! Something went wrong: ${error.message}`, 5000);
        } finally {
            submitBtn.classList.remove('btn-loading');
            isTyping = false;
        }
});
} else {
    console.warn("Story form or submit button not found.");
}


const registerForm = document.getElementById('registerForm');
const registerMessage = document.getElementById('registerMessage');

if (registerForm && registerMessage) {
    registerForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const username = document.getElementById('regUsername').value.trim();
        const password = document.getElementById('regPassword').value.trim();
        registerMessage.innerText = '';
        registerMessage.className = '';

        if (!username || !password) {
            registerMessage.innerText = 'Please enter both username and password.';
            registerMessage.className = 'error'; return;
        }
        if (password.length < 8) {
            registerMessage.innerText = 'Password must be at least 8 characters long.';
            registerMessage.className = 'error'; return;
        }

        try {
            // --- URL UPDATED ---
            const response = await fetch('http://127.0.0.1:8000/users/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: username, password: password }),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || `HTTP error ${response.status}`);
            }
            console.log('Registration successful:', data);
            registerMessage.innerText = `User '${data.username}' registered successfully! You can now log in.`;
            registerMessage.className = 'success';
            registerForm.reset();
        } catch (error) {
            console.error('Registration error:', error.message);
            registerMessage.innerText = `Error: ${error.message}`;
            registerMessage.className = 'error';
        }
    });
} else {
    console.warn("Register form or message element not found.");
}
// --- NEW: Login Form Submission ---
const loginForm = document.getElementById('loginForm');
const loginMessage = document.getElementById('loginMessage');

if (loginForm && loginMessage) { // Check elements exist
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault(); // Stop default form submission

        const username = document.getElementById('loginUsername').value.trim();
        const password = document.getElementById('loginPassword').value.trim();

        // Clear previous messages
        loginMessage.innerText = '';
        loginMessage.className = '';

        if (!username || !password) {
            loginMessage.innerText = 'Please enter both username and password.';
            loginMessage.className = 'error';
            return;
        }

        try {
            // NOTE: FastAPI's OAuth2PasswordRequestForm expects form data, not JSON
            const formData = new URLSearchParams();
            formData.append('username', username);
            formData.append('password', password);

            const response = await fetch('http://127.0.0.1:8000/users/token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded', // Important header for form data
                },
                body: formData // Send as form data
            });

            const data = await response.json(); // Get JSON response (token or error detail)

            if (!response.ok) {
                // Use the detail message from backend (e.g., "Incorrect username or password")
                throw new Error(data.detail || `HTTP error! status: ${response.status}`);
            }

            // --- Login Success ---
            console.log('Login successful:', data);
            // Store the token (e.g., in localStorage for persistence)
            localStorage.setItem('accessToken', data.access_token);
            localStorage.setItem('tokenType', data.token_type);

            loginMessage.innerText = `Welcome back, ${username}! Login successful.`;
            loginMessage.className = 'success';
            loginForm.reset(); // Clear the form

            // TODO: Update UI to show logged-in state (e.g., hide forms, show user info)
            updateUIForLoggedInUser(username); // Call the function to show main app
            fetchRecentStories(); // Fetch stories after successful login


        } catch (error) {
            // --- Login Error ---
            console.error('Login error:', error.message);
            loginMessage.innerText = `Error: ${error.message}`;
            loginMessage.className = 'error';
            // Clear any stored token on login failure
            localStorage.removeItem('accessToken');
            localStorage.removeItem('tokenType');
        }
    });
} else {
    console.warn("Login form or message element not found.");
}
// --- END NEW LOGIN CODE ---

// --- NEW: UI Update Functions ---
// --- NEW: UI Update Functions ---
function updateUIForLoggedInUser(username) {
    // Hide sections using class
    document.getElementById('home')?.classList.add('section-hidden');
    document.getElementById('register')?.classList.add('section-hidden');
    document.getElementById('login')?.classList.add('section-hidden');
    document.getElementById('favorites')?.classList.add('section-hidden');

    // Show main app sections using class
    document.getElementById('create')?.classList.remove('section-hidden');
    document.getElementById('gallery')?.classList.remove('section-hidden');

    // Show Favorites button
    if (viewFavoritesBtn) viewFavoritesBtn.style.display = 'inline-block';

    // Show welcome message in header
    const userInfoDiv = document.getElementById('userInfo');
    if (userInfoDiv) {
        userInfoDiv.innerHTML = `Welcome, ${username}! <button onclick="logout()" class="btn btn-logout">Logout</button>`;
    }
}

function updateUIForLoggedOutUser() {
    // Hide main app sections
    document.getElementById('create')?.classList.add('section-hidden');
    document.getElementById('gallery')?.classList.add('section-hidden');
    document.getElementById('favorites')?.classList.add('section-hidden');
    document.getElementById('register')?.classList.add('section-hidden');
    document.getElementById('login')?.classList.add('section-hidden');

    // Show ONLY the hero section using class
    document.getElementById('home')?.classList.remove('section-hidden');

    // Clear welcome message & hide favorites button
    const userInfoDiv = document.getElementById('userInfo');
    if (userInfoDiv) userInfoDiv.innerHTML = '';
    if (viewFavoritesBtn) viewFavoritesBtn.style.display = 'none';
}
function logout() {
    // Clear stored token and username
    localStorage.removeItem('accessToken');
    localStorage.removeItem('tokenType');
    localStorage.removeItem('username');
    console.log('User logged out.');
    // Update UI back to logged-out state (show Hero)
    updateUIForLoggedOutUser();
    // Optionally: show a message on the login form
    const loginMessage = document.getElementById('loginMessage');
    if(loginMessage) {
        loginMessage.innerText = 'You have been logged out.';
        loginMessage.className = ''; // Clear success/error class
        // Ensure login form is visible after logout, if Get Started was clicked
        const loginSection = document.getElementById('login');
         if (loginSection && loginSection.style.display === 'none') {
            const registerSection = document.getElementById('register');
            if (registerSection) registerSection.style.display = 'block';
            loginSection.style.display = 'block';
         }
    }
}
// --- END NEW UI FUNCTIONS ---
// --- NEW: Character Control Functions ---
const characterContainer = document.getElementById('characterContainer');
const characterMessage = document.getElementById('characterMessage');
let characterHideTimeout = null; // To manage auto-hiding

function showCharacterMessage(message, duration = 0) {
    // Clear any previous auto-hide timer
    if (characterHideTimeout) {
        clearTimeout(characterHideTimeout);
        characterHideTimeout = null;
    }

    if (characterContainer && characterMessage) {
        characterMessage.innerText = message;
        characterContainer.classList.remove('hidden'); // Make it visible

        // Optional: Hide automatically after a duration (in milliseconds)
        if (duration > 0) {
            characterHideTimeout = setTimeout(hideCharacter, duration);
        }
    } else {
        console.warn("Character elements not found.");
    }
}

function hideCharacter() {
    if (characterHideTimeout) { // Clear timer if hiding manually
        clearTimeout(characterHideTimeout);
        characterHideTimeout = null;
    }
    if (characterContainer) {
        characterContainer.classList.add('hidden'); // Add hidden class to slide out
    }
}
// --- END NEW Character Control ---

function showFavoritesView() {
    // Hide Create and Gallery sections
    if (createSection) createSection.style.display = 'none';
    if (gallerySection) gallerySection.style.display = 'none';
    // Show Favorites section
    if (favoritesSection) favoritesSection.style.display = 'block';
    // Fetch and display the favorites
    fetchAndDisplayFavorites();
}

function showMainAppView() {
    // Hide Favorites section
    if (favoritesSection) favoritesSection.style.display = 'none';
    // Show Create and Gallery sections
    if (createSection) createSection.style.display = 'block';
    if (gallerySection) gallerySection.style.display = 'block';
    // Optionally fetch recent stories again if needed
    // fetchRecentStories();
}

async function fetchAndDisplayFavorites() {
    const listElement = document.getElementById('favorite-stories-list');
    if (!listElement) {
        console.error("Favorite stories list element not found!");
        return;
    }
    listElement.innerHTML = '<p>Loading favorites...</p>'; // Show loading message

    try {
        const response = await fetch('http://127.0.0.1:8000/stories/favorites'); // Call the new endpoint

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail);
        }
        const data = await response.json();

        if (data.stories && data.stories.length > 0) {
            listElement.innerHTML = ''; // Clear loading message
            data.stories.forEach(story => {
                const storyEl = document.createElement('div');
                // Use similar styling and button as recent stories
                storyEl.style = "display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid #eee;";
                const contentDiv = document.createElement('div');
                contentDiv.innerHTML = `
                    <p style="font-weight: 600; color: #a855f7; margin-bottom: 0;">
                        ❤️ ${story.name} - <span>(${story.theme})</span>
                    </p>
                    <p style="font-size: 0.9rem; color: #5a4a6a; margin-bottom: 0;">
                        ${story.date}
                    </p>
                `;
                const viewButton = document.createElement('button');
                viewButton.innerText = 'View Story';
                viewButton.style = "padding: 5px 10px; font-size: 0.9rem; cursor: pointer; background-color: #a855f7; color: white; border: none; border-radius: 5px;";
                viewButton.onclick = () => openStoryModal(story); // Reuse the same modal
                storyEl.appendChild(contentDiv);
                storyEl.appendChild(viewButton);
                listElement.appendChild(storyEl);
            });
        } else {
            listElement.innerHTML = '<p>You haven\'t marked any stories as favorites yet!</p>';
        }
    } catch (error) {
        console.error("Error fetching favorites:", error.message);
        listElement.innerHTML = `<p style="color: red; font-weight: bold;">Error: ${error.message}</p>`;
    }
}
// --- Story Actions ---
async function markAsFavorite(buttonElement) {
    if (!currentStoryId) return alert("Cannot favorite story: ID not found.");
    buttonElement.disabled = true;
    buttonElement.innerText = 'Saving...';
    try {
        // --- URL UPDATED ---
        const response = await fetch(`http://127.0.0.1:8000/stories/mark-favorite/${currentStoryId}`, {
            method: 'POST',
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error ${response.status}`);
        }
        const result = await response.json();
        console.log(result.message);
        buttonElement.innerText = 'Favorited! ❤️';
    } catch (error) {
        console.error('Error marking as favorite:', error.message);
        alert(`Could not mark as favorite: ${error.message}`);
        buttonElement.innerText = 'Mark as Favorite ❤️';
        buttonElement.disabled = false;
    }
}

function shareStory() {
    alert('Share functionality coming soon!');
}

// --- Modal Functions ---
function openStoryModal(story) {
    const modal = document.getElementById('storyModal');
    const modalTitle = document.getElementById('modalStoryTitle');
    const modalText = document.getElementById('modalStoryText');
    if (modal && modalTitle && modalText) {
        modalTitle.innerText = `${story.name} - (${story.theme})`;
        modalText.innerText = story.story_text;
        modal.classList.remove('hidden');
    } else {
        console.error("Modal elements not found!");
    }
}

function closeStoryModal() {
    const modal = document.getElementById('storyModal');
    if (modal) {
        modal.classList.add('hidden');
    }
}