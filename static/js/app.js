// Modern PDF Web Crawler Application

class PDFCrawlerApp {
    constructor() {
        this.isRunning = false;
        this.statusInterval = null;
        this.resultsInterval = null;
        this.currentPage = 1;
        this.itemsPerPage = 10;
        this.filteredPdfs = [];
        this.allPdfs = [];
        this.maxDepth = 3;
        this.isAutoDownloadEnabled = false;
        this.selectedDownloadDir = ''; // No default - user must specify
        
        // Clear any previous results on page load
        this.clearResults();
        
        this.initializeEventListeners();
        this.updateStatus();
        this.setupDirectoryPicker();
    }
    
    initializeEventListeners() {
        // Form submission
        document.getElementById('crawlForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.startCrawling();
        });
        
        // Stop button
        document.getElementById('stopBtn').addEventListener('click', () => {
            this.stopCrawling();
        });
        
        // Depth input handler - removed as we now use direct number input
        
        // Search and filter
        document.getElementById('searchInput').addEventListener('input', (e) => {
            this.filterResults();
        });
        
        document.getElementById('statusFilter').addEventListener('change', (e) => {
            this.filterResults();
        });
        
        // URL normalization preview
        document.getElementById('websiteUrl').addEventListener('input', (e) => {
            this.showUrlPreview(e.target.value);
        });
        
        // Pagination
        document.getElementById('prevPage').addEventListener('click', () => {
            this.previousPage();
        });
        
        document.getElementById('nextPage').addEventListener('click', () => {
            this.nextPage();
        });
        
        // Auto-download toggle
        document.getElementById('autoDownloadToggle').addEventListener('click', () => {
            this.toggleAutoDownload();
        });
    }
    
    setupDirectoryPicker() {
        const selectDirBtn = document.getElementById('selectDirBtn');
        const downloadDirInput = document.getElementById('downloadDir');
        
        // Handle Browse button click
        selectDirBtn.addEventListener('click', async () => {
            try {
                // Show loading state
                selectDirBtn.disabled = true;
                selectDirBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Opening...';
                
                // Call server to open native file dialog
                const response = await fetch('/api/select-directory', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Update input with selected path
                    downloadDirInput.value = data.path;
                    this.selectedDownloadDir = data.path;
                    this.showToast(`Selected: ${data.path}`, 'success');
                    console.log('Directory selected via system dialog:', data.path);
                } else {
                    // User cancelled or error occurred
                    if (data.message) {
                        this.showToast(data.message, 'info');
                    }
                }
            } catch (error) {
                console.error('Error selecting directory:', error);
                this.showToast('Error opening directory selector. You can type the path manually.', 'error');
            } finally {
                // Restore button state
                selectDirBtn.disabled = false;
                selectDirBtn.innerHTML = '<i class="fas fa-folder-open"></i> Browse';
            }
        });
        
        // Allow manual editing of the path
        downloadDirInput.addEventListener('input', (e) => {
            this.selectedDownloadDir = e.target.value.trim();
            console.log('Directory path manually updated:', this.selectedDownloadDir);
        });
    }
    

    
    toggleAutoDownload() {
        this.isAutoDownloadEnabled = !this.isAutoDownloadEnabled;
        const toggle = document.getElementById('autoDownloadToggle');
        
        if (this.isAutoDownloadEnabled) {
            toggle.classList.add('active');
            this.showToast('Auto-download enabled', 'success');
        } else {
            toggle.classList.remove('active');
            this.showToast('Auto-download disabled', 'info');
        }
        
        console.log('Auto-download:', this.isAutoDownloadEnabled);
    }
    
    async startCrawling() {
        let websiteUrl = document.getElementById('websiteUrl').value.trim();
        const downloadDir = this.selectedDownloadDir || document.getElementById('downloadDir').value.trim();
        const autoDownload = this.isAutoDownloadEnabled;
        const maxDepth = parseInt(document.getElementById('maxDepth').value) || 3;
        
        if (!websiteUrl) {
            this.showToast('Please enter a website URL', 'error');
            return;
        }
        
        // Validate depth
        if (maxDepth < 1 || maxDepth > 10) {
            this.showToast('Crawl depth must be between 1 and 10', 'error');
            document.getElementById('maxDepth').focus();
            return;
        }
        
        // Validate download directory if auto-download is enabled
        if (autoDownload && !downloadDir) {
            this.showToast('Please enter a download directory path for auto-download', 'error');
            document.getElementById('downloadDir').focus();
            return;
        }
        
        // Normalize the URL
        websiteUrl = this.normalizeUrl(websiteUrl);
        
        // Update the input field with the normalized URL
        document.getElementById('websiteUrl').value = websiteUrl;
        
        try {
            this.updateStatusIndicator('running', 'Crawling...');
            this.showProgressSection();
            
            const response = await fetch('/api/start-crawl', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    website_url: websiteUrl,
                    max_depth: maxDepth,
                    download_dir: downloadDir,
                    auto_download: autoDownload
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.isRunning = true;
                this.updateButtonStates();
                this.startStatusUpdates();
                this.startResultsUpdates();
                this.showToast('Crawling started successfully!', 'success');
            } else {
                this.updateStatusIndicator('stopped', 'Error');
                this.showToast(data.error || 'Failed to start crawling', 'error');
            }
        } catch (error) {
            this.updateStatusIndicator('stopped', 'Error');
            this.showToast('Network error: ' + error.message, 'error');
        }
    }
    
    async stopCrawling() {
        try {
            const response = await fetch('/api/stop-crawl', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.isRunning = false;
                this.updateButtonStates();
                this.stopStatusUpdates();
                this.stopResultsUpdates();
                this.updateStatusIndicator('stopped', 'Stopped');
                this.showToast('Crawling stopped', 'info');
            } else {
                this.showToast(data.error || 'Failed to stop crawling', 'error');
            }
        } catch (error) {
            this.showToast('Network error: ' + error.message, 'error');
        }
    }
    
    updateStatusIndicator(status, text) {
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        
        statusDot.className = 'status-dot';
        statusDot.classList.add(status);
        statusText.textContent = text;
    }
    
    showProgressSection() {
        document.getElementById('progressSection').style.display = 'block';
    }
    
    showUrlPreview(inputValue) {
        const urlInput = document.getElementById('websiteUrl');
        const helpText = urlInput.parentElement.nextElementSibling;
        
        if (inputValue.trim()) {
            const normalizedUrl = this.normalizeUrl(inputValue);
            if (normalizedUrl !== inputValue.trim()) {
                helpText.innerHTML = `
                    <small class="text-muted">
                        <i class="fas fa-info-circle"></i>
                        Will be normalized to: <strong>${normalizedUrl}</strong>
                    </small>
                `;
            } else {
                helpText.innerHTML = `
                    <small class="text-muted">
                        <i class="fas fa-info-circle"></i>
                        Enter domain name (e.g., "example.com" or "www.example.com"). 
                        The app will automatically add https:// and www if needed.
                    </small>
                `;
            }
        } else {
            helpText.innerHTML = `
                <small class="text-muted">
                    <i class="fas fa-info-circle"></i>
                    Enter domain name (e.g., "example.com" or "www.example.com"). 
                    The app will automatically add https:// and www if needed.
                </small>
            `;
        }
    }
    
    async updateStatus() {
        try {
            const response = await fetch('/api/status');
            const status = await response.json();
            
            // Update progress stats
            document.getElementById('currentDepth').textContent = status.current_depth || 0;
            document.getElementById('urlsProcessed').textContent = status.urls_processed || 0;
            document.getElementById('pdfsFound').textContent = status.pdfs_found || 0;
            
            // Update progress bar
            const maxUrls = Math.max(status.urls_processed || 1, 1);
            const progress = Math.min((status.urls_processed / maxUrls) * 100, 100);
            document.getElementById('progressFill').style.width = `${progress}%`;
            document.getElementById('progressText').textContent = `${Math.round(progress)}%`;
            
            // Update status indicator
            if (status.is_running) {
                this.updateStatusIndicator('running', 'Running');
            } else if (status.error) {
                this.updateStatusIndicator('stopped', 'Error');
            } else {
                this.updateStatusIndicator('stopped', 'Ready');
            }
            
            // Update button states based on status
            if (status.is_running !== this.isRunning) {
                this.isRunning = status.is_running;
                this.updateButtonStates();
                
                if (!status.is_running) {
                    this.stopStatusUpdates();
                    this.stopResultsUpdates();
                }
            }
            
        } catch (error) {
            console.error('Error updating status:', error);
        }
    }
    
    async updateResults() {
        try {
            const response = await fetch('/api/results');
            const data = await response.json();
            
            console.log('API Response:', data); // Debug log
            this.allPdfs = data.pdfs || [];
            console.log('All PDFs:', this.allPdfs); // Debug log
            this.filterResults();
            
        } catch (error) {
            console.error('Error updating results:', error);
        }
    }
    
    filterResults() {
        const searchTerm = document.getElementById('searchInput').value.toLowerCase();
        const statusFilter = document.getElementById('statusFilter').value;
        
        console.log('Filtering - Search term:', searchTerm, 'Status filter:', statusFilter); // Debug log
        
        this.filteredPdfs = this.allPdfs.filter(pdf => {
            const matchesSearch = !searchTerm || 
                pdf.filename.toLowerCase().includes(searchTerm) ||
                pdf.source_url.toLowerCase().includes(searchTerm);
            
            const matchesStatus = !statusFilter || pdf.status === statusFilter;
            
            return matchesSearch && matchesStatus;
        });
        
        console.log('Filtered PDFs:', this.filteredPdfs); // Debug log
        
        this.currentPage = 1;
        this.renderResults();
    }
    
    renderResults() {
        const tbody = document.getElementById('resultsBody');
        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = startIndex + this.itemsPerPage;
        const pagePdfs = this.filteredPdfs.slice(startIndex, endIndex);
        
        console.log('Rendering results - Page PDFs:', pagePdfs); // Debug log
        console.log('All PDFs count:', this.allPdfs.length, 'Filtered PDFs count:', this.filteredPdfs.length); // Debug log
        
        if (pagePdfs.length === 0) {
            console.log('No PDFs to display - showing empty state'); // Debug log
            tbody.innerHTML = `
                <tr class="empty-state">
                    <td colspan="5">
                        <div class="empty-message">
                            <i class="fas fa-search"></i>
                            <h4>${this.allPdfs.length === 0 ? 'No PDFs Found Yet' : 'No PDFs Match Your Search'}</h4>
                            <p>${this.allPdfs.length === 0 ? 'Start crawling to discover PDF files on the website' : 'Try adjusting your search criteria'}</p>
                        </div>
                    </td>
                </tr>
            `;
        } else {
            console.log('Displaying', pagePdfs.length, 'PDFs'); // Debug log
            tbody.innerHTML = pagePdfs.map(pdf => this.createPdfRow(pdf)).join('');
        }
        
        this.updatePagination();
    }
    
    createPdfRow(pdf) {
        const size = pdf.size ? this.formatFileSize(pdf.size) : 'Unknown';
        const statusBadge = this.getStatusBadge(pdf.status);
        
        return `
            <tr>
                <td>
                    <div class="file-info">
                        <div class="file-icon">
                            <i class="fas fa-file-pdf"></i>
                        </div>
                        <div class="file-details">
                            <div class="file-name">${this.escapeHtml(pdf.filename)}</div>
                            <div class="file-url text-truncate">${this.escapeHtml(pdf.url)}</div>
                        </div>
                    </div>
                </td>
                <td>
                    <div class="source-info">
                        <a href="${this.escapeHtml(pdf.source_url)}" target="_blank" class="source-link">
                            ${this.escapeHtml(pdf.source_url)}
                        </a>
                    </div>
                </td>
                <td>
                    <span class="file-size">${size}</span>
                </td>
                <td>${statusBadge}</td>
                <td>
                    <div class="file-actions">
                        <a href="${this.escapeHtml(pdf.url)}" target="_blank" 
                           class="btn btn-outline-primary" title="Open PDF">
                            <i class="fas fa-external-link-alt"></i>
                        </a>
                        ${!pdf.local_path ? `
                            <button class="btn btn-outline-success" onclick="app.downloadSinglePdf('${this.escapeHtml(pdf.url)}')" 
                                    title="Download PDF">
                                <i class="fas fa-download"></i>
                            </button>
                        ` : `
                            <button class="btn btn-outline-info" onclick="app.openLocalFile('${this.escapeHtml(pdf.local_path)}')" 
                                    title="Open Local File">
                                <i class="fas fa-folder-open"></i>
                            </button>
                        `}
                    </div>
                </td>
            </tr>
        `;
    }
    
    getStatusBadge(status) {
        const badges = {
            'found': '<span class="badge badge-info">Found</span>',
            'downloaded': '<span class="badge badge-success">Downloaded</span>',
            'download_failed': '<span class="badge badge-danger">Failed</span>',
            'already_exists': '<span class="badge badge-warning">Exists</span>',
            'unverified': '<span class="badge badge-warning">Unverified</span>'
        };
        
        return badges[status] || `<span class="badge badge-secondary">${status}</span>`;
    }
    
    formatFileSize(bytes) {
        if (!bytes) return 'Unknown';
        
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }
    
    updatePagination() {
        const totalPages = Math.ceil(this.filteredPdfs.length / this.itemsPerPage);
        const paginationContainer = document.getElementById('paginationContainer');
        
        if (this.filteredPdfs.length > this.itemsPerPage) {
            paginationContainer.style.display = 'flex';
            
            document.getElementById('currentPage').textContent = this.currentPage;
            document.getElementById('totalPages').textContent = totalPages;
            document.getElementById('showingCount').textContent = 
                Math.min(this.currentPage * this.itemsPerPage, this.filteredPdfs.length);
            document.getElementById('totalCount').textContent = this.filteredPdfs.length;
            
            document.getElementById('prevPage').disabled = this.currentPage <= 1;
            document.getElementById('nextPage').disabled = this.currentPage >= totalPages;
        } else {
            paginationContainer.style.display = 'none';
        }
    }
    
    previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.renderResults();
        }
    }
    
    nextPage() {
        const totalPages = Math.ceil(this.filteredPdfs.length / this.itemsPerPage);
        if (this.currentPage < totalPages) {
            this.currentPage++;
            this.renderResults();
        }
    }
    
    async downloadSinglePdf(url) {
        try {
            const downloadDir = document.getElementById('downloadDir').value || 'downloads';
            
            const response = await fetch('/api/download-pdf', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: url,
                    download_dir: downloadDir
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showToast(`PDF downloaded: ${data.filename}`, 'success');
                this.updateResults(); // Refresh the results to show updated status
            } else {
                this.showToast(data.error || 'Failed to download PDF', 'error');
            }
        } catch (error) {
            this.showToast('Network error: ' + error.message, 'error');
        }
    }
    
    openLocalFile(filepath) {
        this.showToast(`Local file: ${filepath}`, 'info');
    }
    
    updateButtonStates() {
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        
        if (this.isRunning) {
            startBtn.style.display = 'none';
            stopBtn.style.display = 'flex';
        } else {
            startBtn.style.display = 'flex';
            stopBtn.style.display = 'none';
        }
    }
    
    startStatusUpdates() {
        this.statusInterval = setInterval(() => {
            this.updateStatus();
        }, 2000);
    }
    
    stopStatusUpdates() {
        if (this.statusInterval) {
            clearInterval(this.statusInterval);
            this.statusInterval = null;
        }
    }
    
    startResultsUpdates() {
        this.resultsInterval = setInterval(() => {
            this.updateResults();
        }, 5000);
    }
    
    stopResultsUpdates() {
        if (this.resultsInterval) {
            clearInterval(this.resultsInterval);
            this.resultsInterval = null;
        }
    }
    
    clearResults() {
        // Clear the results display
        this.allPdfs = [];
        this.filteredPdfs = [];
        this.currentPage = 1;
        
        // Clear the results table
        const tbody = document.querySelector('#resultsTable tbody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">No PDFs found yet. Start crawling to find PDFs.</td></tr>';
        }
        
        // Update counts
        const totalCount = document.getElementById('totalCount');
        const filteredCount = document.getElementById('filteredCount');
        if (totalCount) totalCount.textContent = '0';
        if (filteredCount) filteredCount.textContent = '0';
        
        // Hide results section if visible
        const resultsSection = document.getElementById('resultsSection');
        if (resultsSection) {
            resultsSection.style.display = 'none';
        }
    }
    
    showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toastContainer');
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = {
            'success': 'fas fa-check-circle',
            'error': 'fas fa-exclamation-circle',
            'warning': 'fas fa-exclamation-triangle',
            'info': 'fas fa-info-circle'
        };
        
        const titles = {
            'success': 'Success',
            'error': 'Error',
            'warning': 'Warning',
            'info': 'Info'
        };
        
        toast.innerHTML = `
            <div class="toast-header">
                <div class="toast-title">
                    <i class="${icons[type]}"></i>
                    ${titles[type]}
                </div>
                <button class="toast-close" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 5000);
    }
    
    normalizeUrl(url) {
        // Remove leading/trailing whitespace
        url = url.trim();
        
        // If no protocol specified, add https://
        if (!url.match(/^https?:\/\//)) {
            url = 'https://' + url;
        }
        
        return url;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the application when the page loads
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new PDFCrawlerApp();
});
