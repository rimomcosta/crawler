import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import re
from typing import Set, List, Dict, Optional
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


class PDFCrawler:
    def __init__(self, max_depth: int = 3, max_workers: int = 5):
        self.max_depth = max_depth
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.visited_urls: Set[str] = set()
        self.pdf_links: List[Dict] = []
        self.crawl_status = {
            'is_running': False,
            'current_depth': 0,
            'urls_processed': 0,
            'pdfs_found': 0,
            'error': None
        }
        
    def is_valid_url(self, url: str, base_domain: str) -> bool:
        """Check if URL is valid and belongs to the same domain."""
        try:
            parsed = urlparse(url)
            
            # Skip non-HTTP/HTTPS URLs
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Get domain without www
            url_domain = parsed.netloc.lower().replace('www.', '')
            base = base_domain.lower().replace('www.', '')
            
            # Allow same domain or subdomains
            if url_domain != base:
                # Check if it's a subdomain of the base domain
                if url_domain.endswith('.' + base):
                    return True
                return False
                
            # Skip common non-content URLs
            skip_patterns = [
                r'\.(jpg|jpeg|png|gif|svg|ico|css|js|xml|json|txt|zip|rar|exe|dmg)$',
                r'#.*$',  # Skip anchors
                r'mailto:',  # Skip email links
                r'tel:',  # Skip phone links
            ]
            
            for pattern in skip_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return False
                    
            return True
        except Exception as e:
            print(f"Error validating URL {url}: {e}")
            return False
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL by adding protocol if needed."""
        url = url.strip()
        
        # If no protocol specified, add https://
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
                
        return url
    
    def is_pdf_url(self, url: str) -> bool:
        """Check if URL points to a PDF file."""
        # Check file extension
        if url.lower().endswith('.pdf'):
            return True
        # Check if URL contains PDF-related patterns
        if '/pdf/' in url.lower() or 'pdf' in url.lower():
            # Verify it's likely a PDF by checking for file-like patterns
            if any(pattern in url for pattern in ['/file/', '/download/', '/api/v1/file/']):
                return True
        return False
    
    def extract_pdf_info(self, url: str, source_url: str) -> Dict:
        """Extract information about a PDF link."""
        try:
            # Try to get headers to check if it's actually a PDF
            response = self.session.head(url, timeout=10, allow_redirects=True)
            content_type = response.headers.get('content-type', '').lower()
            
            is_valid_pdf = (
                url.lower().endswith('.pdf') or 
                'application/pdf' in content_type or
                'pdf' in content_type
            )
            
            if is_valid_pdf:
                filename = os.path.basename(urlparse(url).path)
                if not filename.endswith('.pdf'):
                    filename += '.pdf'
                    
                return {
                    'url': url,
                    'filename': filename,
                    'source_url': source_url,
                    'content_type': content_type,
                    'size': response.headers.get('content-length'),
                    'status': 'found'
                }
        except Exception as e:
            # If HEAD request fails, still include it but mark as unverified
            filename = os.path.basename(urlparse(url).path)
            if not filename.endswith('.pdf'):
                filename += '.pdf'
                
            return {
                'url': url,
                'filename': filename,
                'source_url': source_url,
                'content_type': 'unknown',
                'size': None,
                'status': 'unverified'
            }
        
        return None
    
    def get_page_links(self, url: str) -> List[str]:
        """Extract all links from a webpage."""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            links = []
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(url, href)
                # Only add links from the same domain
                if absolute_url.startswith(('http://', 'https://')):
                    links.append(absolute_url)
            
            print(f"  Found {len(links)} links on {url}")
            return links
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return []
    
    def crawl_page(self, url: str, depth: int, base_domain: str) -> List[str]:
        """Crawl a single page and return new URLs to visit."""
        if depth > self.max_depth or url in self.visited_urls:
            return []
            
        self.visited_urls.add(url)
        self.crawl_status['urls_processed'] += 1
        self.crawl_status['current_depth'] = depth
        
        print(f"Crawling: {url} (depth: {depth})")
        
        # Find PDFs on current page
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for PDF links in multiple ways
            # 1. Direct PDF links in anchor tags
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(url, href)
                
                if self.is_pdf_url(absolute_url):
                    pdf_info = self.extract_pdf_info(absolute_url, url)
                    if pdf_info and not any(p['url'] == pdf_info['url'] for p in self.pdf_links):
                        # Store the source page URL, not the PDF file URL
                        pdf_info['source_url'] = url
                        self.pdf_links.append(pdf_info)
                        self.crawl_status['pdfs_found'] += 1
                        print(f"  Found PDF: {pdf_info['filename']} from {url}")
                        
                        # Download immediately if auto-download is enabled
                        if hasattr(self, 'auto_download_enabled') and self.auto_download_enabled and hasattr(self, 'download_dir'):
                            self.download_single_pdf(pdf_info)
            
                        # 2. Look for embed and iframe tags that might contain PDFs
            for embed in soup.find_all(['embed', 'iframe', 'object']):
                src = embed.get('src') or embed.get('data')
                if src:
                    absolute_url = urljoin(url, src)
                    if self.is_pdf_url(absolute_url):
                        pdf_info = self.extract_pdf_info(absolute_url, url)
                        if pdf_info and not any(p['url'] == pdf_info['url'] for p in self.pdf_links):
                            # Store the source page URL, not the PDF file URL
                            pdf_info['source_url'] = url
                            self.pdf_links.append(pdf_info)
                            self.crawl_status['pdfs_found'] += 1
                            print(f"  Found embedded PDF: {pdf_info['filename']} from {url}")
                            
                            # Download immediately if auto-download is enabled
                            if hasattr(self, 'auto_download_enabled') and self.auto_download_enabled and hasattr(self, 'download_dir'):
                                self.download_single_pdf(pdf_info)
            
            # If we haven't reached max depth, get more links to crawl
            if depth < self.max_depth:
                return self.get_page_links(url)
                
        except Exception as e:
            print(f"Error processing {url}: {e}")
            
        return []
    
    def crawl_website(self, start_url: str, download_dir: str = None, auto_download: bool = False) -> Dict:
        """Main crawling function."""
        self.crawl_status = {
            'is_running': True,
            'current_depth': 0,
            'urls_processed': 0,
            'pdfs_found': 0,
            'error': None
        }
        
        self.visited_urls.clear()
        self.pdf_links.clear()
        
        # Store auto-download settings for immediate downloads
        self.auto_download_enabled = auto_download
        self.download_dir = download_dir
        
        print(f"\n=== Starting crawl ===")
        print(f"URL: {start_url}")
        print(f"Max depth: {self.max_depth}")
        print(f"Auto-download: {auto_download}")
        print(f"Download directory: {download_dir}")
        
        try:
            # Normalize the start URL
            start_url = self.normalize_url(start_url)
            base_domain = urlparse(start_url).netloc
            
            # Create download directory if auto-download is enabled
            if auto_download and download_dir:
                os.makedirs(download_dir, exist_ok=True)
            
            # Start crawling
            urls_to_visit = [(start_url, 0)]
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                while urls_to_visit and self.crawl_status['is_running']:
                    current_batch = urls_to_visit[:self.max_workers]
                    urls_to_visit = urls_to_visit[self.max_workers:]
                    
                    print(f"Processing batch of {len(current_batch)} URLs...")
                    
                    # Submit current batch
                    future_to_url = {
                        executor.submit(self.crawl_page, url, depth, base_domain): (url, depth)
                        for url, depth in current_batch
                    }
                    
                    # Process completed tasks
                    for future in as_completed(future_to_url):
                        if not self.crawl_status['is_running']:
                            break
                            
                        try:
                            new_urls = future.result()
                            url, depth = future_to_url[future]
                            
                            # Add new URLs to visit
                            for new_url in new_urls:
                                if (self.is_valid_url(new_url, base_domain) and 
                                    new_url not in self.visited_urls and
                                    depth + 1 <= self.max_depth):
                                    urls_to_visit.append((new_url, depth + 1))
                                    print(f"  Added to queue: {new_url} (depth {depth + 1})")
                                    
                        except Exception as e:
                            print(f"Error in thread: {e}")
                    
                    # Update current depth
                    if urls_to_visit:
                        self.crawl_status['current_depth'] = max(depth for _, depth in urls_to_visit)
            
            # Note: PDFs are now downloaded immediately when found
            # No need to download all at the end
            
            print(f"\n=== Crawl completed ===")
            print(f"URLs visited: {len(self.visited_urls)}")
            print(f"PDFs found: {len(self.pdf_links)}")
            print(f"Max depth reached: {self.crawl_status['current_depth']}")
                
        except Exception as e:
            self.crawl_status['error'] = str(e)
            print(f"Crawling error: {e}")
        finally:
            self.crawl_status['is_running'] = False
            
        return {
            'status': self.crawl_status,
            'pdfs': self.pdf_links,
            'total_urls_visited': len(self.visited_urls)
        }
    
    def download_pdfs(self, download_dir: str) -> List[Dict]:
        """Download all found PDFs to the specified directory."""
        downloaded = []
        
        # Ensure download_dir is absolute
        if not os.path.isabs(download_dir):
            # If relative, make it relative to the current working directory
            download_dir = os.path.abspath(download_dir)
        
        print(f"Downloading PDFs to: {download_dir}")
        
        # Create directory if it doesn't exist
        os.makedirs(download_dir, exist_ok=True)
        
        for pdf_info in self.pdf_links:
            try:
                url = pdf_info['url']
                filename = pdf_info['filename']
                filepath = os.path.join(download_dir, filename)
                
                print(f"  Downloading {filename} to {filepath}")
                
                # Skip if file already exists
                if os.path.exists(filepath):
                    pdf_info['status'] = 'already_exists'
                    downloaded.append(pdf_info)
                    print(f"    Skipped - file already exists")
                    continue
                
                # Download the PDF
                response = self.session.get(url, timeout=30, stream=True)
                response.raise_for_status()
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                pdf_info['status'] = 'downloaded'
                pdf_info['local_path'] = filepath
                downloaded.append(pdf_info)
                print(f"    Downloaded successfully")
                
            except Exception as e:
                pdf_info['status'] = 'download_failed'
                pdf_info['error'] = str(e)
                downloaded.append(pdf_info)
                print(f"    Download failed: {e}")
                
        return downloaded
    
    def download_single_pdf(self, pdf_info: Dict) -> bool:
        """Download a single PDF immediately when found."""
        try:
            if not self.download_dir:
                return False
                
            # Ensure download_dir is absolute
            if not os.path.isabs(self.download_dir):
                download_dir = os.path.abspath(self.download_dir)
            else:
                download_dir = self.download_dir
            
            # Create directory if it doesn't exist
            os.makedirs(download_dir, exist_ok=True)
            
            url = pdf_info['url']
            filename = pdf_info['filename']
            filepath = os.path.join(download_dir, filename)
            
            print(f"    Downloading {filename} immediately to {filepath}")
            
            # Skip if file already exists
            if os.path.exists(filepath):
                pdf_info['status'] = 'already_exists'
                print(f"      Skipped - file already exists")
                return True
            
            # Download the PDF
            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            pdf_info['status'] = 'downloaded'
            pdf_info['local_path'] = filepath
            print(f"      Downloaded successfully")
            return True
            
        except Exception as e:
            pdf_info['status'] = 'download_failed'
            pdf_info['error'] = str(e)
            print(f"      Download failed: {e}")
            return False
    
    def stop_crawling(self):
        """Stop the crawling process."""
        self.crawl_status['is_running'] = False
