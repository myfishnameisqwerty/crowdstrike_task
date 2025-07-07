# Animal Collateral Adjectives Microservices Project

A modular Python microservices system that scrapes Wikipedia for animal collateral adjectives, downloads associated images, and generates beautiful HTML galleries organized by collateral adjective categories.

## 🏗️ Architecture

The system consists of three microservices:

1. **Data Scraper Service** (`data-scraper-service`) - Scrapes Wikipedia for animal names and their collateral adjectives
2. **Image Downloader Service** (`image-downloader`) - Downloads animal images with threading support
3. **Orchestrator Service** (`orchestrator`) - Coordinates workflows and generates HTML galleries

## 🚀 Quick Start

### 1. Start All Services
```bash
docker-compose up --build
```

This starts all three services:
- Data Scraper: http://localhost:9001
- Image Downloader: http://localhost:9002  
- Orchestrator: http://localhost:9003

### 2. Trigger a Workflow
```bash
curl -X POST http://localhost:9003/trigger \
  -H "Content-Type: application/json" \
  -d '{"trigger": "wikipedia-animals"}'
```

### 3. View Results
- **HTML Gallery**: http://localhost:9003/html/wikipedia_animals_gallery.html
- **Downloaded Images**: `/tmp/wikipedia_animals/` (inside containers)



### View Animals Grouped by Collateral Adjectives
```bash
docker-compose logs orchestrator | grep -A 50 "Animals grouped by collateral adjectives"
```

This shows the complete mapping of collateral adjectives to their associated animals.

### View Download Progress
```bash
docker-compose logs orchestrator | grep -E "(Downloaded|Skipping|Will download)"
```

### View Service Health
```bash
# Check all services
curl http://localhost:9001/health
curl http://localhost:9002/health  
curl http://localhost:9003/health
```

## 🖼️ Image Management

### Image Storage
- **Location**: `/tmp/wikipedia_animals/` (inside containers)
- **Format**: Supports JPG, PNG, JPEG, GIF
- **Naming**: `animal_name.png` (lowercase, underscores)
- **Caching**: Existing images are skipped, only new images are downloaded

### Image Download Features
- **Threading**: 15 concurrent downloads
- **Retry Logic**: 3 attempts with exponential backoff
- **Timeout**: Per-download timeout (configurable)

## 🎨 HTML Gallery

The generated HTML gallery shows:
1. **Collateral adjective as title** (e.g., "chick", "cria", "cub")
2. **Animal images row** - All images for that adjective displayed horizontally
3. **Animal names row** - All animal names as tags below the images

### Access the Gallery
```bash
# View in browser
open http://localhost:9003/html/wikipedia_animals_gallery.html

# Or curl to see HTML structure
curl -s http://localhost:9003/html/wikipedia_animals_gallery.html | head -50
```

## 🔧 Service Details

### Data Scraper Service
- **Port**: 9001
- **Endpoint**: `GET /scrape?source=wikipedia&category=animals`

### Image Downloader Service  
- **Port**: 9002
- **Endpoints**: 
  - `POST /download` - Batch downloads
  - `POST /download-single` - Single download
  - `GET /health` - Health check

### Orchestrator Service
- **Port**: 9003
- **Endpoints**:
  - `POST /trigger` - Start workflow
  - `GET /status` - Check status
  - `GET /html/{filename}` - Access HTML galleries

## 🧪 Testing

### Run All Tests
```bash
# Data Scraper tests
docker-compose run --rm data-scraper-service pytest /app/tests/ -v

# Image Downloader tests  
docker-compose run --rm image-downloader pytest /app/tests/ -v

# Orchestrator tests (not implemented)
```


## 🎯 Example Workflow

1. **Trigger**: `POST /trigger` with `{"trigger": "wikipedia-animals"}`
2. **Scrape**: Data scraper extracts 258 animals with collateral adjectives
3. **Group**: Animals organized into 90 unique collateral adjective categories
4. **Download**: Images downloaded to `/tmp/wikipedia_animals/`
5. **Generate**: HTML gallery created with collateral adjectives as sections
6. **Access**: View at `http://localhost:9003/html/wikipedia_animals_gallery.html`


### Log Analysis
```bash
docker-compose logs orchestrator
docker-compose logs data-scraper-service
docker-compose logs image-downloader
``` 