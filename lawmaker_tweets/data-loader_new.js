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
        
        // Store issues list (excluding "All" if present)
        this.issues = (this.index.issues || []).filter(i => i !== 'All');
        
        // Sort months chronologically before taking last months
        const sortedMonths = [...this.index.months].sort((a, b) => {
            const [yearA, monthA] = a.split('-').map(Number);
            const [yearB, monthB] = b.split('-').map(Number);
            return yearA === yearB ? monthA - monthB : yearA - yearB;
        });
        
        this.index.months = sortedMonths;
        
        // Load last 3 months by default
        const lastThreeMonths = sortedMonths.slice(-3);
        if (lastThreeMonths.length > 0) {
            await this.loadMonths(lastThreeMonths);
        }
    }
    
    async loadMonths(months) {
        const monthsToLoad = months.filter(m => !this.loadedMonths.has(m));
        
        if (monthsToLoad.length === 0) return;
        
        console.log(`Loading data for months: ${monthsToLoad.join(', ')}`);
        
        const promises = monthsToLoad.map(async (month) => {
            const response = await fetch(`data/tweets-${month}.json.gz`);
            const compressed = await response.arrayBuffer();
            
            const decompressed = await this.decompress(compressed);
            const data = JSON.parse(decompressed);
            
            data.forEach(record => {
                const key = `${record.person_id}_${record.issue_name}_${record.month}`;
                this.tweetData.set(key, record);
            });
            
            this.loadedMonths.add(month);
        });
        
        await Promise.all(promises);
        console.log(`Successfully loaded ${monthsToLoad.length} month(s). Total records: ${this.tweetData.size}`);
    }
    
    async decompress(compressed) {
        const ds = new DecompressionStream('gzip');
        const decompressedStream = new Response(compressed).body.pipeThrough(ds);
        return new Response(decompressedStream).text();
    }
    
    getFilteredData(filters) {
        const { startDate, endDate, issue, chamber, party } = filters;
        
        const neededMonths = this.getMonthsInRange(startDate, endDate);
        const unloadedMonths = neededMonths.filter(m => !this.loadedMonths.has(m));
        
        if (unloadedMonths.length > 0) {
            return this.loadMonths(unloadedMonths).then(() => this.filterData(filters));
        }
        
        return Promise.resolve(this.filterData(filters));
    }
    
    filterData(filters) {
        const aggregated = new Map();
        
        console.log(`Filtering ${this.tweetData.size} records with:`, {
            startDate: filters.startDate,
            endDate: filters.endDate,
            issue: filters.issue,
            chamber: filters.chamber,
            party: filters.party
        });
        
        let recordsProcessed = 0;
        let recordsPassed = 0;
        
        for (const [key, record] of this.tweetData) {
            recordsProcessed++;
            
            const lawmaker = this.lawmakers.get(record.person_id);
            if (!lawmaker) continue;
            
            // CRITICAL FIX: Handle "All" issue properly including NULL/undefined values
            // When filtering by "All", only use records with issue_name="All"
            // When filtering by specific issue, only use records with that specific issue (skip "All")
            // When filtering by specific issue OR "All", include tweets with no issue (NULL/undefined)
            if (filters.issue === 'All') {
                // Only include records with issue_name="All" (the deduplicated count)
                // OR records with no issue assignment (NULL/undefined)
                if (record.issue_name !== 'All' && record.issue_name != null) continue;
            } else {
                // Only include records matching the specific issue (skip "All")
                // OR records with no issue assignment (NULL/undefined)
                if (record.issue_name === 'All') continue;
                if (record.issue_name != null && record.issue_name !== filters.issue) continue;
            }
            
            // Apply other filters
            if (filters.chamber !== 'Both Chambers' && lawmaker.chamber !== filters.chamber) continue;
            if (filters.party !== 'All Parties' && !lawmaker.party_name.includes(filters.party)) continue;
            
            // Check date range
            const [year, month] = record.month.split('-').map(Number);
            const recordDate = new Date(year, month - 1, 1);
            
            if (recordDate < filters.startDate || recordDate > filters.endDate) continue;
            
            recordsPassed++;
            
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
        
        console.log(`Filtered ${recordsProcessed} records, ${recordsPassed} passed filters, ${aggregated.size} unique lawmakers`);
        
        return Array.from(aggregated.values());
    }
    
    getMonthsInRange(startDate, endDate) {
        const months = [];
        const current = new Date(startDate);
        current.setDate(1);
        
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
