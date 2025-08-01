// Lobbying Revenue Dashboard - Full Version with Rolling 4-Quarter View

// Global variables
let chart = null;
let firmData = [];
let filteredData = [];
let selectedFirm = null;
let currentView = 'bar';
let allFirmData = null; // Store multi-year data for line charts

// Format currency
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(value);
}

// Load year data
async function loadYearData(year) {
    console.log(`Loading data for year ${year}...`);
    try {
        const response = await fetch(`data/firms_${year}.json`);
        if (!response.ok) throw new Error(`Failed to load data for year ${year}`);
        const data = await response.json();
        console.log(`Loaded ${data.length} firms for ${year}`);
        
        // Log a sample firm to see the data structure
        if (data.length > 0) {
            console.log('Sample firm data:', data[0]);
        }
        
        return data;
    } catch (error) {
        console.error(`Error loading data for year ${year}:`, error);
        throw error;
    }
}

// Load multiple years of data for line charts
// Load multiple years of data for line charts
// Load multiple years of data for line charts
async function loadAllData() {
    try {
        const [data2024, data2025] = await Promise.all([
            loadYearData(2024),
            loadYearData(2025)
        ]);
        
        // Create a map to store firms by their ID
        const firmMap = new Map();
        
        // Process 2024 data first
        data2024.forEach(firm => {
            const firmData = {
                ...firm,
                year: 2024,
                quarterlyRevenue: { ...firm.quarterlyRevenue },
                allYearData: {
                    2024: firm,
                    2025: null
                }
            };
            firmMap.set(firm.firm_id, firmData);
        });
        
        // Process 2025 data - carefully merge without overwriting valid 2024 data
        data2025.forEach(firm => {
            const existingFirm = firmMap.get(firm.firm_id);
            
            if (existingFirm) {
                // Start with the existing quarterly revenue (which has 2024 data)
                const mergedQuarterlyRevenue = { ...existingFirm.quarterlyRevenue };
                
                // Only add/update quarters from 2025 data if they have real values
                if (firm.quarterlyRevenue) {
                    Object.entries(firm.quarterlyRevenue).forEach(([quarter, value]) => {
                        // Only update if the quarter is 2025 OR if we don't have data for this quarter yet
                        // Never overwrite existing 2024 data with zeros from 2025 file
                        if (quarter.startsWith('2025-') || 
                            (value > 0 && !mergedQuarterlyRevenue[quarter])) {
                            mergedQuarterlyRevenue[quarter] = value;
                        }
                    });
                }
                
                // Update the firm with most recent non-quarterly data
                existingFirm.totalRevenue = firm.totalRevenue;
                existingFirm.externalRevenue = firm.externalRevenue;
                existingFirm.inHouseRevenue = firm.inHouseRevenue;
                existingFirm.lobbyists = firm.lobbyists;
                existingFirm.numClients = firm.numClients;
                existingFirm.year = 2025;
                existingFirm.quarterlyRevenue = mergedQuarterlyRevenue;
                existingFirm.allYearData[2025] = firm;
                
                // Debug logging
                if (firm.name.includes('Miller Strategies')) {
                    console.log('Miller Strategies merge process:');
                    console.log('2024 quarterly data:', data2024.find(f => f.firm_id === firm.firm_id)?.quarterlyRevenue);
                    console.log('2025 quarterly data:', firm.quarterlyRevenue);
                    console.log('Merged quarterly data:', mergedQuarterlyRevenue);
                }
            } else {
                // Firm only exists in 2025
                firmMap.set(firm.firm_id, {
                    ...firm,
                    year: 2025,
                    quarterlyRevenue: { ...firm.quarterlyRevenue },
                    allYearData: {
                        2024: null,
                        2025: firm
                    }
                });
            }
        });
        
        const mergedData = Array.from(firmMap.values());
        console.log(`Loaded ${mergedData.length} unique firms across both years`);
        
        // Find and log Miller Strategies data specifically
        const millerFirm = mergedData.find(f => f.name.includes('Miller Strategies LLC'));
        if (millerFirm) {
            console.log('Miller Strategies final merged data:', {
                name: millerFirm.name,
                quarterlyRevenue: millerFirm.quarterlyRevenue
            });
        }
        
        return mergedData;
    } catch (error) {
        console.error('Error loading multi-year data:', error);
        throw error;
    }
}
// Show loading state
function showLoading() {
    document.getElementById('chartSubtitle').textContent = 'Loading data...';
    const chartContent = document.querySelector('.chart-content');
    if (chartContent) {
        chartContent.innerHTML = '<div class="loading">Loading...</div>';
    }
}

// Hide loading state
function hideLoading() {
    const chartContent = document.querySelector('.chart-content');
    if (chartContent) {
        chartContent.innerHTML = '<canvas id="revenueChart"></canvas>';
    }
}

// Show error state
function showError(message) {
    const chartContent = document.querySelector('.chart-content');
    if (chartContent) {
        chartContent.innerHTML = `<div class="error">${message}</div>`;
    }
}

// Switch view function
function switchView(view) {
    currentView = view;
    
    // Update toggle buttons
    document.getElementById('barBtn').classList.toggle('active', view === 'bar');
    document.getElementById('lineBtn').classList.toggle('active', view === 'line');
    
    // Clear selected firm when switching to line view
    if (view === 'line' && selectedFirm) {
        selectedFirm = null;
        updateFirmDetails();
    }
    
    // Update chart title
    document.getElementById('chartTitle').textContent = view === 'bar' 
        ? 'Revenue per Active Lobbyist Rankings'
        : 'Quarterly Revenue Trends';
    
    // Destroy and recreate chart with new type
    if (chart) {
        chart.destroy();
    }
    initCharts();
    
    // If switching to line view, ensure we have multi-year data
    if (view === 'line' && !allFirmData) {
        loadAllData().then(data => {
            allFirmData = data;
            updateChart();
        });
    } else {
        updateChart();
    }
}

// Initialize charts
function initCharts() {
    const canvas = document.getElementById('revenueChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    if (currentView === 'bar') {
        // Bar chart config
        const config = {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Revenue per Lobbyist',
                    data: [],
                    backgroundColor: '#31598B',
                    borderColor: '#31598B',
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const displayData = getDisplayData();
                        selectedFirm = displayData[index];
                        updateFirmDetails();
                        updateChart();
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const displayData = getDisplayData();
                                const firm = displayData[context.dataIndex];
                                return [
                                    `Revenue per Lobbyist: ${formatCurrency(context.parsed.x)}`,
                                    `Total Revenue: ${formatCurrency(firm.displayRevenue || firm.totalRevenue)}`,
                                    `Active Lobbyists: ${firm.lobbyists}`,
                                    `Number of Clients: ${firm.numClients || 'N/A'}`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Revenue per Active Lobbyist ($)'
                        },
                        ticks: {
                            callback: function(value) {
                                return '$' + (value / 1000000).toFixed(1) + 'M';
                            }
                        }
                    },
                    y: {
                        ticks: {
                            autoSkip: false,
                            font: {
                                size: 11
                            }
                        }
                    }
                }
            }
        };
        chart = new Chart(ctx, config);
    } else {
        // Line chart config
        const config = {
            type: 'line',
            data: {
                labels: ['Q1 2024', 'Q2 2024', 'Q3 2024', 'Q4 2024', 'Q1 2025'],
                datasets: []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            boxWidth: 12,
                            font: {
                                size: 11
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + formatCurrency(context.parsed.y);
                            }
                        }
                    }
                },
                
                scales: {
                    y: {
                        title: {
                            display: true,
                            text: 'Quarterly Revenue ($)'
                        },
                        ticks: {
                            callback: function(value) {
                                return '$' + (value / 1000000).toFixed(1) + 'M';
                            }
                        }
                    }
                }
            }
        };
        chart = new Chart(ctx, config);
    }
}

// Get display data for current view
function getDisplayData() {
    const topN = document.getElementById('topNFilter').value;
    const limit = topN === 'all' ? filteredData.length : parseInt(topN);
    let startIndex = 0;
    
    if (currentView === 'bar' && selectedFirm) {
        const selectedIndex = filteredData.findIndex(f => f.firm_id === selectedFirm.firm_id);
        
        if (selectedIndex !== -1) {
            const halfRange = Math.floor(limit / 2);
            startIndex = Math.max(0, selectedIndex - halfRange);
            
            if (startIndex + limit > filteredData.length) {
                startIndex = Math.max(0, filteredData.length - limit);
            }
        }
    }
    
    return filteredData.slice(startIndex, startIndex + limit);
}

// Update chart
function updateChart() {
    if (!chart || !filteredData || filteredData.length === 0) return;
    
    if (currentView === 'bar') {
        updateBarChart();
    } else {
        updateLineChart();
    }
}

// Update bar chart
function updateBarChart() {
    const displayData = getDisplayData();
    const topN = document.getElementById('topNFilter').value;
    const limit = topN === 'all' ? filteredData.length : parseInt(topN);
    
    let startIndex = 0;
    if (selectedFirm) {
        const selectedIndex = filteredData.findIndex(f => f.firm_id === selectedFirm.firm_id);
        if (selectedIndex !== -1) {
            const halfRange = Math.floor(limit / 2);
            startIndex = Math.max(0, selectedIndex - halfRange);
            if (startIndex + limit > filteredData.length) {
                startIndex = Math.max(0, filteredData.length - limit);
            }
        }
    }
    
    const labels = displayData.map((firm, index) => {
        const actualRank = startIndex + index + 1;
        return `${actualRank}. ${firm.name}`;
    });
    
    const data = displayData.map(firm => firm.revenuePerLobbyist || 0);
    const colors = displayData.map(firm => {
        if (selectedFirm && selectedFirm.firm_id === firm.firm_id) {
            return '#28a745';
        }
        return '#31598B';
    });
    
    chart.data.labels = labels;
    chart.data.datasets[0].data = data;
    chart.data.datasets[0].backgroundColor = colors;
    chart.data.datasets[0].borderColor = colors;
    
    chart.update();
    
    // Update subtitle with total count
    const displayCount = displayData.length;
    const totalCount = filteredData.length;
    let subtitle;
    
    if (selectedFirm && displayData.find(f => f.firm_id === selectedFirm.firm_id)) {
        const selectedRank = filteredData.findIndex(f => f.firm_id === selectedFirm.firm_id) + 1;
        subtitle = `Showing ${displayCount} firms centered around #${selectedRank} ${selectedFirm.name}`;
    } else {
        subtitle = topN === 'all' 
            ? `Showing all ${totalCount} firms that meet filter criteria`
            : `Showing top ${displayCount} of ${totalCount} firms that meet filter criteria`;
    }
    
    document.getElementById('chartSubtitle').textContent = subtitle;
}

// Update line chart
function updateLineChart() {
    const topN = document.getElementById('topNFilter').value;
    const searchTerm = document.getElementById('firmSearch').value.toLowerCase();
    const lobbyingType = document.getElementById('lobbyingTypeFilter').value;
    let displayFirms = [];
    
    // Use multi-year data for line chart if available
    const dataSource = allFirmData || filteredData;
    
    if (searchTerm) {
        displayFirms = dataSource.filter(firm => 
            firm.name.toLowerCase().includes(searchTerm)
        );
    } else {
        // Apply filters to multi-year data if using allFirmData
        let filterableData = dataSource;
        if (allFirmData) {
            const minRevenue = parseFloat(document.getElementById('minRevenueFilter').value) || 0;
            const maxRevenue = parseFloat(document.getElementById('maxRevenueFilter').value) || Infinity;
            const minLobbyists = parseInt(document.getElementById('minLobbyistsFilter').value) || 0;
            const maxLobbyists = parseInt(document.getElementById('maxLobbyistsFilter').value) || Infinity;
            
            filterableData = allFirmData.filter(firm => {
                const isInHouse = 
                    firm.lobbyingType === "In-House" ||
                    firm.inHouseOnly === true ||
                    firm.isInHouse === true ||
                    (firm.name && firm.name.toLowerCase().includes("in-house")) ||
                    (firm.inHousePercentage && firm.inHousePercentage === 1) ||
                    (firm.inHousePercentage && firm.inHousePercentage === 100);
                
                if (lobbyingType === 'exclude-in-house' && isInHouse) {
                    return false;
                }
                
                let revenue = firm.totalRevenue;
                if (lobbyingType === 'exclude-in-house' && firm.externalRevenue !== undefined) {
                    revenue = firm.externalRevenue;
                }
                
                if (revenue < minRevenue || revenue > maxRevenue) return false;
                if (firm.lobbyists < minLobbyists || firm.lobbyists > maxLobbyists) return false;
                
                return true;
            });
            
            // Calculate revenue per lobbyist for sorting
            filterableData.forEach(firm => {
                let revenue = firm.totalRevenue;
                if (lobbyingType === 'exclude-in-house' && firm.externalRevenue !== undefined) {
                    revenue = firm.externalRevenue;
                }
                firm.revenuePerLobbyist = firm.lobbyists > 0 ? revenue / firm.lobbyists : 0;
            });
            
            // Sort by revenue per lobbyist
            filterableData.sort((a, b) => b.revenuePerLobbyist - a.revenuePerLobbyist);
        }
        
        // Now apply the topN filter
        const limit = topN === 'all' ? filterableData.length : parseInt(topN);
        displayFirms = filterableData.slice(0, limit);
    }
    
    // Define the quarters based on available data
    const quarterLabels = ['Q1 2024', 'Q2 2024', 'Q3 2024', 'Q4 2024', 'Q1 2025', 'Q2 2025'];
    const quarterKeys = ['2024-Q1', '2024-Q2', '2024-Q3', '2024-Q4', '2025-Q1', '2025-Q2'];
    
    // Debug logging
    console.log('Displaying firms:', displayFirms.length);
    if (displayFirms.length > 0) {
        console.log('First firm quarterly data:', displayFirms[0].name, displayFirms[0].quarterlyRevenue);
    }
    
    const datasets = displayFirms.map((firm, index) => {
        let quarterlyData = [];
        
        if (firm.quarterlyRevenue) {
            // Use actual quarterly data if available
            quarterlyData = quarterKeys.map(key => {
                const value = firm.quarterlyRevenue[key];
                // Log if we find Miller Strategies data
                if (firm.name.includes('Miller Strategies') && key === '2024-Q1') {
                    console.log(`${firm.name} Q1 2024 value:`, value);
                }
                return value !== undefined ? value : 0;
            });
        } else {
            // If no quarterly data, show zeros
            quarterlyData = [0, 0, 0, 0, 0, 0];
        }
        
        // Use a color palette that can handle more lines
        const colors = [
            '#31598B', '#28a745', '#dc3545', '#ffc107', '#17a2b8',
            '#6c757d', '#343a40', '#007bff', '#6f42c1', '#e83e8c',
            '#fd7e14', '#20c997', '#375a7f', '#444', '#6610f2',
            '#e74c3c', '#3498db', '#9b59b6', '#2ecc71', '#f39c12',
            '#1abc9c', '#34495e', '#16a085', '#27ae60', '#2980b9'
        ];
        
        return {
            label: firm.name,
            data: quarterlyData,
            borderColor: colors[index % colors.length],
            backgroundColor: colors[index % colors.length] + '20',
            tension: 0.1, // Slight curve for better visibility
            pointRadius: displayFirms.length > 50 ? 0 : 4,
            pointHoverRadius: 6,
            borderWidth: displayFirms.length > 50 ? 1 : 2
        };
    });
    
    chart.data.labels = quarterLabels;
    chart.data.datasets = datasets;
    
    // Update legend visibility based on number of firms
    chart.options.plugins.legend.display = displayFirms.length <= 25;
    
    chart.update();
    
    // Update subtitle
    const totalCount = allFirmData ? 
        allFirmData.filter(firm => {
            const isInHouse = 
                firm.lobbyingType === "In-House" ||
                firm.inHouseOnly === true ||
                firm.isInHouse === true ||
                (firm.name && firm.name.toLowerCase().includes("in-house")) ||
                (firm.inHousePercentage && firm.inHousePercentage === 1) ||
                (firm.inHousePercentage && firm.inHousePercentage === 100);
            return !(lobbyingType === 'exclude-in-house' && isInHouse);
        }).length : 
        filteredData.length;
        
    const subtitle = topN === 'all' 
        ? `Quarterly revenue trends for all ${displayFirms.length} firms (last 6 quarters)`
        : `Quarterly revenue trends for top ${displayFirms.length} of ${totalCount} firms (last 6 quarters)`;
    document.getElementById('chartSubtitle').textContent = subtitle;
}
// Apply filters
async function applyFilters() {
    const year = parseInt(document.getElementById('yearFilter').value);
    const minRevenue = parseFloat(document.getElementById('minRevenueFilter').value) || 0;
    const maxRevenue = parseFloat(document.getElementById('maxRevenueFilter').value) || Infinity;
    const minLobbyists = parseInt(document.getElementById('minLobbyistsFilter').value) || 0;
    const maxLobbyists = parseInt(document.getElementById('maxLobbyistsFilter').value) || Infinity;
    const lobbyingType = document.getElementById('lobbyingTypeFilter').value;
    
    console.log('Filter values:', { year, minRevenue, maxRevenue, minLobbyists, maxLobbyists, lobbyingType });
    
    try {
        // For line chart, we need all data; for bar chart, just the selected year
        if (currentView === 'line' && !allFirmData) {
            allFirmData = await loadAllData();
        }
        
        // Load specific year data for bar chart
        firmData = await loadYearData(year);
        
        filteredData = firmData.filter(firm => {
            // Check if this is an in-house firm
            const isInHouse = 
                firm.lobbyingType === "In-House" ||
                firm.inHouseOnly === true ||
                firm.isInHouse === true ||
                (firm.name && firm.name.toLowerCase().includes("in-house")) ||
                (firm.inHousePercentage && firm.inHousePercentage === 1) ||
                (firm.inHousePercentage && firm.inHousePercentage === 100);
            
            // If excluding in-house and this is an in-house firm, filter it out
            if (lobbyingType === 'exclude-in-house' && isInHouse) {
                console.log(`Filtering out in-house firm: ${firm.name}`);
                return false;
            }
            
            // Use the appropriate revenue value
            let revenue = firm.totalRevenue;
            if (lobbyingType === 'exclude-in-house' && firm.externalRevenue !== undefined) {
                revenue = firm.externalRevenue;
            }
            
            // Apply revenue range filter
            if (revenue < minRevenue || revenue > maxRevenue) return false;
            
            // Apply lobbyist range filter
            if (firm.lobbyists < minLobbyists || firm.lobbyists > maxLobbyists) return false;
            
            return true;
        });
        
        // Calculate revenue per lobbyist
        filteredData.forEach(firm => {
            let revenue = firm.totalRevenue;
            if (lobbyingType === 'exclude-in-house' && firm.externalRevenue !== undefined) {
                revenue = firm.externalRevenue;
            }
            
            firm.displayRevenue = revenue;
            firm.revenuePerLobbyist = firm.lobbyists > 0 ? revenue / firm.lobbyists : 0;
        });
        
        // Sort by revenue per lobbyist
        filteredData.sort((a, b) => b.revenuePerLobbyist - a.revenuePerLobbyist);
        
        console.log(`Filtered to ${filteredData.length} firms`);
        if (lobbyingType === 'exclude-in-house') {
            console.log('In-house firms excluded from results');
        }
        
        updateChart();
        
        if (selectedFirm && !filteredData.find(f => f.firm_id === selectedFirm.firm_id)) {
            selectedFirm = null;
            updateFirmDetails();
        }
        
    } catch (error) {
        console.error('Error in applyFilters:', error);
        showError(`Failed to load data for ${year}`);
    }
}

// Update firm details panel
function updateFirmDetails() {
    const detailsDiv = document.getElementById('firmDetails');
    
    if (!selectedFirm) {
        detailsDiv.innerHTML = `
            <div class="detail-header">
                <div class="detail-title">Firm Overview</div>
                <div class="detail-subtitle">Click on a firm for details</div>
            </div>
            <div class="no-selection">
                Select a firm from the chart to view detailed information
            </div>
        `;
        return;
    }

    const lobbyingType = document.getElementById('lobbyingTypeFilter').value;
    const displayRevenue = selectedFirm.displayRevenue || selectedFirm.totalRevenue;
    const displayRevenuePerLobbyist = selectedFirm.revenuePerLobbyist || 
        (selectedFirm.lobbyists > 0 ? displayRevenue / selectedFirm.lobbyists : 0);
    
    // Check if this is an in-house firm
    const isInHouse = 
        selectedFirm.lobbyingType === "In-House" ||
        selectedFirm.inHouseOnly === true ||
        selectedFirm.isInHouse === true ||
        (selectedFirm.name && selectedFirm.name.toLowerCase().includes("in-house")) ||
        (selectedFirm.inHousePercentage && selectedFirm.inHousePercentage >= 1);
    
    // Generate sample client data if not present
    if (!selectedFirm.clients) {
        selectedFirm.clients = [
            { name: "Client A", amount: displayRevenue * 0.3 },
            { name: "Client B", amount: displayRevenue * 0.2 },
            { name: "Client C", amount: displayRevenue * 0.15 },
            { name: "Client D", amount: displayRevenue * 0.1 },
            { name: "Client E", amount: displayRevenue * 0.05 }
        ];
    }
    
    detailsDiv.innerHTML = `
        <div class="detail-header">
            <div class="detail-title">Firm Details</div>
            <div class="detail-subtitle">Revenue Analysis (${selectedFirm.year || document.getElementById('yearFilter').value})</div>
        </div>
        <div class="firm-card">
            <div class="firm-name">${selectedFirm.name}</div>
            <div class="metric-grid">
                <div class="metric-item">
                    <div class="metric-value">${formatCurrency(displayRevenuePerLobbyist)}</div>
                    <div class="metric-label">Revenue per Lobbyist</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">${formatCurrency(displayRevenue)}</div>
                    <div class="metric-label">Total Revenue</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">${selectedFirm.lobbyists}</div>
                    <div class="metric-label">Active Lobbyists</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">${selectedFirm.numClients || 'N/A'}</div>
                    <div class="metric-label">Total Clients</div>
                </div>
            </div>
            ${isInHouse ? `
                <div class="in-house-badge">
                    100% In-House Revenue
                </div>
            ` : selectedFirm.inHousePercentage > 0 ? `
                <div class="in-house-badge">
                    ${(selectedFirm.inHousePercentage * 100).toFixed(1)}% In-House Revenue
                </div>
            ` : ''}
            <div class="client-list">
                <div class="client-header">Top Clients</div>
                ${selectedFirm.clients.slice(0, 5).map(client => `
                    <div class="client-row">
                        <div class="client-name">${client.name}</div>
                        <div class="client-amount">${formatCurrency(client.amount)}</div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// Setup autocomplete
function setupAutocomplete() {
    const searchInput = document.getElementById('firmSearch');
    const autocompleteDiv = document.getElementById('autocomplete');
    let selectedIndex = -1;
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        
        if (searchTerm.length < 2) {
            autocompleteDiv.style.display = 'none';
            if (searchTerm.length === 0) {
                selectedFirm = null;
                updateFirmDetails();
            }
            applyFilters();
            return;
        }
        
        const matches = firmData
            .filter(firm => firm.name.toLowerCase().includes(searchTerm))
            .slice(0, 10);
        
        if (matches.length > 0) {
            autocompleteDiv.innerHTML = matches.map((firm, index) => 
                `<div class="autocomplete-item" data-index="${index}" data-id="${firm.firm_id}">
                    ${firm.name}
                </div>`
            ).join('');
            autocompleteDiv.style.display = 'block';
            selectedIndex = -1;
        } else {
            autocompleteDiv.style.display = 'none';
        }
    });
    
    searchInput.addEventListener('keydown', function(e) {
        const items = autocompleteDiv.querySelectorAll('.autocomplete-item');
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
            updateSelection(items, selectedIndex);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            selectedIndex = Math.max(selectedIndex - 1, -1);
            updateSelection(items, selectedIndex);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (selectedIndex >= 0 && items[selectedIndex]) {
                const firmId = items[selectedIndex].dataset.id;
                selectFirm(firmId);
            }
        } else if (e.key === 'Escape') {
            autocompleteDiv.style.display = 'none';
            selectedIndex = -1;
        }
    });
    
    function updateSelection(items, index) {
        items.forEach((item, i) => {
            item.classList.toggle('selected', i === index);
        });
    }
    
    autocompleteDiv.addEventListener('click', function(e) {
        if (e.target.classList.contains('autocomplete-item')) {
            selectFirm(e.target.dataset.id);
        }
    });
    
    function selectFirm(firmId) {
        selectedFirm = firmData.find(f => f.firm_id === firmId);
        searchInput.value = selectedFirm.name;
        autocompleteDiv.style.display = 'none';
        
        applyFilters().then(() => {
            updateFirmDetails();
            updateChart();
        });
    }
    
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !autocompleteDiv.contains(e.target)) {
            autocompleteDiv.style.display = 'none';
        }
    });
}

// Setup event listeners
function setupEventListeners() {
    document.getElementById('yearFilter').addEventListener('change', applyFilters);
    document.getElementById('topNFilter').addEventListener('change', () => updateChart());
    document.getElementById('minRevenueFilter').addEventListener('input', applyFilters);
    document.getElementById('maxRevenueFilter').addEventListener('input', applyFilters);
    document.getElementById('minLobbyistsFilter').addEventListener('input', applyFilters);
    document.getElementById('maxLobbyistsFilter').addEventListener('input', applyFilters);
    document.getElementById('lobbyingTypeFilter').addEventListener('change', applyFilters);
    
    document.getElementById('barBtn').addEventListener('click', () => switchView('bar'));
    document.getElementById('lineBtn').addEventListener('click', () => switchView('line'));
}

// Initialize application
async function initializeApp() {
    try {
        showLoading();

        const yearSelect = document.getElementById('yearFilter');
        yearSelect.innerHTML = '';
        
        const years = [2025, 2024];
        years.forEach((year, index) => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            if (index === 0) option.selected = true;
            yearSelect.appendChild(option);
        });
        
        // Set default values
        document.getElementById('minLobbyistsFilter').value = '10';
        document.getElementById('lobbyingTypeFilter').value = 'exclude-in-house';

        hideLoading();
        
        setTimeout(() => {
            initCharts();
            setupAutocomplete();
            setupEventListeners();
            applyFilters();
        }, 100);

    } catch (error) {
        console.error('Failed to initialize app:', error);
        showError('Failed to initialize application');
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

// Handle window resize
window.addEventListener('resize', () => {
    if (chart) {
        chart.resize();
    }
});
