// Utility functions
function showAlert(message, type = 'success') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    setTimeout(() => alertDiv.remove(), 5000);
}

function formatDate(date) {
    return new Date(date).toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function formatTime(date) {
    return new Date(date).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Event handling
document.addEventListener('DOMContentLoaded', () => {
    // Event creation form
    const eventForm = document.getElementById('eventForm');
    if (eventForm) {
        eventForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(eventForm);
            const eventData = {
                title: formData.get('title'),
                description: formData.get('description') || null,
                location: formData.get('location'),
                date: formData.get('date'),
                time: formData.get('time'),
                email: formData.get('email') || null,
                weather_change_threshold: 10.0,
                reminder_days_before: 1
            };

            try {
                const response = await fetch('/events/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(eventData)
                });

                if (!response.ok) {
                    const error = await response.text();
                    throw new Error(error);
                }

                const result = await response.json();
                showAlert('Event created successfully!');
                eventForm.reset();
                
                // Refresh events list
                loadEvents();
            } catch (error) {
                showAlert(error.message, 'error');
            }
        });
    }

    // Load initial events
    loadEvents();
});

// Event loading and display
async function loadEvents() {
    try {
        const response = await fetch('/events/');
        if (!response.ok) {
            throw new Error('Failed to load events');
        }

        const events = await response.json();
        const eventsList = document.getElementById('eventsList');
        if (!eventsList) return;

        eventsList.innerHTML = events.map(event => `
            <div class="card">
                <h3>${event.title}</h3>
                <p>${event.description || ''}</p>
                <div class="event-details">
                    <p><strong>Location:</strong> ${event.location}</p>
                    <p><strong>Date:</strong> ${formatDate(event.date)}</p>
                    <p><strong>Time:</strong> ${formatTime(event.date)}</p>
                </div>
                ${event.weather_data ? `
                    <div class="weather-info">
                        <div class="weather-card">
                            <h4>Weather Forecast</h4>
                            <p>Temperature: ${event.weather_data.temperature}°C</p>
                            <p>Humidity: ${event.weather_data.humidity}%</p>
                            <p>Wind: ${event.weather_data.wind_speed} m/s</p>
                        </div>
                    </div>
                ` : ''}
                <div class="event-actions">
                    <button onclick="checkAlternatives(${event.id})" class="btn btn-secondary">
                        Check Alternatives
                    </button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        showAlert('Failed to load events', 'error');
    }
}

// Alternative dates checking
async function checkAlternatives(eventId) {
    try {
        const response = await fetch(`/events/${eventId}/alternatives`);
        if (!response.ok) {
            const error = await response.text();
            throw new Error(error);
        }

        const alternatives = await response.json();
        const modal = document.getElementById('alternativesModal');
        const modalContent = document.getElementById('alternativesContent');
        
        if (!modal || !modalContent) return;

        if (alternatives.length === 0) {
            modalContent.innerHTML = `
                <div class="alert alert-warning">
                    No better alternative dates found within the specified range.
                </div>
            `;
        } else {
            modalContent.innerHTML = alternatives.map(alt => `
                <div class="card">
                    <h4>${formatDate(alt.date)}</h4>
                    <div class="weather-info">
                        <div class="weather-card">
                            <p>Temperature: ${alt.weather_data.temperature}°C</p>
                            <p>Humidity: ${alt.weather_data.humidity}%</p>
                            <p>Wind: ${alt.weather_data.wind_speed} m/s</p>
                        </div>
                    </div>
                    <div class="recommendations">
                        <h5>Recommendations:</h5>
                        <ul>
                            ${alt.weather_analysis.recommendations.map(rec => 
                                `<li>${rec}</li>`
                            ).join('')}
                        </ul>
                    </div>
                </div>
            `).join('');
        }

        modal.style.display = 'block';
    } catch (error) {
        showAlert(error.message, 'error');
    }
}

// Modal handling
window.onclick = function(event) {
    const modal = document.getElementById('alternativesModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

// Close modal when clicking the close button
document.querySelectorAll('.close-modal').forEach(button => {
    button.addEventListener('click', () => {
        const modal = document.getElementById('alternativesModal');
        if (modal) {
            modal.style.display = 'none';
        }
    });
}); 