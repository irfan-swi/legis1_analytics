# Congressional Tweet Sentiment Analysis

An interactive web application for analyzing sentiment trends in tweets by members of Congress.

## 🚀 Quick Start

**Run the app locally:**
```bash
python serve.py
```

Then open your browser to `http://localhost:8080`

## 📊 Features

- **Interactive Sentiment Timeline**: Line chart showing daily sentiment by party (Democrat, Republican, Independent, Combined)
- **Advanced Filtering**: Filter by chamber, party, state, member, issue area, and date range
- **Content Search**: Search tweets by keyword with debounced input
- **Member Rankings**: View most positive/negative members with detailed stats
- **Summary Statistics**: Real-time stats including total tweets, average sentiment, member count, and date range

## 🛠️ Technical Optimizations

### Data Architecture
- **Smart File Loading**: Only loads relevant data files based on selected date range
- **Optimized File Sizes**: Data split into chunks <6.6MB for fast loading
- **Total Dataset**: 847,634 tweets from 456 members across 21 issue areas
- **Efficient Storage**: 79MB total data size (under GitHub's 100MB limit)

### Performance Features
- **DuckDB-WASM**: In-browser analytics database for fast queries
- **Incremental Loading**: Loads 2-4 files instead of all 22 files based on filters
- **Query Optimization**: Explicit type casting and optimized SQL queries
- **Search Debouncing**: 500ms delay for search to reduce server load
- **Memory Management**: Efficient connection handling and error recovery

## 📁 Project Structure

```
├── index.html              # Main application file
├── serve.py                # Local development server
├── data/                   # Data files directory
│   ├── metadata.json       # Dataset metadata and file index
│   ├── sample.parquet      # Sample data for testing
│   └── tweets_*.parquet    # Optimized data files by time period
└── scripts/
    └── prepare_data.py     # Data preparation script
```

## 🔧 Data Preparation

To recreate the optimized data files from your CSV:

```bash
python scripts/prepare_data.py
```

This script:
- Splits large files into monthly chunks for better performance
- Creates metadata for smart file loading
- Generates a sample file for testing
- Optimizes parquet compression

## 📈 Usage Tips

1. **Date Range**: Default shows last 1 year of data for optimal performance
2. **Search**: Use 3+ characters for keyword search to avoid overwhelming results
3. **Large Datasets**: The app automatically loads only relevant data files
4. **Performance**: Monitor browser console for query timing information

## 🔍 Data Schema

Each tweet record includes:
- `display_name`: Member name
- `party_name`: Political party (Democrat, Republican, Independent)
- `chamber`: House or Senate
- `us_state_id`: State abbreviation
- `person_id`: Unique member identifier (for Legis1 links)
- `score`: Sentiment score (-1 to +1)
- `pub_date`: Publication date (YYYY-MM-DD)
- `content`: Tweet text content
- `issue_name`: Tagged issue area

## 🌐 Deployment

For GitHub Pages or similar static hosting:
1. All files are under 100MB (GitHub limit)
2. Uses CDN resources (Chart.js, DuckDB-WASM)
3. No server-side dependencies required
4. CORS headers handled in serve.py for development

## ⚠️ Important Notes

- **CORS**: Must be served from a web server (not file://) due to browser security
- **Browser Compatibility**: Requires modern browser with WebAssembly support
- **Memory Usage**: Optimized for datasets up to ~1M rows
- **File Loading**: First load may take 10-30 seconds depending on date range

## 🐛 Troubleshooting

**"Table with name tweets does not exist"**
- Ensure you're running from a web server (`python serve.py`)
- Check browser console for CORS errors

**Slow Loading**
- Narrow date range to load fewer files
- Clear browser cache
- Check network connection

**No Data Showing**
- Verify data files exist in `/data` directory
- Check date range includes available data (2023-2025)
- Run data preparation script if needed