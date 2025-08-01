// Data loader for lawmaker Twitter activity
class DataLoader {
    constructor() {
        this.lawmakers = new Map();
        this.tweetData = new Map();
        this.loadedMonths = new Set();
        this.index = null;
        this.issues = [];
    }
    
    async init() {
        // Load index and lawmakers (small files)
        const [indexResponse, lawmakersResponse] = await Promise.all([
            fetch('data/index.json'),
            fetch('data/lawmakers.json')
        ]);
        
        this.index = await indexResponse.json();
        const lawmakersArray = await lawmakersResponse.json();
        
        // Create lawmakers map
        lawmakersArray.forEach(lm => {
            this.lawmakers.set(lm.person_id, lm);
        });
        
        // Store issues list
        this.issues = this.index.issues || [];
        
        // Load last 3 months by default
        const recentMonths = this.index.months.slice(-3);
        await this.loadMonths(recentMonths);
    }
    
    async loadMonths(months) {
        const monthsToLoad = months.filter(m => !this.loadedMonths.has(m));
        
        if (monthsToLoad.length === 0) return;
        
        // Show loading indicator
        console.log(`Loading data for months: ${monthsToLoad.join(', ')}`);
        
        // Load compressed monthly data
        const promises = monthsToLoad.map(async (month) => {
            const response = await fetch(`data/tweets-${month}.json.gz`);
            const compressed = await response.arrayBuffer();
            
            // Decompress in browser
            const decompressed = await this.decompress(compressed);
            const data = JSON.parse(decompressed);
            
            // Store in memory
            data.forEach(record => {
                const key = `${record.person_id}_${record.issue_name}_${record.month}`;
                this.tweetData.set(key, record);
            });
            
            this.loadedMonths.add(month);
        });
        
        await Promise.all(promises);
    }
    
    async decompress(compressed) {
        // Use browser's native decompression
        const ds = new DecompressionStream('gzip');
        const decompressedStream = new Response(compressed).body.pipeThrough(ds);
        return new Response(decompressedStream).text();
    }
    
    getFilteredData(filters) {
        const { startDate, endDate, issue, chamber, party } = filters;
        
        // Ensure we have the needed months loaded
        const neededMonths = this.getMonthsInRange(startDate, endDate);
        const unloadedMonths = neededMonths.filter(m => !this.loadedMonths.has(m));
        
        if (unloadedMonths.length > 0) {
            // Return promise that loads data first
            return this.loadMonths(unloadedMonths).then(() => this.filterData(filters));
        }
        
        return Promise.resolve(this.filterData(filters));
    }
    
    filterData(filters) {
        const aggregated = new Map();
        
        for (const [key, record] of this.tweetData) {
            const lawmaker = this.lawmakers.get(record.person_id);
            if (!lawmaker) continue;
            
            // Apply filters
            if (filters.issue !== 'All' && record.issue_name !== filters.issue) continue;
            if (filters.chamber !== 'Both Chambers' && lawmaker.chamber !== filters.chamber) continue;
            if (filters.party !== 'All Parties' && !lawmaker.party_name.includes(filters.party)) continue;
            
            // Check date range
            const [year, month] = record.month.split('-').map(Number);
            const recordDate = new Date(year, month - 1, 1);
            
            if (recordDate < filters.startDate || recordDate > filters.endDate) continue;
            
            // Aggregate by person
            const personId = record.person_id;
            if (!aggregated.has(personId)) {
                aggregated.set(personId, {
                    person_id: personId,
                    display_name: lawmaker.display_name,
                    party_clean: lawmaker.party_name,
                    posts: 0
                });
            }
            aggregated.get(personId).posts += record.count;
        }
        
        return Array.from(aggregated.values());
    }
    
    getMonthsInRange(startDate, endDate) {
        const months = [];
        const current = new Date(startDate);
        current.setDate(1); // Start at beginning of month
        
        while (current <= endDate) {
            const year = current.getFullYear();
            const month = current.getMonth() + 1;
            months.push(`${year}-${month}`);
            current.setMonth(current.getMonth() + 1);
        }
        
        return months;
    }
    
    getDateRange() {
        if (!this.index || !this.index.months || this.index.months.length === 0) {
            return { start: new Date(), end: new Date() };
        }
        
        const firstMonth = this.index.months[0];
        const lastMonth = this.index.months[this.index.months.length - 1];
        
        const [startYear, startMonth] = firstMonth.split('-').map(Number);
        const [endYear, endMonth] = lastMonth.split('-').map(Number);
        
        return {
            start: new Date(startYear, startMonth - 1, 1),
            end: new Date(endYear, endMonth - 1, 1)
        };
    }
}

// Export for use in main app
window.DataLoader = DataLoader;
