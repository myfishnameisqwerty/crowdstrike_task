import os
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import Dict, List
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import DownloadRequest, DownloadResult, BatchDownloadRequest, BatchDownloadResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageDownloader:
    """Threading-based image downloader with retry logic."""

    def __init__(self, max_workers: int = 15) -> None:
        self.max_workers: int = max_workers
        
        # Configure requests session with retry strategy
        self.session: requests.Session = requests.Session()
        
        # Set proper User-Agent to comply with Wikimedia's policy
        self.session.headers.update({
            'User-Agent': 'AnimalImageDownloader/1.0 (https://github.com/your-repo; your-email@example.com) Python/3.13'
        })
        
        retry_strategy = Retry(
            total=3,  # 3 retries
            backoff_factor=1,  # Exponential backoff: 1s, 2s, 4s
            status_forcelist=[403, 429, 500, 502, 503, 504],  # Added 403 for User-Agent violations
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _ensure_directory(self, directory: str) -> bool:
        """Ensure directory exists, thread-safe."""
        try:
            os.makedirs(directory, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {e}")
            return False
    
    def _get_file_extension(self, url: str, content_type: str) -> str:
        """Get file extension from URL or content type."""
        # Try to get extension from URL
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        # Extract extension from URL path
        if '.' in path:
            return '.' + path.split('.')[-1]
        
        # Fallback to content type
        if '/' in content_type:
            subtype = content_type.split('/')[-1].lower()
            return '.' + subtype
        
        raise ValueError(f"Cannot determine file extension for URL: {url}, Content-Type: {content_type}")
    
    def _download_single_image(self, download_request: DownloadRequest, timeout_seconds: int = 30) -> DownloadResult:
        """Download a single image with retry logic."""
        start_time: float = time.time()
        target_path: str = download_request.target_path
        
        # Ensure target directory exists
        target_dir: str = os.path.dirname(target_path)
        if not self._ensure_directory(target_dir):
            return DownloadResult(
                image_url=download_request.image_url,
                target_path=target_path,
                is_successful=False,
                file_size=0,
                download_time=time.time() - start_time,
                error_message="Failed to create target directory"
            )
                
        try:
            # Download with timeout
            response = self.session.get(
                download_request.image_url,
                timeout=timeout_seconds,
                stream=True
            )
                    response.raise_for_status()
                    
            # Get file extension
            content_type: str = response.headers.get('content-type', '')
            file_extension: str = self._get_file_extension(download_request.image_url, content_type)
            
            # Update target path with correct extension
            base_path: str = os.path.splitext(target_path)[0]
            final_target_path: str = base_path + file_extension
            
            # Download file
            with open(final_target_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Get file size
            file_size: int = os.path.getsize(final_target_path)
            download_time: float = time.time() - start_time
            
            logger.info(f"Successfully downloaded {download_request.name} to {final_target_path} ({file_size} bytes)")
                    
                    return DownloadResult(
                image_url=download_request.image_url,
                target_path=final_target_path,
                is_successful=True,
                        file_size=file_size,
                download_time=download_time
                    )
                    
        except requests.exceptions.Timeout:
            error_msg: str = f"Timeout downloading {download_request.name} from {download_request.image_url}"
            logger.error(error_msg)
                    return DownloadResult(
                image_url=download_request.image_url,
                        target_path=target_path,
                is_successful=False,
                file_size=0,
                        download_time=time.time() - start_time,
                error_message=error_msg
                    )
                    
        except requests.exceptions.RequestException as e:
            error_msg: str = f"Request failed for {download_request.name}: {str(e)}"
            logger.error(error_msg)
                    return DownloadResult(
                image_url=download_request.image_url,
                        target_path=target_path,
                is_successful=False,
                file_size=0,
                        download_time=time.time() - start_time,
                error_message=error_msg
                    )
                    
        except ValueError as e:
            error_msg: str = f"Invalid file format for {download_request.name}: {str(e)}"
            logger.error(error_msg)
                    return DownloadResult(
                image_url=download_request.image_url,
                        target_path=target_path,
                is_successful=False,
                file_size=0,
                        download_time=time.time() - start_time,
                error_message=error_msg
            )
            
        except Exception as e:
            error_msg: str = f"Unexpected error downloading {download_request.name}: {str(e)}"
            logger.error(error_msg)
        return DownloadResult(
                image_url=download_request.image_url,
            target_path=target_path,
                is_successful=False,
                file_size=0,
            download_time=time.time() - start_time,
                error_message=error_msg
        )

    def download_batch(self, batch_request: BatchDownloadRequest) -> BatchDownloadResult:
        """Download multiple images using ThreadPoolExecutor."""
        start_time: float = time.time()
        total_count: int = len(batch_request.downloads)
        
        if total_count == 0:
            return BatchDownloadResult(
                results=[],
                total_count=0,
                success_count=0,
                failure_count=0,
                total_time=0.0,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ")
            )
        
        logger.info(f"Starting batch download of {total_count} images with {self.max_workers} workers")
        
        results: List[DownloadResult] = []
        success_count: int = 0
        failure_count: int = 0
        
        # Use ThreadPoolExecutor for parallel downloads
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all download tasks
            future_to_request: Dict[Future[DownloadResult], DownloadRequest] = {
                executor.submit(self._download_single_image, request, batch_request.timeout_seconds): request
                for request in batch_request.downloads
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_request):
                try:
                    result: DownloadResult = future.result()
                    results.append(result)
                    
                    if result.is_successful:
                        success_count += 1
                    else:
                        failure_count += 1
                        
                except Exception as e:
                    request: DownloadRequest = future_to_request[future]
                    error_msg: str = f"Thread execution failed for {request.name}: {str(e)}"
                    logger.error(error_msg)
                    
                    results.append(DownloadResult(
                        image_url=request.image_url,
                        target_path=request.target_path,
                        is_successful=False,
                        file_size=0,
                        download_time=0.0,
                        error_message=error_msg
                    ))
                    failure_count += 1
        
        total_time: float = time.time() - start_time
        
        logger.info(f"Batch download completed: {success_count} successful, {failure_count} failed in {total_time:.2f}s")
        
        return BatchDownloadResult(
            results=results,
            total_count=total_count,
            success_count=success_count,
            failure_count=failure_count,
            total_time=total_time,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ")
        ) 