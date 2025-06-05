// Script to split large lda_orgs.json file by congress for GitHub compatibility
const fs = require('fs');
const path = require('path');

async function splitDataByCongress() {
    console.log('Loading lda_orgs.json...');
    
    try {
        const data = JSON.parse(fs.readFileSync('lda_orgs.json', 'utf8'));
        console.log(`Loaded ${data.length} records`);
        
        // Group by congress
        const congressGroups = {};
        data.forEach(record => {
            const congress = record.congress;
            if (!congressGroups[congress]) {
                congressGroups[congress] = [];
            }
            congressGroups[congress].push(record);
        });
        
        // Create data directory
        const dataDir = 'data';
        if (!fs.existsSync(dataDir)) {
            fs.mkdirSync(dataDir);
        }
        
        // Write each congress to separate file
        const congressList = Object.keys(congressGroups).sort((a, b) => b - a); // Newest first
        console.log(`Found ${congressList.length} congresses: ${congressList.join(', ')}`);
        
        const fileSizes = {};
        congressList.forEach(congress => {
            const filename = `lda_orgs_${congress}.json`;
            const filepath = path.join(dataDir, filename);
            const congressData = congressGroups[congress];
            
            fs.writeFileSync(filepath, JSON.stringify(congressData, null, 0));
            const stats = fs.statSync(filepath);
            const sizeMB = (stats.size / (1024 * 1024)).toFixed(1);
            fileSizes[congress] = sizeMB;
            
            console.log(`Created ${filename}: ${congressData.length} records, ${sizeMB}MB`);
        });
        
        // Create manifest file
        const manifest = {
            congresses: congressList.map(congress => ({
                congress: parseInt(congress),
                filename: `lda_orgs_${congress}.json`,
                records: congressGroups[congress].length,
                sizeMB: parseFloat(fileSizes[congress])
            })),
            totalRecords: data.length,
            splitDate: new Date().toISOString()
        };
        
        fs.writeFileSync(path.join(dataDir, 'manifest.json'), JSON.stringify(manifest, null, 2));
        console.log('Created manifest.json');
        
        // Copy issues file to data directory (it's small enough)
        if (fs.existsSync('lda_bill_issues.json')) {
            fs.copyFileSync('lda_bill_issues.json', path.join(dataDir, 'lda_bill_issues.json'));
            console.log('Copied lda_bill_issues.json to data directory');
        }
        
        console.log('\nSplit complete! Files are in the "data" directory.');
        console.log('Update your app to load data from the data/ directory.');
        
    } catch (error) {
        console.error('Error splitting data:', error);
    }
}

splitDataByCongress();