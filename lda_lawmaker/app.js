// Global variables
let orgData = [];
let issueData = [];
let chart = null;
let filteredData = [];
let availableCongresses = [];
let currentCongress = null;

// Helper function to generate bill URL safely
function generateBillUrl(bill) {
    // Generate URL from the new separate fields: bill_number + bill_type + congress
    if (bill.bill_number && bill.bill_type && bill.congress) {
        return `${bill.bill_number}_${bill.congress}_${bill.bill_type}`;
    }
    
    // Fallback - return null to prevent bad URLs
    console.warn('Unable to generate bill URL for bill:', bill);
    return null;
}

// Color palettes matching R Shiny app
const partyColors = {
    'Democrat': '#2E598E',
    'Republican': '#810000',
    'Independent': '#B19CD9'
};

const organizationColors = [
    '#0C2041', '#2E598E', '#E37A61', '#EFA982', '#579DB9',
    '#89C1C4', '#4A001E', '#810000', '#973D7D', '#6B56AA'
];

// Load manifest and initialize congress selector
async function loadManifest() {
    try {
        console.log('Loading data manifest...');
        const response = await fetch('data/manifest.json');
        if (!response.ok) {
            throw new Error(`Failed to load manifest: ${response.status}`);
        }
        
        const manifest = await response.json();
        availableCongresses = manifest.congresses;
        console.log('Available congresses:', availableCongresses.map(c => c.congress));
        
        // Initialize congress selector with available options
        const congressSelect = document.getElementById('congress-version');
        congressSelect.innerHTML = '';
        
        availableCongresses.forEach(congress => {
            const option = document.createElement('option');
            option.value = congress.congress;
            option.textContent = congress.congress;
            congressSelect.appendChild(option);
        });
        
        // Set default to latest congress
        const latestCongress = availableCongresses[0].congress;
        congressSelect.value = latestCongress;
        currentCongress = latestCongress;
        
        // Add change listener for congress selector
        congressSelect.addEventListener('change', loadCongressData);
        
        // Load initial data
        await loadCongressData();
        
    } catch (error) {
        console.error('Error loading manifest:', error);
        document.getElementById('main-title').textContent = 'Error loading data manifest. Please check console.';
    }
}

// Load data for specific congress
async function loadCongressData() {
    try {
        const selectedCongress = document.getElementById('congress-version').value;
        console.log(`Loading data for Congress ${selectedCongress}...`);
        
        // Show loading indicator
        document.getElementById('subtitle').textContent = `Loading Congress ${selectedCongress} data...`;
        
        const [orgResponse, issueResponse] = await Promise.all([
            fetch(`data/lda_orgs_${selectedCongress}.json`),
            fetch('data/lda_bill_issues.json')
        ]);
        
        if (!orgResponse.ok) {
            throw new Error(`Failed to load organizations data for Congress ${selectedCongress}: ${orgResponse.status}`);
        }
        if (!issueResponse.ok) {
            throw new Error(`Failed to load issues data: ${issueResponse.status}`);
        }
        
        orgData = await orgResponse.json();
        issueData = await issueResponse.json();
        currentCongress = selectedCongress;
        
        console.log('Data loaded:', {
            congress: selectedCongress,
            orgData: orgData.length,
            issueData: issueData.length
        });
        
        // Clear existing chips and reinitialize filters
        clearAllChips();
        initializeFilters();
        updateChart();
        
    } catch (error) {
        console.error('Error loading congress data:', error);
        document.getElementById('subtitle').textContent = `Error loading Congress data: ${error.message}`;
    }
}

// Clear all existing chips and reset filters
function clearAllChips() {
    const chipContainers = document.querySelectorAll('.chip-input-container');
    chipContainers.forEach(container => {
        const chips = container.querySelectorAll('.chip');
        chips.forEach(chip => chip.remove());
        
        const select = container.querySelector('select[multiple]');
        if (select) {
            Array.from(select.options).forEach(option => option.selected = false);
        }
        
        const searchInput = container.querySelector('.chip-input');
        if (searchInput) {
            searchInput.value = '';
            searchInput.placeholder = searchInput.placeholder.replace('Add more...', `Type to search ${searchInput.id.replace('-search', '').replace('-', ' ')}...`);
        }
    });
}

// Initialize filter options
function initializeFilters() {
    console.log('Initializing filters...');
    
    if (!orgData || !issueData || orgData.length === 0) {
        console.error('No data available for filters');
        return;
    }
    
    try {
        // Congress filter is now handled by loadManifest function
        
        // Organization filter (chip input)
        const organizations = [...new Set(orgData.map(d => d.combined_name).filter(Boolean))].sort();
        console.log('Organizations count:', organizations.length);
        initializeChipInput('selected-organizations', 'organizations-container', organizations);
        
        // Sponsor filter (chip input) - sort by last_name
        const sponsorData = orgData.filter(d => d.display_name && d.last_name);
        const uniqueSponsors = [...new Map(sponsorData.map(d => [d.display_name, d.last_name])).entries()];
        const sponsors = uniqueSponsors
            .sort((a, b) => a[1].localeCompare(b[1])) // Sort by last_name (index 1)
            .map(sponsor => sponsor[0]); // Get display_name (index 0)
        console.log('Sponsors count:', sponsors.length);
        initializeChipInput('selected-sponsors', 'sponsors-container', sponsors);
        
        // Party filter (chip input)
        const parties = [...new Set(orgData.map(d => d.party_name).filter(Boolean))].sort();
        console.log('Parties:', parties);
        initializeChipInput('selected-party', 'party-container', parties);
        
        // Status filter (chip input)
        const statuses = [...new Set(orgData.map(d => d.status).filter(s => s && s !== 'NULL'))].sort();
        console.log('Statuses count:', statuses.length);
        initializeChipInput('selected-status', 'status-container', statuses);
        
        // Issue filter (chip input)
        const issues = [...new Set(issueData.map(d => d.issue_name).filter(Boolean))].sort();
        console.log('Issues count:', issues.length);
        initializeChipInput('selected-issues', 'issues-container', issues);
        
        // Add event listeners to single-select filters (congress listener is added in loadManifest)
        document.getElementById('num-bills').addEventListener('change', updateChart);
        
        // Global click handler to close all chip dropdowns when clicking outside
        document.addEventListener('click', (e) => {
            // Check if click is outside any chip input container
            const chipContainers = document.querySelectorAll('.chip-input-container');
            let isClickOutside = true;
            
            chipContainers.forEach(container => {
                if (e.target.closest(`#${container.id}`)) {
                    isClickOutside = false;
                }
            });
            
            if (isClickOutside) {
                // Hide all open dropdowns
                document.querySelectorAll('.chip-dropdown.show').forEach(dropdown => {
                    dropdown.classList.remove('show');
                });
            }
        });
        
        console.log('Filters initialized successfully');
    } catch (error) {
        console.error('Error initializing filters:', error);
    }
}

// Helper function to populate single select options
function populateSingleSelect(selectId, options, selected = null) {
    const select = document.getElementById(selectId);
    select.innerHTML = '';
    
    options.forEach(option => {
        const optionElement = document.createElement('option');
        optionElement.value = option;
        optionElement.textContent = option;
        if (option === selected) {
            optionElement.selected = true;
        }
        select.appendChild(optionElement);
    });
}

// Initialize chip input
function initializeChipInput(selectId, containerId, options) {
    console.log(`Initializing chip input for ${selectId} with ${options.length} options`);
    
    const select = document.getElementById(selectId);
    const container = document.getElementById(containerId);
    const searchInput = document.getElementById(selectId.replace('selected-', '') + '-search');
    
    if (!select || !container || !searchInput) {
        console.error(`Elements not found for ${selectId}`, { 
            select: !!select, 
            container: !!container, 
            searchInput: !!searchInput 
        });
        return;
    }
    
    // Store all options for filtering
    select.allOptions = options;
    
    // Clear existing options
    select.innerHTML = '';
    
    // Add all options to hidden select
    options.forEach(option => {
        const optionElement = document.createElement('option');
        optionElement.value = option;
        optionElement.textContent = option;
        select.appendChild(optionElement);
    });
    
    // Remove existing dropdown if it exists
    const existingDropdown = document.getElementById(`${selectId}-dropdown`);
    if (existingDropdown) {
        existingDropdown.remove();
    }
    
    // Create dropdown
    const dropdown = document.createElement('div');
    dropdown.className = 'chip-dropdown';
    dropdown.id = `${selectId}-dropdown`;
    
    // Add dropdown to DOM inside container but positioned absolutely
    container.appendChild(dropdown);
    console.log(`Dropdown created and appended for ${selectId}`);
    populateChipDropdown(selectId, options);
    
    // Make container clickable to focus input
    container.addEventListener('click', () => {
        searchInput.focus();
    });
    
    // Setup search functionality
    searchInput.addEventListener('input', (e) => {
        console.log(`Input event fired for ${selectId} with: "${e.target.value}"`);
        filterChipOptions(selectId, e.target.value);
        
        // Always show dropdown when typing (even for empty search)
        console.log(`About to show dropdown for ${selectId}`);
        showChipDropdown(selectId);
    });
    
    searchInput.addEventListener('focus', () => {
        // Show dropdown on focus if there's text or just for initial display
        showChipDropdown(selectId);
    });
    
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            console.log(`Enter pressed for ${selectId}`);
            const dropdown = document.getElementById(`${selectId}-dropdown`);
            if (dropdown) {
                const allOptions = dropdown.querySelectorAll('.dropdown-option');
                const visibleOptions = Array.from(allOptions).filter(option => 
                    option.style.display !== 'none' && !option.style.display.includes('none')
                );
                console.log(`Found ${allOptions.length} total options, ${visibleOptions.length} visible options`);
                if (visibleOptions.length > 0) {
                    console.log(`Clicking first option: ${visibleOptions[0].textContent}`);
                    visibleOptions[0].click();
                }
            } else {
                console.error(`Dropdown not found: ${selectId}-dropdown`);
            }
        }
        
        // Handle backspace to remove last chip if input is empty
        if (e.key === 'Backspace' && searchInput.value === '') {
            console.log(`Backspace pressed for ${selectId} with empty input`);
            const selectedOptions = Array.from(select.selectedOptions);
            console.log(`Found ${selectedOptions.length} selected options`);
            if (selectedOptions.length > 0) {
                const lastOption = selectedOptions[selectedOptions.length - 1];
                console.log(`Removing last option: ${lastOption.value}`);
                lastOption.selected = false;
                updateChips(selectId, containerId);
                updateChart();
            }
        }
    });
    
    // Note: Global click handler is attached in initializeFilters to avoid duplicates
    
    console.log(`Chip input initialized for ${selectId}`);
}

// Populate chip dropdown options
function populateChipDropdown(selectId, options) {
    const dropdown = document.getElementById(`${selectId}-dropdown`);
    
    if (!dropdown) {
        console.error(`Dropdown element not found: ${selectId}-dropdown`);
        return;
    }
    
    dropdown.innerHTML = '';
    
    options.forEach(option => {
        const optionDiv = document.createElement('div');
        optionDiv.className = 'dropdown-option';
        optionDiv.textContent = option;
        optionDiv.addEventListener('click', () => addChip(selectId, selectId.replace('selected-', '') + '-container', option));
        dropdown.appendChild(optionDiv);
    });
    
    console.log(`Populated ${options.length} options for ${selectId}`);
}

// Filter chip options based on search term
function filterChipOptions(selectId, searchTerm) {
    const dropdown = document.getElementById(`${selectId}-dropdown`);
    
    if (!dropdown) {
        console.error(`Dropdown not found for filtering: ${selectId}-dropdown`);
        return;
    }
    
    const options = dropdown.querySelectorAll('.dropdown-option');
    const term = searchTerm.toLowerCase();
    
    console.log(`Filtering ${options.length} options for "${term}"`);
    
    let visibleCount = 0;
    options.forEach(option => {
        const text = option.textContent.toLowerCase();
        if (text.includes(term)) {
            option.style.display = 'block';
            visibleCount++;
        } else {
            option.style.display = 'none';
        }
    });
    
    console.log(`${visibleCount} options visible after filtering`);
}

// Show chip dropdown
function showChipDropdown(selectId) {
    console.log(`Showing dropdown for ${selectId}`);
    
    // Close all other dropdowns first
    document.querySelectorAll('.chip-dropdown').forEach(dd => {
        dd.classList.remove('show');
    });
    
    const dropdown = document.getElementById(`${selectId}-dropdown`);
    if (dropdown) {
        console.log(`Dropdown found, adding show class`);
        dropdown.classList.add('show');
    } else {
        console.error(`Dropdown not found: ${selectId}-dropdown`);
    }
}

// Hide chip dropdown
function hideChipDropdown(selectId) {
    const dropdown = document.getElementById(`${selectId}-dropdown`);
    const searchInput = document.getElementById(selectId.replace('selected-', '') + '-search');
    
    if (dropdown) {
        dropdown.classList.remove('show');
    }
    
    // Clear search and reset filter
    if (searchInput) {
        searchInput.value = '';
        filterChipOptions(selectId, '');
    }
}

// Add chip (select option)
function addChip(selectId, containerId, value) {
    console.log(`Adding chip: ${value} for ${selectId}`);
    
    const select = document.getElementById(selectId);
    const optionElement = Array.from(select.options).find(opt => opt.value === value);
    const searchInput = document.getElementById(selectId.replace('selected-', '') + '-search');
    
    if (!optionElement) {
        console.error(`Option not found: ${value}`);
        return;
    }
    
    // Don't add if already selected
    if (optionElement.selected) {
        console.log(`Option already selected: ${value}`);
        hideChipDropdown(selectId);
        if (searchInput) {
            searchInput.value = '';
            searchInput.focus();
        }
        return;
    }
    
    optionElement.selected = true;
    updateChips(selectId, containerId);
    
    // Clear search and refocus for more selections
    if (searchInput) {
        searchInput.value = '';
        filterChipOptions(selectId, '');
        setTimeout(() => searchInput.focus(), 50);
    }
    
    hideChipDropdown(selectId);
    updateChart();
}

// Remove chip (deselect option)
function removeChip(selectId, containerId, value) {
    console.log(`removeChip called for: ${value}`);
    const select = document.getElementById(selectId);
    const optionElement = Array.from(select.options).find(opt => opt.value === value);
    
    if (optionElement) {
        console.log(`Found option element, deselecting: ${value}`);
        optionElement.selected = false;
        updateChips(selectId, containerId);
        updateChart();
    } else {
        console.error(`Option element not found for value: ${value}`);
    }
}

// Update chips display
function updateChips(selectId, containerId) {
    const select = document.getElementById(selectId);
    const container = document.getElementById(containerId);
    const searchInput = document.getElementById(selectId.replace('selected-', '') + '-search');
    
    if (!container) {
        console.error(`Container not found: ${containerId}`);
        return;
    }
    
    const selectedValues = Array.from(select.selectedOptions).map(opt => opt.value);
    
    // Clear container but keep search input and dropdown
    Array.from(container.children).forEach(child => {
        if (!child.classList.contains('chip-input') && 
            !child.classList.contains('chip-dropdown') &&
            child.tagName !== 'SELECT') {
            child.remove();
        }
    });
    
    // Add chips before search input
    selectedValues.forEach(value => {
        const chip = document.createElement('span');
        chip.className = 'chip';
        
        // Create remove button with proper event listener instead of onclick
        const removeBtn = document.createElement('span');
        removeBtn.className = 'remove';
        removeBtn.textContent = '×';
        removeBtn.addEventListener('click', (e) => {
            console.log(`Remove button clicked for: ${value}`);
            e.stopPropagation();
            removeChip(selectId, containerId, value);
        });
        
        chip.appendChild(document.createTextNode(value + ' '));
        chip.appendChild(removeBtn);
        container.insertBefore(chip, searchInput);
    });
    
    // Update placeholder if no selections
    if (selectedValues.length === 0) {
        searchInput.placeholder = `Type to search ${selectId.replace('selected-', '').replace('-', ' ')}...`;
    } else {
        searchInput.placeholder = 'Add more...';
    }
}

// Legacy function for backward compatibility - redirects to chip functions
function removeSelection(selectId, containerId, value) {
    removeChip(selectId, containerId, value);
}

// Get selected values from any select
function getSelectedValues(selectId) {
    const select = document.getElementById(selectId);
    if (select.multiple) {
        return Array.from(select.selectedOptions).map(option => option.value);
    } else {
        return select.value ? [select.value] : [];
    }
}

// Filter data based on current selections
function filterData() {
    let filtered = [...orgData];
    
    // Filter by congress
    const selectedCongress = getSelectedValues('congress-version');
    if (selectedCongress.length > 0) {
        filtered = filtered.filter(d => selectedCongress.includes(d.congress.toString()));
    }
    
    // Filter by organizations
    const selectedOrgs = getSelectedValues('selected-organizations');
    if (selectedOrgs.length > 0) {
        filtered = filtered.filter(d => selectedOrgs.includes(d.combined_name));
    }
    
    // Filter by sponsors
    const selectedSponsors = getSelectedValues('selected-sponsors');
    if (selectedSponsors.length > 0) {
        filtered = filtered.filter(d => selectedSponsors.includes(d.display_name));
    }
    
    // Filter by party
    const selectedParties = getSelectedValues('selected-party');
    if (selectedParties.length > 0) {
        filtered = filtered.filter(d => selectedParties.includes(d.party_name));
    }
    
    // Filter by status
    const selectedStatuses = getSelectedValues('selected-status');
    if (selectedStatuses.length > 0) {
        filtered = filtered.filter(d => selectedStatuses.includes(d.status));
    }
    
    // Filter by issues
    const selectedIssues = getSelectedValues('selected-issues');
    if (selectedIssues.length > 0) {
        const relevantBillIds = issueData
            .filter(d => selectedIssues.includes(d.issue_name))
            .map(d => d.bill_id);
        filtered = filtered.filter(d => relevantBillIds.includes(d.bill_id));
    }
    
    return filtered;
}

// Process data for chart
function processDataForChart(data) {
    const selectedOrgs = getSelectedValues('selected-organizations');
    const numBills = parseInt(document.getElementById('num-bills').value);
    
    // Group by bill and count LDA entries (since count_lda field was removed)
    const billGroups = {};
    data.forEach(d => {
        const key = d.bill_id;
        if (!billGroups[key]) {
            billGroups[key] = {
                bill_id: d.bill_id,
                bill_name: d.bill_name,
                bill_number_full: d.bill_number_full,
                bill_number: d.bill_number,
                bill_type: d.bill_type,
                display_name: d.display_name,
                party_name: d.party_name,
                cosponsor_count: d.cosponsor_count || 0,
                status: d.status,
                congress: d.congress,
                total_count_lda: 0,
                organizations: {}
            };
        }
        billGroups[key].total_count_lda += 1; // Count each LDA entry
        
        // Track organization-specific counts for stacked view
        const orgName = d.combined_name || d.organization_name;
        if (!billGroups[key].organizations[orgName]) {
            billGroups[key].organizations[orgName] = 0;
        }
        billGroups[key].organizations[orgName] += 1;
    });
    
    // Get top bills by LDA count
    const sortedBills = Object.values(billGroups)
        .sort((a, b) => b.total_count_lda - a.total_count_lda)
        .slice(0, numBills)
        .map(bill => {
            // Ensure bill has a valid bill_url
            if (!bill.bill_url || bill.bill_url === 'null' || bill.bill_url === null) {
                bill.bill_url = generateBillUrl(bill);
            }
            return bill;
        });
    
    return { bills: sortedBills, isOrgSelected: selectedOrgs.length > 0 };
}

// Update chart
function updateChart() {
    console.log('Updating chart...');
    
    if (!orgData || orgData.length === 0) {
        console.error('No orgData available for chart');
        return;
    }
    
    try {
        const filtered = filterData();
        console.log('Filtered data length:', filtered.length);
        
        const processed = processDataForChart(filtered);
        console.log('Processed bills:', processed.bills.length);
        
        // Update subtitle
        const selectedOrgs = getSelectedValues('selected-organizations');
        const subtitle = selectedOrgs.length > 0 
            ? selectedOrgs.join(', ')
            : 'All Organizations, by Party';
        document.getElementById('subtitle').textContent = subtitle;
        
        // Destroy existing chart
        if (chart) {
            chart.destroy();
            chart = null;
        }
        
        // Create new chart
        const ctx = document.getElementById('legislation-chart').getContext('2d');
        
        if (processed.isOrgSelected) {
            createStackedChart(ctx, processed.bills, selectedOrgs);
        } else {
            createPartyChart(ctx, processed.bills);
        }
        
        console.log('Chart updated successfully');
    } catch (error) {
        console.error('Error updating chart:', error);
    }
}

// Create party-colored chart
function createPartyChart(ctx, bills) {
    console.log('Creating party chart with', bills.length, 'bills');
    
    if (bills.length === 0) {
        console.warn('No bills to display in party chart');
        return;
    }
    
    const labels = bills.map(b => b.bill_number_full);
    const data = bills.map(b => b.total_count_lda);
    const colors = bills.map(b => partyColors[b.party_name] || '#999999');
    
    console.log('Chart data:', { labels: labels.length, data: data.length, colors: colors.length });
    
    chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Number of LDAs',
                data: data,
                backgroundColor: colors,
                borderColor: colors,
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        generateLabels: function(chart) {
                            const uniqueParties = [...new Set(bills.map(b => b.party_name))];
                            return uniqueParties.map(party => ({
                                text: party,
                                fillStyle: partyColors[party] || '#999999',
                                strokeStyle: partyColors[party] || '#999999',
                                lineWidth: 1,
                                hidden: false
                            }));
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            const bill = bills[context[0].dataIndex];
                            return `${bill.bill_number} ${bill.bill_name}`;
                        },
                        label: function(context) {
                            const bill = bills[context.dataIndex];
                            return [
                                `Bill Status: ${bill.status}`,
                                `Congress: ${bill.congress}th`,
                                `Sponsor: ${bill.display_name}`,
                                `Number of Cosponsors: ${bill.cosponsor_count}`,
                                `Number of LDAs: ${bill.total_count_lda}`
                            ];
                        }
                    }
                }
            },
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const bill = bills[elements[0].index];
                    const billUrl = generateBillUrl(bill);
                    
                    if (billUrl) {
                        const url = `https://app.legis1.com/bill/detail?id=${billUrl}#summary`;
                        console.log('Opening bill URL:', url);
                        window.open(url, '_blank');
                    } else {
                        console.error('Cannot generate URL for bill:', bill);
                        alert('Unable to open bill details - URL could not be generated');
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Number of LDAs'
                    },
                    ticks: {
                        stepSize: 1,
                        precision: 0
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Bill'
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
    
    console.log('Party chart created successfully');
}

// Create organization-stacked chart
function createStackedChart(ctx, bills, selectedOrgs) {
    const labels = bills.map(b => b.bill_number_full);
    const datasets = [];
    
    selectedOrgs.forEach((org, index) => {
        const data = bills.map(bill => bill.organizations[org] || 0);
        datasets.push({
            label: org,
            data: data,
            backgroundColor: organizationColors[index % organizationColors.length],
            borderColor: organizationColors[index % organizationColors.length],
            borderWidth: 1
        });
    });
    
    chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            const bill = bills[context[0].dataIndex];
                            return `${bill.bill_number_full} ${bill.bill_name}`;
                        },
                        afterTitle: function(context) {
                            const bill = bills[context[0].dataIndex];
                            return [
                                `Bill Status: ${bill.status}`,
                                `Congress: ${bill.congress}th`,
                                `Sponsor: ${bill.display_name}`,
                                `Number of Cosponsors: ${bill.cosponsor_count}`,
                                `Number of LDAs: ${bill.total_count_lda}`
                            ];
                        }
                    }
                }
            },
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const bill = bills[elements[0].index];
                    const billUrl = generateBillUrl(bill);
                    
                    if (billUrl) {
                        const url = `https://app.legis1.com/bill/detail?id=${billUrl}#summary`;
                        console.log('Opening bill URL:', url);
                        window.open(url, '_blank');
                    } else {
                        console.error('Cannot generate URL for bill:', bill);
                        alert('Unable to open bill details - URL could not be generated');
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Number of LDAs'
                    },
                    ticks: {
                        stepSize: 1,
                        precision: 0
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Bill'
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Initialize app when page loads
document.addEventListener('DOMContentLoaded', loadManifest);