# Frontend API & Functions Documentation

## Project Overview
QualiTest Analytics is an Enterprise-Grade UI Quality Assurance Platform with a React frontend that interacts with a FastAPI backend for UI screenshot analysis and management.

## Project Structure
```
front/agent-front/
├── src/
│   ├── Components/
│   │   ├── Dashboard.jsx          # Main dashboard component
│   │   ├── Orchestrator.jsx       # Quality analysis orchestrator
│   │   ├── ChangeVerification.jsx # Visual regression testing
│   │   └── *.css                  # Component styles
│   ├── App.jsx                    # Root application component
│   └── main.jsx                   # Application entry point
├── public/                        # Static assets
├── package.json                   # Dependencies
└── vite.config.js                 # Build configuration
```

## API Endpoints & Data Structures

### 1. System Status Check

**Endpoint:** `GET /orchestrator-status`
**Purpose:** Health check for backend service
**Request Headers:**
```javascript
{
  'Content-Type': 'application/json'
}
```
**Response:** HTTP Status Code (200 = Online, 4xx/5xx = Offline)
**Frontend Usage:**
```javascript
const checkSystemStatus = async () => {
  try {
    const response = await fetch('http://127.0.0.1:8000/orchestrator-status', {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(5000)
    });
    setSystemStatus(response.ok ? 'online' : 'offline');
  } catch (error) {
    setSystemStatus('offline');
  }
};
```

### 2. Image Upload

**Endpoint:** `POST /upload-image`
**Purpose:** Upload new UI screenshot to backend
**Request Data:** `FormData` object
```javascript
const formData = new FormData();
formData.append('file', fileObject);
```
**Expected Response:**
```json
{
  "status": "success",
  "filename": "uploaded_screenshot.png",
  "message": "Image uploaded successfully"
}
```
**Frontend Implementation:**
```javascript
const handleImageUpload = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  
  setUploading(true);
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const response = await fetch('http://127.0.0.1:8000/upload-image', {
      method: 'POST',
      body: formData
    });
    
    if (response.ok) {
      const data = await response.json();
      setImageFilenames(prev => [...prev, data.filename]);
      setSelectedImage(data.filename);
    }
  } catch (err) {
    console.error('Upload failed:', err);
  } finally {
    setUploading(false);
  }
};
```

### 3. Static Image Serving

**Endpoint:** `GET /amadeus-images/<filename>`
**Purpose:** Serve images from Amadeus cockpit folder
**Request:** Direct HTTP GET to image URL
**Response:** Binary image data (PNG, JPG, etc.)
**Frontend Usage:**
```javascript
const backendUrl = 'http://127.0.0.1:8000/amadeus-images/';
const imageUrl = `${backendUrl}${selectedImage}`;

// Used in JSX
<img 
  src={imageUrl} 
  alt={selectedImage}
  className="gallery-image"
  style={{ maxWidth: '320px', maxHeight: '180px' }}
/>
```

### 4. Image List (Recommended Future Enhancement)

**Endpoint:** `GET /list-images`
**Purpose:** Get list of available screenshots
**Expected Response:**
```json
{
  "images": [
    "screen1.png",
    "screen2.jpg", 
    "screen3.jpeg",
    "uploaded_screenshot.png"
  ],
  "total": 4
}
```

## Frontend State Management

### Dashboard Component State
```javascript
const [systemStatus, setSystemStatus] = useState('checking');
const [activeTab, setActiveTab] = useState('analysis');
const [lastChecked, setLastChecked] = useState(new Date());
const [imageFilenames, setImageFilenames] = useState([]);
const [selectedImage, setSelectedImage] = useState('');
const [uploading, setUploading] = useState(false);
```

### State Values & Meanings
- **systemStatus:** `'online' | 'offline' | 'checking'`
- **activeTab:** `'analysis' | 'verification'`
- **lastChecked:** JavaScript Date object for last status check
- **imageFilenames:** Array of available image file names
- **selectedImage:** Currently selected image filename
- **uploading:** Boolean indicating upload in progress

## Key Functions

### 1. System Status Management
```javascript
const checkSystemStatus = async () => {
  // Checks backend health every 30 seconds
  // Updates systemStatus state
  // Handles timeout and error cases
};

const getStatusIcon = () => {
  // Returns appropriate icon based on system status
  // Maps status to React Icons (FiCheck, FiX, FiRefreshCw)
};
```

### 2. Image Management
```javascript
const handleSelectChange = (e) => {
  // Updates selected image when dropdown changes
  setSelectedImage(e.target.value);
};

const handleImageUpload = async (e) => {
  // Handles file upload to backend
  // Updates image list on success
  // Shows upload progress
};
```

### 3. UI State Management
```javascript
const formatLastChecked = (date) => {
  // Formats timestamp for display
  // Returns HH:MM format
};
```

## Component Integration

### Tab System
The dashboard uses a tab-based navigation:
- **Quality Analysis Tab:** Renders `<Orchestrator />` component
- **Visual Regression Tab:** Renders `<ChangeVerification />` component

### Image Gallery Integration
The image gallery is embedded within the Quality Analysis tab and provides:
- File upload interface
- Image selection dropdown
- Live image preview
- Error handling for failed uploads

## Error Handling

### Network Errors
```javascript
try {
  // API call
} catch (error) {
  console.log('Backend service not available:', error.message);
  setSystemStatus('offline');
}
```

### Upload Errors
```javascript
if (response.ok) {
  // Handle success
} else {
  alert('Upload failed');
}
```

## Styling & UI

### CSS Classes
- `.dashboard-wrapper` - Main container
- `.dashboard-header` - Top navigation bar
- `.dashboard-nav` - Tab navigation
- `.dashboard-main` - Content area
- `.image-gallery` - Image upload/selection section
- `.gallery-item` - Individual image container

### Responsive Design
- Uses flexible layouts with CSS Grid/Flexbox
- Images auto-resize with `maxWidth` and `maxHeight`
- Mobile-friendly navigation tabs

## Backend Dependencies

The frontend expects these backend endpoints to be available:
1. `GET /orchestrator-status` - System health check
2. `POST /upload-image` - File upload handling
3. `GET /amadeus-images/<filename>` - Static file serving
4. `GET /list-images` - (Optional) Dynamic image listing

## Environment Configuration

### Backend URL Configuration
```javascript
// Currently hardcoded - should be moved to environment variables
const backendUrl = 'http://127.0.0.1:8000/amadeus-images/';
const apiBaseUrl = 'http://127.0.0.1:8000';
```

### Recommended Environment Setup
```javascript
// .env file
REACT_APP_BACKEND_URL=http://127.0.0.1:8000
REACT_APP_IMAGES_URL=http://127.0.0.1:8000/amadeus-images
```

## Development Workflow

1. **Start Backend:** Ensure FastAPI server is running on port 8000
2. **Start Frontend:** `npm run dev` (Vite development server)
3. **Test Upload:** Use file input to upload test images
4. **Verify Images:** Check dropdown populates with available images
5. **Test Selection:** Verify image preview updates when selection changes

## Future Enhancements

1. **Dynamic Image Loading:** Implement `/list-images` endpoint integration
2. **Image Management:** Add delete/rename functionality
3. **Error UI:** Replace alerts with toast notifications
4. **Loading States:** Add skeleton loaders for image previews
5. **Image Optimization:** Add client-side resize before upload
6. **Drag & Drop:** Enhance upload UX with drag-and-drop zone

## Troubleshooting

### Common Issues
1. **Images not loading:** Check if backend `/amadeus-images` endpoint is configured
2. **Upload failing:** Verify backend `/upload-image` endpoint exists
3. **System showing offline:** Check if backend is running on port 8000
4. **CORS errors:** Ensure backend CORS middleware allows frontend origin

### Debug Commands
```bash
# Check if backend is running
curl http://127.0.0.1:8000/orchestrator-status

# Test image serving
curl http://127.0.0.1:8000/amadeus-images/screen1.png

# Check frontend console for errors
# Open browser dev tools > Console tab
```
