# Backend API & Data Response Documentation

## Project Overview
**Comprehensive UI Testing & Image Comparison Agent** - A FastAPI backend service providing enterprise-grade UI quality assurance with AI-powered analysis, pixel-level comparison, and expert analysis capabilities.

**Version:** 3.0.0
**Framework:** FastAPI with Azure OpenAI integration
**Core Features:** 9 integrated testing tools, AI expert analysis, pixel comparison, and comprehensive UI testing

---

## API Configuration

### Environment Variables
```bash
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
```

### Server Configuration
- **Base URL:** `http://127.0.0.1:8000`
- **CORS:** Enabled for all origins
- **Static Files:** `/amadeus-images/` serves images from `Amadeus cockpit (2)` folder
- **OpenAPI:** Available at `/docs`

---

## Core API Endpoints

### 1. System Status & Health Check

#### `GET /orchestrator-status`
**Purpose:** Get comprehensive system status and available features
**Response Data Structure:**
```json
{
  "orchestrator_active": true,
  "image_comparison_tools": 5,
  "ui_testing_tools": 4,
  "total_tools": 9,
  "openai_configured": true,
  "features": {
    "pixel_comparison": true,
    "ssim_analysis": true,
    "histogram_matching": true,
    "difference_detection": true,
    "unwanted_element_detection": true,
    "galen_layout_validation": true,
    "parallel_execution": true,
    "batch_testing": true,
    "multi_viewport_testing": true,
    "intelligent_tool_assignment": true,
    "clean_ui_comparison": true,
    "openai_reanalysis": true
  },
  "recommended_endpoints": {
    "comprehensive_analysis": "/orchestrate-ui-dev-analysis-stream",
    "change_verification": "/orchestrate-change-verification-analysis",
    "expert_analysis": "/available-experts"
  }
}
```

### 2. Image Upload & Management

#### `POST /upload-image`
**Purpose:** Upload UI screenshot to backend (Expected endpoint)
**Request Data:** 
```javascript
FormData: {
  file: File // Image file (PNG, JPG, JPEG)
}
```
**Response Data Structure:**
```json
{
  "status": "success",
  "filename": "uploaded_screenshot.png",
  "message": "Image uploaded successfully",
  "file_path": "/amadeus-images/uploaded_screenshot.png"
}
```

#### `GET /amadeus-images/<filename>`
**Purpose:** Serve static images from Amadeus cockpit folder
**Response:** Binary image data
**Content-Type:** `image/png`, `image/jpeg`, etc.

---

## Core Analysis Endpoints

### 3. UI vs Development Analysis

#### `POST /orchestrate-ui-dev-analysis-stream`
**Purpose:** Comprehensive UI design vs development implementation analysis
**Request Data:**
```javascript
FormData: {
  ui_design: File,           // UI design/mockup image
  dev_implementation: File,  // Developer implementation screenshot
  stream: boolean           // Optional streaming mode
}
```

**Response Data Structure (Complete):**
```json
{
  "status": "completed",
  "image_comparison": {
    "match_score": 0.857,
    "differences_found": 23,
    "pixel_differences_analyzed": true,
    "difference_image_provided_to_agents": true,
    "technical_analysis_provided": true
  },
  "technical_analysis": {
    "pixel_analysis": {
      "match_score": 0.857,
      "different_pixels": 143250,
      "total_pixels": 1000000,
      "difference_percentage": 14.33
    },
    "differences_data": {
      "differences_count": 23,
      "coordinates": [
        {"x": 120, "y": 45, "width": 200, "height": 30, "area": 6000},
        {"x": 350, "y": 200, "width": 150, "height": 25, "area": 3750}
      ],
      "similarity_metrics": {
        "ssim_score": 0.743,
        "histogram_similarity": 0.892
      }
    }
  },
  "dimension_analysis": {
    "original_ui_dimensions": {"width": 1920, "height": 1080},
    "original_dev_dimensions": {"width": 1366, "height": 768},
    "ui_cropped_dimensions": {"width": 1366, "height": 768},
    "processed_dimensions": {"width": 1366, "height": 768},
    "dimension_difference": {
      "width_diff": 554,
      "height_diff": 312,
      "aspect_ratio_ui": 1.778,
      "aspect_ratio_dev": 1.779,
      "ui_auto_cropped": true
    }
  },
  "Agent Results": {
    "expert_analyses": {
      "Alex (Component Pixel Analysis Expert - Young Adults)": {
        "overall_rating": 7.2,
        "match_percentage": 85.7,
        "differences": [
          {
            "category": "Layout",
            "description": "Primary navigation button positioned 15px lower than design specification",
            "priority": "High",
            "location": "x:200-350, y:25-65",
            "color_details": "Current: #E5E7EB, Expected: #3B82F6",
            "measurements": "Current: 150x40px, Expected: 150x40px",
            "detailed_explanation": "Button maintains correct size but vertical position deviates from design mockup causing visual hierarchy disruption",
            "technical_analysis": "CSS top property offset by 15px, likely due to margin calculation error"
          }
        ],
        "detailed_summary": "Component-level analysis reveals 12 pixel-perfect differences requiring attention",
        "root_cause_analysis": "Implementation differences primarily stem from CSS margin/padding inconsistencies",
        "quality_assessment": "Good",
        "technical_insights": [
          "Button positioning requires 15px upward adjustment",
          "Color values need correction to match brand guidelines",
          "Font weight should be increased for better visibility"
        ]
      },
      "Sarah (Component Issue Priority Expert - Middle Age)": {
        "overall_rating": 6.8,
        "match_percentage": 82.4,
        "differences": [
          {
            "category": "Business Priority",
            "description": "Primary CTA button color deviation impacts conversion potential",
            "priority": "Critical",
            "location": "x:320-520, y:450-498",
            "detailed_explanation": "Button color off-brand reduces user confidence and click-through rates",
            "technical_analysis": "Brand compliance violation requiring immediate CSS correction"
          }
        ],
        "detailed_summary": "Business-critical issues identified requiring immediate development attention",
        "root_cause_analysis": "CSS implementation lacks brand color variable consistency",
        "quality_assessment": "Fair",
        "technical_insights": [
          "Primary CTA requires immediate color correction",
          "Secondary navigation elements need alignment fixes",
          "Typography consistency improvements needed"
        ]
      }
    },
    "combined_rating": 7.0,
    "all_differences": [
      "Primary navigation button positioned 15px lower",
      "CTA button color deviation from brand guidelines",
      "Secondary text font weight inconsistency"
    ],
    "all_technical_insights": [
      "CSS margin/padding standardization needed",
      "Brand color variables implementation required",
      "Typography system consistency improvements"
    ],
    "total_experts": 8,
    "spatial_analysis_enabled": true,
    "detailed_explanations_focus": true
  }
}
```

**Streaming Mode Response:**
```javascript
// Server-Sent Events (SSE) stream
data: {"status": "starting", "progress": 0, "message": "Initializing analysis..."}
data: {"status": "processing", "progress": 25, "message": "Loading images..."}
data: {"status": "processing", "progress": 50, "message": "Analyzing differences..."}
data: {"status": "processing", "progress": 75, "message": "Running expert analysis..."}
data: {"status": "completed", "progress": 100, "match_score": 0.857}
```

### 4. Change Verification Analysis

#### `POST /orchestrate-change-verification-analysis`
**Purpose:** Verify implementation of specific changes between before/after images
**Request Data:**
```javascript
FormData: {
  before_image: File,              // Image before changes
  after_image: File,               // Image after changes  
  change_description: string       // Description of expected changes
}
```

**Response Data Structure:**
```json
{
  "status": "completed",
  "change_requirements": "Updated button color to brand primary blue and increased font size",
  "detailed_analysis": {
    "implementation_breakdown": [
      {
        "requirement": "Button color change to brand blue",
        "implementation_status": "Clearly Implemented",
        "implementation_percentage": 95,
        "details": "Button color successfully changed from gray to brand blue (#3B82F6)",
        "location": "Primary CTA button area",
        "priority": "High"
      },
      {
        "requirement": "Font size increase",
        "implementation_status": "Partially Clear", 
        "implementation_percentage": 70,
        "details": "Font appears larger but exact size difficult to verify",
        "location": "Button text",
        "priority": "Medium"
      }
    ],
    "overall_implementation_percentage": 82,
    "critical_issues": [],
    "recommendations": [
      "Verify exact font size measurements",
      "Consider adding visual emphasis to completed changes"
    ],
    "verification_summary": {
      "overall_status": "Clearly Implemented",
      "summary": "Most requested changes are visibly implemented with good clarity"
    }
  },
  "images": {
    "before_image": "base64_encoded_image_data",
    "after_image": "base64_encoded_image_data", 
    "difference_image": "base64_encoded_diff_data"
  },
  "summary": {
    "overall_implementation_percentage": 82,
    "verification_status": "Clearly Implemented",
    "ai_analysis_available": true
  }
}
```

---

## Image Processing Endpoints

### 5. Image Resizing & Processing

#### `POST /resize-images`
**Purpose:** Resize two images to same dimensions for comparison
**Request Data:**
```javascript
FormData: {
  image1: File,
  image2: File
}
```
**Response Data Structure:**
```json
{
  "original_dimensions": {
    "image1": {"width": 1920, "height": 1080},
    "image2": {"width": 1366, "height": 768}
  },
  "resized_dimensions": {
    "width": 1920,
    "height": 1080
  },
  "resized_images": {
    "image1": "base64_encoded_resized_image1",
    "image2": "base64_encoded_resized_image2"
  }
}
```

#### `POST /crop-and-resize`
**Purpose:** Crop specific regions and resize images
**Request Parameters:**
```javascript
FormData: {
  image1: File,
  image2: File,
  x1: int,    // Crop coordinates for image1
  y1: int,
  w1: int,
  h1: int,
  x2: int,    // Crop coordinates for image2  
  y2: int,
  w2: int,
  h2: int
}
```

#### `POST /get-difference-image`
**Purpose:** Generate visual difference image highlighting changes
**Response:** Binary PNG image showing highlighted differences

---

## Expert Analysis System

### 6. Available Experts

#### `GET /available-experts`
**Purpose:** Get list of AI expert agents and their specializations
**Response Data Structure:**
```json
{
  "success": true,
  "total_experts": 8,
  "experts": {
    "Young_Adults_UI_Expert": {
      "name": "Alex (Component Pixel Analysis Expert - Young Adults)",
      "description": "28-year-old Component-Level Pixel Analysis Specialist with methodical, detail-oriented personality..."
    },
    "Middle_Age_UI_Expert": {
      "name": "Sarah (Component Issue Priority Expert - Middle Age)", 
      "description": "42-year-old Component Issue Priority Specialist with strategic, business-focused personality..."
    }
  },
  "high_detection_experts": [
    "Young_Adults_UI_Expert",
    "Middle_Age_UI_Expert",
    "Senior_UI_Expert",
    "Layout_Alignment_Expert",
    "Color_Typography_Expert",
    "Spacing_Check_Expert", 
    "Interactive_States_Expert",
    "Responsive_Mobile_Expert"
  ],
  "expert_specializations": {
    "Young_Adults_UI_Expert": "Component identification and pixel-level difference analysis",
    "Middle_Age_UI_Expert": "Component issue prioritization and fix urgency ranking",
    "Senior_UI_Expert": "Comprehensive pixel-level difference documentation",
    "Layout_Alignment_Expert": "Layout structure and alignment pixel analysis",
    "Color_Typography_Expert": "Color accuracy and typography rendering pixel analysis",
    "Spacing_Check_Expert": "Margin, padding, and spacing precision pixel analysis",
    "Interactive_States_Expert": "Interactive states and accessibility compliance pixel analysis",
    "Responsive_Mobile_Expert": "Responsive design and mobile interface pixel analysis"
  }
}
```

---

## Data Models & Structures

### Core Analysis Models

#### `DifferenceItem`
```json
{
  "category": "Layout | Colors | Content | Typography | Spacing",
  "description": "Detailed description with exact measurements",
  "priority": "Critical | High | Medium | Low",
  "location": "x:200-350, y:25-65",
  "color_details": "Current: #E5E7EB, Expected: #3B82F6",
  "measurements": "Current: 150x40px, Expected: 150x40px",
  "typography_specs": "Font: Arial, Size: 16px, Weight: 500",
  "detailed_explanation": "In-depth technical explanation",
  "technical_analysis": "CSS/implementation analysis"
}
```

#### `AIImageAnalysis`
```json
{
  "overall_rating": 7.5,
  "match_percentage": 85.2,
  "differences": [...], // Array of DifferenceItem
  "detailed_summary": "Comprehensive analysis summary",
  "root_cause_analysis": "Technical root cause explanation",
  "quality_assessment": "Excellent | Good | Fair | Poor",
  "technical_insights": ["Insight 1", "Insight 2", ...]
}
```

#### `ExpertAnalysis`
```json
{
  "expert_name": "Alex (Component Pixel Analysis Expert)",
  "analysis": {...}, // AIImageAnalysis object
  "specialized_insights": ["Expert-specific insights"],
  "technical_findings": ["Technical findings"]
}
```

### Technical Metrics Models

#### `LayoutAnalysis`
```json
{
  "layout_type": "Grid | Flexbox | Float | Absolute",
  "element_positioning": ["Positioning issues found"],
  "spacing_consistency": 8.5,
  "alignment_issues": ["Alignment problems"],
  "responsive_behavior": "Responsive design assessment"
}
```

#### `UIComponentAnalysis`
```json
{
  "component_type": "Button | Form | Navigation | Card | Modal",
  "location": "x:100-200, y:50-80",
  "styling_issues": ["Styling problems"],
  "functionality_assessment": "Functionality evaluation", 
  "accessibility_score": 7.8
}
```

### Pixel Analysis Data Structure
```json
{
  "total_pixels": 1000000,
  "exact_matches": 856743,
  "exact_match_percentage": 85.67,
  "tolerance_matches": {
    "1_pixel_tolerance": 92.3,
    "5_pixel_tolerance": 96.8,
    "10_pixel_tolerance": 98.2
  },
  "average_pixel_difference": 2.34,
  "psnr": 28.45,
  "normalized_cross_correlation": 0.923,
  "channel_differences": {
    "blue_avg_diff": 1.2,
    "green_avg_diff": 2.1,
    "red_avg_diff": 1.8
  }
}
```

---

## Error Handling & Status Codes

### Success Responses
- **200 OK:** Successful analysis/operation
- **201 Created:** Image uploaded successfully

### Error Responses
- **400 Bad Request:** Invalid image format or parameters
- **404 Not Found:** Image not found
- **500 Internal Server Error:** Analysis failed or system error
- **504 Gateway Timeout:** AI analysis timeout

### Error Response Structure
```json
{
  "detail": "Error description",
  "error_type": "analysis_error | timeout | configuration_error",
  "error_details": "Detailed error information",
  "recommendations": ["Suggestion 1", "Suggestion 2"]
}
```

---

## Performance & Optimization

### Timeouts & Limits
- **AI Analysis Timeout:** 90 seconds per expert
- **Total Analysis Timeout:** 300 seconds (5 minutes)
- **Max File Size:** 50MB per image
- **Supported Formats:** PNG, JPG, JPEG

### Optimization Features
- **Auto-cropping:** UI images automatically cropped to match dev dimensions
- **Image resizing:** Automatic resizing for consistent comparison
- **Lightweight fallbacks:** Simple analysis when AI unavailable
- **Progress streaming:** Real-time progress updates for long operations

---

## Integration Examples

### JavaScript Frontend Integration
```javascript
// Upload and analyze images
const formData = new FormData();
formData.append('ui_design', uiImageFile);
formData.append('dev_implementation', devImageFile);

const response = await fetch('http://127.0.0.1:8000/orchestrate-ui-dev-analysis-stream', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log('Match Score:', result.image_comparison.match_score);
console.log('Expert Analyses:', result['Agent Results'].expert_analyses);
```

### Python Client Integration
```python
import requests

files = {
    'ui_design': open('ui_design.png', 'rb'),
    'dev_implementation': open('dev_screenshot.png', 'rb')
}

response = requests.post(
    'http://127.0.0.1:8000/orchestrate-ui-dev-analysis-stream',
    files=files
)

result = response.json()
match_score = result['image_comparison']['match_score']
expert_analyses = result['Agent Results']['expert_analyses']
```

---

## Expert Agent Details

### Alex - Component Pixel Analysis Expert
- **Focus:** Pixel-level component analysis with forensic precision
- **Output:** Exact measurements, color values, coordinates
- **Specializes:** Modern UI components, precise technical documentation

### Sarah - Component Issue Priority Expert  
- **Focus:** Business impact and priority ranking
- **Output:** ROI analysis, implementation timelines, resource allocation
- **Specializes:** Strategic planning, cost-benefit analysis

### Robert - Detailed Pixel Difference Expert
- **Focus:** Exhaustive pixel-level documentation
- **Output:** Complete technical specifications, browser compatibility
- **Specializes:** Quality assurance, comprehensive testing

### Maya - Layout Alignment Expert
- **Focus:** Spatial relationships and grid systems
- **Output:** Alignment analysis, spacing measurements
- **Specializes:** Grid systems, mathematical precision

### Jordan - Color & Typography Expert
- **Focus:** Visual design accuracy
- **Output:** Color analysis, contrast ratios, typography specifications  
- **Specializes:** Brand consistency, accessibility compliance

### Taylor - Spacing & Padding Expert
- **Focus:** Spacing consistency and design systems
- **Output:** Margin/padding analysis, touch target compliance
- **Specializes:** Design systems, mathematical spacing scales

### Casey - Interactive States Expert
- **Focus:** Accessibility and interaction design
- **Output:** State analysis, WCAG compliance, usability assessment
- **Specializes:** Inclusive design, assistive technology compatibility

### Morgan - Responsive & Mobile Expert
- **Focus:** Multi-device compatibility
- **Output:** Responsive analysis, mobile optimization
- **Specializes:** Mobile-first design, cross-device consistency

---

## Troubleshooting Guide

### Common Issues

1. **AI Analysis Timeout**
   - **Cause:** Large images or complex analysis
   - **Solution:** Reduce image size, try streaming mode
   - **Prevention:** Optimize images before upload

2. **Low Match Scores**
   - **Cause:** Significant differences or misaligned images  
   - **Solution:** Check image alignment, review differences
   - **Prevention:** Ensure consistent screenshot methodology

3. **Missing Expert Analysis**
   - **Cause:** AI service unavailable or timeout
   - **Solution:** Check Azure OpenAI configuration
   - **Prevention:** Monitor AI service health

4. **CORS Errors**
   - **Cause:** Frontend origin not allowed
   - **Solution:** Verify CORS settings in backend
   - **Prevention:** Whitelist frontend domains

### Debug Commands
```bash
# Test backend health
curl http://127.0.0.1:8000/orchestrator-status

# Test image serving
curl http://127.0.0.1:8000/amadeus-images/test_image.png

# Check AI configuration
curl -X GET http://127.0.0.1:8000/available-experts
```

---

## Development & Deployment

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export AZURE_OPENAI_API_KEY=your_key
export AZURE_OPENAI_ENDPOINT=your_endpoint

# Run server
python agentd.py
# or
uvicorn agentd:app --host 0.0.0.0 --port 8000 --reload
```

### Docker Deployment
```dockerfile
FROM python:3.11
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "agentd:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations
- Configure proper CORS origins
- Set up image storage persistence
- Implement rate limiting
- Add authentication for sensitive endpoints
- Monitor AI service usage and costs
- Set up logging and monitoring
- Configure backup and recovery procedures

---

## API Rate Limits & Quotas

### Azure OpenAI Limits
- **Request Rate:** Depends on Azure OpenAI tier
- **Token Limits:** 1500 tokens per expert analysis
- **Concurrent Requests:** Limited by Azure configuration

### Backend Limits  
- **Concurrent Analyses:** 10 simultaneous requests
- **File Upload Size:** 50MB maximum
- **Analysis Timeout:** 300 seconds maximum

### Monitoring & Metrics
- Track API usage and response times
- Monitor AI service costs and token usage
- Alert on high error rates or timeouts
- Log detailed analysis results for debugging
