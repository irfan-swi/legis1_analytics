# Legislation by LDA

A modern web application for analyzing lobbying activity on congressional bills by LDA (Lobbying Disclosure Act) filings.

## Features

- **Interactive Charts**: Horizontal bar charts showing bills with the most LDA activity
- **Multi-select Filters**: Chip-style inputs for filtering by organization, sponsor, party, status, and issues
- **Congress Selection**: Dynamic loading of data by congressional session
- **Responsive Design**: Clean, modern interface that works on all devices
- **Real-time Filtering**: Instant updates as you modify filter selections

## Data Structure

The application uses split data files for GitHub compatibility:

### Data Directory (`data/`)
- `manifest.json` - Contains metadata about available congressional sessions
- `lda_orgs_117.json` - Organization data for 117th Congress (~23MB)
- `lda_orgs_118.json` - Organization data for 118th Congress (~57MB) 
- `lda_orgs_119.json` - Organization data for 119th Congress (~4.4MB)
- `lda_bill_issues.json` - Issue classification data (~2.8MB)

### Why Split Data?
The original `lda_orgs.json` file was 97MB, approaching GitHub's 100MB file limit. Splitting by congressional session provides:
- ✅ GitHub compatibility (all files under 60MB)
- ✅ Faster loading (users only load data for selected congress)
- ✅ Better performance (smaller datasets to filter and process)
- ✅ Logical organization (congress is a natural boundary)

## Usage

### Running Locally
1. Clone the repository
2. Start a local web server:
   ```bash
   # Using Python
   python3 -m http.server 8000
   
   # Using Node.js
   npx serve
   
   # Using PHP
   php -S localhost:8000
   ```
3. Open `http://localhost:8000` in your browser

### Deploying
This app works with any static hosting service:
- GitHub Pages
- Netlify
- Vercel
- AWS S3 + CloudFront
- Any web server with static file support

## Filter Usage

### Congress Selection
- Dropdown shows available congressional sessions with record counts
- Changing congress dynamically loads new data and resets all filters
- Defaults to the most recent congress

### Chip Filters
All multi-select filters use chip-style inputs:

1. **Type to search** - Shows autocomplete dropdown with filtered options
2. **Click to select** - Adds item as a chip
3. **Press Enter** - Selects first visible option
4. **Click × button** - Removes individual chips
5. **Press Backspace** - Removes last chip when input is empty

Available filters:
- **Organization**: Filter by lobbying organizations
- **Sponsor**: Filter by bill sponsors (sorted alphabetically by last name)
- **Sponsor's Party**: Filter by sponsor party affiliation
- **Bill Status**: Filter by current bill status
- **Issue**: Filter by issue categories

## Chart Features

- **Party Colors**: Bills are colored by sponsor's party (Republican red, Democrat blue)
- **Stacked View**: When organizations are selected, shows organization-specific breakdowns
- **Clickable Bars**: Click any bar to open the bill details on legis1.com
- **Responsive**: Adjusts to container size
- **Tooltips**: Hover for detailed bill information

## Technical Details

### Browser Compatibility
- Modern browsers with ES6+ support
- Chrome, Firefox, Safari, Edge (recent versions)

### Dependencies
- Chart.js for data visualization
- No build process required
- Pure JavaScript (ES6+)

### Performance
- Lazy loading of congress data
- Efficient filtering with indexed lookups
- Minimal DOM manipulation
- Optimized for datasets with 50k+ records

## Data Sources

LDA data is sourced from official lobbying disclosure filings and processed to include:
- Bill information (number, title, status, sponsors)
- Organization data (lobbying firms and clients)
- Issue classifications
- Party affiliations
- Congressional session metadata

## Development

### Re-splitting Data
If you need to regenerate the split files:

```bash
# Ensure you have the original lda_orgs.json file
node split_data.js
```

This will recreate the `data/` directory with split files.

### File Structure
```
legislation_by_lda/
├── index.html          # Main application
├── app.js             # Application logic
├── styles.css         # Styling
├── data/              # Split data files
│   ├── manifest.json
│   ├── lda_orgs_117.json
│   ├── lda_orgs_118.json
│   ├── lda_orgs_119.json
│   └── lda_bill_issues.json
├── split_data.js      # Data splitting utility
└── README.md          # This file
```

## License

This project is for educational and research purposes. LDA data is public domain.