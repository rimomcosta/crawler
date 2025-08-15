# 🕷️ PDF Web Crawler

A powerful and user-friendly web crawler designed to find and download PDF files from websites. Built with Python (Flask) and modern JavaScript, featuring a beautiful UI and real-time progress tracking.

![PDF Web Crawler Screenshot](screenshot.jpg?v=2)

## ✨ Features

- **🔍 Smart PDF Detection**: Automatically finds PDFs in links, embedded content, and various URL patterns
- **📊 Customizable Depth**: Crawl websites from 1 to 10 levels deep
- **💾 Auto-Download**: Download PDFs immediately as they're found or review them first
- **📁 System Directory Picker**: Native folder selection dialog for choosing download location
- **🎯 Real-time Progress**: Live updates showing crawl progress and found PDFs
- **🔎 Search & Filter**: Filter results by filename or download status
- **🌐 Smart URL Handling**: Automatically handles various URL formats (with/without http://, www, etc.)
- **⚡ Concurrent Crawling**: Multi-threaded crawling for faster results
- **🎨 Modern UI**: Clean, responsive interface with smooth animations

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- pip (Python package manager)
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/rimomcosta/crawler.git
cd crawler
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run the application:**
```bash
python app.py
```

4. **Open your browser:**
Navigate to `http://localhost:8080`

## 📖 How to Use

1. **Enter Website URL**: Type or paste the website URL you want to crawl
   - The app automatically adds `https://` if needed
   - Works with or without `www`

2. **Set Crawl Depth**: Choose how deep to crawl (1-10 levels)
   - Level 1: Only the main page
   - Level 2: Main page + directly linked pages
   - Level 3+: Deeper crawling for comprehensive results

3. **Select Download Directory**: 
   - Click "Browse" to open system folder picker
   - Or manually enter the full path

4. **Enable Auto-Download** (Optional):
   - Toggle ON: PDFs download immediately when found
   - Toggle OFF: Review PDFs first, then download selectively

5. **Start Crawling**: Click the "Start Crawling" button
   - Watch real-time progress
   - See PDFs being discovered
   - Stop anytime with the "Stop" button

6. **Manage Results**:
   - Search PDFs by filename
   - Filter by status (All/Downloaded/Pending/Failed)
   - Download individual PDFs
   - View source pages where PDFs were found

## 🛠️ Technical Details

### Backend (Python/Flask)
- **Framework**: Flask 2.3.3
- **Web Scraping**: BeautifulSoup4 + Requests
- **Concurrency**: ThreadPoolExecutor for parallel crawling
- **PDF Detection**: Multiple strategies including URL patterns, content-type headers, and embedded content

### Frontend
- **Pure JavaScript**: No framework dependencies
- **Responsive Design**: Works on desktop and mobile
- **Real-time Updates**: Polling for live progress
- **Modern CSS**: Custom properties, flexbox, and grid layouts

### Key Files
- `app.py`: Flask application and API endpoints
- `crawler.py`: Core crawling logic and PDF detection
- `static/js/app.js`: Frontend application logic
- `static/css/style.css`: Modern styling
- `templates/index.html`: Main UI template

## 🔧 Configuration

### Crawler Settings
- **Max Workers**: 5 concurrent threads (configurable in `crawler.py`)
- **Timeout**: 10 seconds per request
- **User Agent**: Chrome 91.0 (customizable)

### Supported PDF Detection
- Direct PDF links (`.pdf` extension)
- PDF URLs with patterns (`/pdf/`, `/download/`, `/file/`)
- Embedded PDFs (`<embed>`, `<iframe>`, `<object>`)
- Content-Type header detection

## 📝 API Endpoints

- `GET /`: Main application UI
- `POST /api/start-crawl`: Start crawling a website
- `POST /api/stop-crawl`: Stop current crawl
- `GET /api/status`: Get current crawl status
- `GET /api/results`: Get found PDFs
- `POST /api/select-directory`: Open system directory picker
- `POST /api/download-pdf`: Download a specific PDF

## 🐛 Troubleshooting

### Port Already in Use
If port 8080 is busy, you can change it in `app.py`:
```python
app.run(debug=True, port=8081)  # Change to any available port
```

### PDFs Not Downloading
- Ensure you have write permissions to the selected directory
- Check that the directory path is absolute (e.g., `/Users/username/Downloads`)
- Verify auto-download is enabled if you want immediate downloads

### Crawler Stopping Early
- Some websites may have rate limiting
- Try reducing the crawl depth
- Check the console for any error messages

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with Flask and BeautifulSoup4
- UI inspired by modern web design principles
- Icons from Font Awesome

## 📧 Contact

For questions or support, please open an issue on GitHub.

---
Made with ❤️