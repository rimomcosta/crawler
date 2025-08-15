from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from crawler import PDFCrawler
import os
import threading
import time
import json
from datetime import datetime
import platform
import subprocess

app = Flask(__name__)
CORS(app)

# Global crawler instance
crawler = None
crawler_thread = None

@app.route('/')
def index():
    response = render_template('index.html')
    # Prevent caching during development
    response = app.make_response(response)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/start-crawl', methods=['POST'])
def start_crawl():
    global crawler, crawler_thread
    
    try:
        data = request.get_json()
        website_url = data.get('website_url')
        max_depth = int(data.get('max_depth', 3))
        download_dir = data.get('download_dir', 'downloads')
        auto_download = data.get('auto_download', False)
        
        if not website_url:
            return jsonify({'error': 'Website URL is required'}), 400
        
        # Stop any existing crawler
        if crawler and crawler.crawl_status['is_running']:
            crawler.stop_crawling()
            if crawler_thread:
                crawler_thread.join(timeout=5)
        
        # Create new crawler
        crawler = PDFCrawler(max_depth=max_depth)
        
        # Start crawling in a separate thread
        def crawl_worker():
            crawler.crawl_website(website_url, download_dir, auto_download)
        
        crawler_thread = threading.Thread(target=crawl_worker)
        crawler_thread.daemon = True
        crawler_thread.start()
        
        return jsonify({
            'message': 'Crawling started',
            'status': 'running'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop-crawl', methods=['POST'])
def stop_crawl():
    global crawler
    
    if crawler:
        crawler.stop_crawling()
        return jsonify({'message': 'Crawling stopped'})
    
    return jsonify({'message': 'No crawler running'})

@app.route('/api/status')
def get_status():
    global crawler
    
    if not crawler:
        return jsonify({
            'is_running': False,
            'current_depth': 0,
            'urls_processed': 0,
            'pdfs_found': 0,
            'error': None
        })
    
    return jsonify(crawler.crawl_status)

@app.route('/api/results')
def get_results():
    global crawler
    
    if not crawler:
        return jsonify({'pdfs': [], 'total_urls_visited': 0})
    
    return jsonify({
        'pdfs': crawler.pdf_links,
        'total_urls_visited': len(crawler.visited_urls)
    })

@app.route('/api/select-directory', methods=['POST'])
def select_directory():
    """Open native file dialog to select directory."""
    try:
        system = platform.system()
        selected_path = None
        
        if system == 'Darwin':  # macOS
            # Use AppleScript to open folder selection dialog
            script = '''
            tell application "System Events"
                activate
                set theFolder to choose folder with prompt "Select folder for PDF downloads"
                return POSIX path of theFolder
            end tell
            '''
            result = subprocess.run(['osascript', '-e', script], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout:
                selected_path = result.stdout.strip()
        
        elif system == 'Windows':
            # Use PowerShell for Windows
            script = '''
            Add-Type -AssemblyName System.Windows.Forms
            $folderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
            $folderBrowser.Description = "Select folder for PDF downloads"
            $result = $folderBrowser.ShowDialog()
            if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
                Write-Output $folderBrowser.SelectedPath
            }
            '''
            result = subprocess.run(['powershell', '-Command', script], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout:
                selected_path = result.stdout.strip()
        
        else:  # Linux
            # Try using zenity if available
            try:
                result = subprocess.run(['zenity', '--file-selection', '--directory',
                                       '--title=Select folder for PDF downloads'],
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0 and result.stdout:
                    selected_path = result.stdout.strip()
            except FileNotFoundError:
                # Zenity not available, try kdialog
                try:
                    result = subprocess.run(['kdialog', '--getexistingdirectory', '.',
                                           '--title', 'Select folder for PDF downloads'],
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode == 0 and result.stdout:
                        selected_path = result.stdout.strip()
                except FileNotFoundError:
                    pass
        
        if selected_path:
            return jsonify({
                'success': True,
                'path': selected_path,
                'message': f'Selected: {selected_path}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No directory selected or dialog was cancelled'
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Dialog timed out'
        }), 408
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/download-pdf', methods=['POST'])
def download_pdf():
    try:
        data = request.get_json()
        pdf_url = data.get('url')
        download_dir = data.get('download_dir', 'downloads')
        
        if not pdf_url:
            return jsonify({'error': 'PDF URL is required'}), 400
        
        # Ensure download_dir is absolute
        if not os.path.isabs(download_dir):
            download_dir = os.path.abspath(download_dir)
        
        # Create download directory
        os.makedirs(download_dir, exist_ok=True)
        
        # Create a temporary crawler for single download
        temp_crawler = PDFCrawler()
        temp_crawler.session.get(pdf_url)  # Test if URL is accessible
        
        # Download the PDF
        filename = os.path.basename(pdf_url)
        if not filename.endswith('.pdf'):
            filename += '.pdf'
        
        filepath = os.path.join(download_dir, filename)
        
        response = temp_crawler.session.get(pdf_url, stream=True)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return jsonify({
            'message': 'PDF downloaded successfully',
            'filename': filename,
            'filepath': filepath
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/downloads/<path:filename>')
def download_file(filename):
    download_dir = request.args.get('dir', 'downloads')
    return send_from_directory(download_dir, filename, as_attachment=True)

if __name__ == '__main__':
    # Create downloads directory
    os.makedirs('downloads', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=8080)
