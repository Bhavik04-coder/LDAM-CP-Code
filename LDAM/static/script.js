let currentData = {};
let tempChart = null;
let tempHistory = [];
let maxHistoryPoints = 50;
let statsCounters = {
    normal: 0,
    warning: 0,
    fever: 0
};

// Initialize Chart
function initChart() {
    const ctx = document.getElementById('tempChart').getContext('2d');
    tempChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Temperature (°C)',
                data: [],
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: '#6366f1',
                pointBorderColor: '#fff',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(30, 41, 59, 0.9)',
                    titleColor: '#f1f5f9',
                    bodyColor: '#f1f5f9',
                    borderColor: '#334155',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    min: 35,
                    max: 42,
                    grid: {
                        color: 'rgba(51, 65, 85, 0.3)'
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(51, 65, 85, 0.3)'
                    },
                    ticks: {
                        color: '#94a3b8',
                        maxTicksLimit: 10
                    }
                }
            }
        }
    });
}

// Update temperature chart
function updateChart(temperature, timestamp) {
    if (!tempChart) return;
    
    const time = new Date(timestamp).toLocaleTimeString();
    
    tempHistory.push({ temp: temperature, time: time });
    if (tempHistory.length > maxHistoryPoints) {
        tempHistory.shift();
    }
    
    tempChart.data.labels = tempHistory.map(h => h.time);
    tempChart.data.datasets[0].data = tempHistory.map(h => h.temp);
    
    // Change line color based on temperature
    if (temperature >= 39.5) {
        tempChart.data.datasets[0].borderColor = '#ef4444';
        tempChart.data.datasets[0].backgroundColor = 'rgba(239, 68, 68, 0.1)';
    } else if (temperature >= 39.0) {
        tempChart.data.datasets[0].borderColor = '#f59e0b';
        tempChart.data.datasets[0].backgroundColor = 'rgba(245, 158, 11, 0.1)';
    } else {
        tempChart.data.datasets[0].borderColor = '#10b981';
        tempChart.data.datasets[0].backgroundColor = 'rgba(16, 185, 129, 0.1)';
    }
    
    tempChart.update('none');
}

// Update temperature gauge
function updateGauge(temperature) {
    const gauge = document.getElementById('gaugeProgress');
    if (!gauge) return;
    
    const minTemp = 35;
    const maxTemp = 42;
    const percentage = ((temperature - minTemp) / (maxTemp - minTemp)) * 100;
    const circumference = 2 * Math.PI * 80;
    const offset = circumference - (percentage / 100) * circumference;
    
    gauge.style.strokeDashoffset = offset;
    
    // Change color based on temperature
    if (temperature >= 39.5) {
        gauge.style.stroke = '#ef4444';
    } else if (temperature >= 39.0) {
        gauge.style.stroke = '#f59e0b';
    } else {
        gauge.style.stroke = '#10b981';
    }
}

// Update UI with sensor data
function updateUI() {
    fetch('/api/data')
        .then(response => response.json())
        .then(data => {
            currentData = data;

            // Update navigation status
            const statusDotNav = document.getElementById('statusDotNav');
            const statusTextNav = document.getElementById('statusTextNav');
            const connectBtn = document.getElementById('connectBtn');
            const disconnectBtn = document.getElementById('disconnectBtn');

            if (data.connected) {
                statusDotNav.style.backgroundColor = '#10b981';
                statusTextNav.textContent = 'Online';
                statusTextNav.style.color = '#10b981';
                connectBtn.disabled = true;
                disconnectBtn.disabled = false;
                
                document.getElementById('connectionIcon').className = 'fas fa-circle status-icon online';
                document.getElementById('connectionStatus').textContent = 'Online';
                document.getElementById('dataIcon').className = 'fas fa-circle status-icon online';
                document.getElementById('dataStatus').textContent = 'Active';
            } else {
                statusDotNav.style.backgroundColor = '#ef4444';
                statusTextNav.textContent = 'Offline';
                statusTextNav.style.color = '#ef4444';
                connectBtn.disabled = false;
                disconnectBtn.disabled = true;
                
                document.getElementById('connectionIcon').className = 'fas fa-circle status-icon offline';
                document.getElementById('connectionStatus').textContent = 'Offline';
                document.getElementById('dataIcon').className = 'fas fa-circle status-icon offline';
                document.getElementById('dataStatus').textContent = 'Idle';
            }

            // Update temperature
            const tempValue = document.getElementById('tempValue');
            const heroTemp = document.getElementById('heroTemp');
            
            if (data.temperature !== null) {
                const temp = parseFloat(data.temperature);
                tempValue.textContent = temp.toFixed(1);
                heroTemp.textContent = temp.toFixed(1) + '°C';
                
                // Update gauge
                updateGauge(temp);
                
                // Update chart
                if (data.timestamp) {
                    updateChart(temp, data.timestamp);
                }
                
                // Update stats counters
                if (data.fever_alert) {
                    statsCounters.fever++;
                } else if (data.fever_status === 'ELEVATED TEMP') {
                    statsCounters.warning++;
                } else if (data.fever_status === 'NORMAL') {
                    statsCounters.normal++;
                }
            } else {
                tempValue.textContent = '--';
                heroTemp.textContent = '--°C';
            }

            // Update fever badge
            const feverBadge = document.getElementById('feverBadge');
            
            if (data.fever_alert) {
                feverBadge.innerHTML = '<i class="fas fa-fire"></i> FEVER DETECTED!';
                feverBadge.className = 'status-badge fever';
            } else if (data.fever_status === 'ELEVATED TEMP') {
                feverBadge.innerHTML = '<i class="fas fa-exclamation-triangle"></i> ELEVATED TEMP';
                feverBadge.className = 'status-badge elevated';
            } else if (data.fever_status === 'NORMAL') {
                feverBadge.innerHTML = '<i class="fas fa-check-circle"></i> NORMAL';
                feverBadge.className = 'status-badge normal';
            } else {
                feverBadge.innerHTML = '<i class="fas fa-info-circle"></i> NO DATA';
                feverBadge.className = 'status-badge';
            }

            // Update location
            const latValue = document.getElementById('latValue');
            const lonValue = document.getElementById('lonValue');
            const gpsStatus = document.getElementById('gpsStatus');
            const heroGPS = document.getElementById('heroGPS');
            const gpsIcon = document.getElementById('gpsIcon');
            const gpsSignalStatus = document.getElementById('gpsSignalStatus');

            if (data.gps_available && data.latitude && data.longitude) {
                latValue.textContent = parseFloat(data.latitude).toFixed(6);
                lonValue.textContent = parseFloat(data.longitude).toFixed(6);
                gpsStatus.innerHTML = '<i class="fas fa-satellite-dish"></i> GPS Active';
                gpsStatus.className = 'gps-status active';
                heroGPS.textContent = 'Active';
                heroGPS.className = 'hero-stat-value text-success';
                gpsIcon.className = 'fas fa-circle status-icon online';
                gpsSignalStatus.textContent = 'Active';
            } else {
                latValue.textContent = '--';
                lonValue.textContent = '--';
                gpsStatus.innerHTML = '<i class="fas fa-satellite-dish"></i> Searching...';
                gpsStatus.className = 'gps-status';
                heroGPS.textContent = 'Waiting';
                heroGPS.className = 'hero-stat-value';
                gpsIcon.className = 'fas fa-circle status-icon offline';
                gpsSignalStatus.textContent = 'No Signal';
            }

            // Update timestamp
            const lastUpdate = document.getElementById('lastUpdate');
            if (data.timestamp) {
                lastUpdate.innerHTML = `<i class="fas fa-clock"></i> Last update: ${data.timestamp}`;
            } else {
                lastUpdate.innerHTML = '<i class="fas fa-clock"></i> Last update: Never';
            }

            // Update counts
            const updateCount = document.getElementById('updateCount');
            const heroUpdates = document.getElementById('heroUpdates');
            const normalCount = document.getElementById('normalCount');
            const warningCount = document.getElementById('warningCount');
            const feverCount = document.getElementById('feverCount');
            
            updateCount.textContent = data.update_count || 0;
            heroUpdates.textContent = data.update_count || 0;
            normalCount.textContent = statsCounters.normal;
            warningCount.textContent = statsCounters.warning;
            feverCount.textContent = statsCounters.fever;

            // Update error
            const errorBox = document.getElementById('errorBox');
            if (data.error) {
                errorBox.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${data.error}`;
                errorBox.className = 'error-display error';
            } else {
                errorBox.innerHTML = '<i class="fas fa-check-circle"></i> All systems operational';
                errorBox.className = 'error-display';
            }
        })
        .catch(error => {
            console.error('Error fetching data:', error);
        });
}

// Refresh available ports
function refreshPorts() {
    const portsList = document.getElementById('portsList');
    portsList.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Loading ports...</div>';
    
    fetch('/api/ports')
        .then(response => response.json())
        .then(ports => {
            const portSelect = document.getElementById('portSelect');
            
            // Update dropdown
            portSelect.innerHTML = '';
            if (ports.length > 0) {
                ports.forEach(port => {
                    const option = document.createElement('option');
                    option.value = port.device;
                    option.textContent = port.device;
                    portSelect.appendChild(option);
                });
            } else {
                const option = document.createElement('option');
                option.value = 'COM5';
                option.textContent = 'COM5';
                portSelect.appendChild(option);
            }

            // Update ports list display
            if (ports.length > 0) {
                portsList.innerHTML = ports.map(p => `
                    <div class="port-item">
                        <div class="port-device"><i class="fas fa-usb"></i> ${p.device}</div>
                        <div class="port-description">${p.description}</div>
                    </div>
                `).join('');
            } else {
                portsList.innerHTML = '<div style="text-align: center; color: var(--text-secondary); padding: 1rem;">No serial ports detected</div>';
            }

            showNotification('Port list updated successfully', 'success');
        })
        .catch(error => {
            console.error('Error refreshing ports:', error);
            portsList.innerHTML = '<div style="text-align: center; color: var(--danger); padding: 1rem;"><i class="fas fa-exclamation-triangle"></i> Error loading ports</div>';
            showNotification('Error refreshing ports', 'error');
        });
}

// Show notification
function showNotification(message, type = 'info') {
    // Simple alert for now - can be enhanced with toast notifications
    console.log(`[${type.toUpperCase()}] ${message}`);
}

// Connect to serial port
function connectSerial() {
    const port = document.getElementById('portSelect').value;
    const statusDotNav = document.getElementById('statusDotNav');
    const statusTextNav = document.getElementById('statusTextNav');
    const connectBtn = document.getElementById('connectBtn');
    
    statusDotNav.style.backgroundColor = '#f59e0b';
    statusTextNav.textContent = 'Connecting...';
    statusTextNav.style.color = '#f59e0b';
    connectBtn.disabled = true;

    fetch('/api/connect', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ port: port })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
        } else {
            showNotification('Connection failed: ' + data.message, 'error');
            statusDotNav.style.backgroundColor = '#ef4444';
            statusTextNav.textContent = 'Failed';
            statusTextNav.style.color = '#ef4444';
            connectBtn.disabled = false;
        }
    })
    .catch(error => {
        console.error('Error connecting:', error);
        showNotification('Error connecting to serial port', 'error');
        statusDotNav.style.backgroundColor = '#ef4444';
        statusTextNav.textContent = 'Error';
        statusTextNav.style.color = '#ef4444';
        connectBtn.disabled = false;
    });
}

// Disconnect from serial port
function disconnectSerial() {
    fetch('/api/disconnect', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
        } else {
            showNotification('Disconnect failed: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error disconnecting:', error);
        showNotification('Error disconnecting from serial port', 'error');
    });
}

// Set chart time range
function setChartRange(range) {
    // Update active button
    document.querySelectorAll('.chart-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Adjust max history points based on range
    if (range === '1h') {
        maxHistoryPoints = 50;
    } else if (range === '6h') {
        maxHistoryPoints = 300;
    } else if (range === '24h') {
        maxHistoryPoints = 1440;
    }
    
    showNotification(`Chart range set to ${range}`, 'info');
}

// Open location on Google Maps
function openMap() {
    if (currentData.latitude && currentData.longitude) {
        const url = `https://www.google.com/maps?q=${currentData.latitude},${currentData.longitude}`;
        window.open(url, '_blank');
    } else {
        alert('GPS data not available yet');
    }
}

// Theme Management
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    // Update icon
    const themeIcon = document.getElementById('themeIcon');
    if (newTheme === 'light') {
        themeIcon.className = 'fas fa-sun';
    } else {
        themeIcon.className = 'fas fa-moon';
    }
    
    // Update chart colors if chart exists
    if (tempChart) {
        updateChartTheme(newTheme);
    }
}

function updateChartTheme(theme) {
    if (!tempChart) return;
    
    const gridColor = theme === 'light' ? 'rgba(226, 232, 240, 0.5)' : 'rgba(51, 65, 85, 0.3)';
    const textColor = theme === 'light' ? '#475569' : '#94a3b8';
    
    tempChart.options.scales.y.grid.color = gridColor;
    tempChart.options.scales.y.ticks.color = textColor;
    tempChart.options.scales.x.grid.color = gridColor;
    tempChart.options.scales.x.ticks.color = textColor;
    
    tempChart.update('none');
}

function loadTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    
    const themeIcon = document.getElementById('themeIcon');
    if (themeIcon) {
        themeIcon.className = savedTheme === 'light' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Load saved theme
    loadTheme();
    
    // Initialize chart
    initChart();
    
    // Initial load
    refreshPorts();
    updateUI();
    
    // Update every second
    setInterval(updateUI, 1000);
    
    // Add smooth scroll for navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    console.log('Livestock Health Monitor Pro initialized');
});
