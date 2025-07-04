# LLM-GEN-REPORT

## Overview

LLM-GEN-REPORT is a comprehensive full-stack data analysis and visualization platform that combines the power of Large Language Models (LLMs) with interactive data visualization. Upload your data files, ask questions in natural language, and get intelligent insights with beautiful charts and visualizations.

**🚀 Key Features:**
- **AI-Powered Analysis**: Leverages Anthropic Claude for intelligent data interpretation
- **Interactive Chat Interface**: Natural language queries with persistent chat history
- **Dynamic Visualizations**: Automatic chart generation (bar, pie, line, scatter, doughnut)
- **Multi-Format Support**: CSV, Excel (.xlsx, .xls, .xlsm, .xlsb), ODF (.ods, .odt)
- **Export Functionality**: Download charts as PNG, PDF, or data as CSV/JSON
- **Session Persistence**: Save and restore analysis sessions
- **Real-time Processing**: Instant responses with graceful loading states
- **Modern UI/UX**: Clean, responsive design with dark/light mode support

---

## 🏗️ Architecture

### Project Structure
```
LLM-GEN-REPORT/
├── backend/                    # FastAPI backend
│   ├── main.py                # Main server with API endpoints
│   ├── services/              # Business logic services
│   │   ├── database_service.py    # Session & data persistence
│   │   ├── export_service.py      # Chart & data export functionality
│   │   └── visualization_service.py # Chart data generation
│   ├── models/                # Data models and schemas
│   ├── data/                  # SQLite database storage
│   ├── uploads/               # Uploaded file storage
│   ├── exports/               # Generated export files
│   └── requirements.txt       # Python dependencies
├── frontend/                  # React + Vite frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── ChatScreen.jsx     # Main chat interface
│   │   │   ├── UploadScreen.jsx   # File upload interface
│   │   │   ├── ExportButton.jsx   # Chart export functionality
│   │   │   └── SessionHistory.jsx # Session management
│   │   └── styles/           # CSS styling
│   └── package.json          # Node.js dependencies
└── README.md                 # This file
```

### Technology Stack

**Backend:**
- **FastAPI**: High-performance Python web framework
- **Anthropic Claude**: Advanced LLM for data analysis
- **Pandas**: Data manipulation and analysis
- **SQLite**: Lightweight database for session storage
- **Chart.js Integration**: Server-side chart data generation

**Frontend:**
- **React 19**: Modern UI framework
- **Vite**: Fast build tool and dev server
- **Chart.js**: Interactive chart library
- **Marked**: Markdown rendering for AI responses

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+** with pip
- **Node.js 16+** with npm
- **Anthropic API Key** ([Get one here](https://console.anthropic.com/))

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables for local development
echo "ANTHROPIC_API_KEY=your_api_key_here" > .env
# In a Vercel deployment, configure this variable in the Vercel dashboard

# Start the backend server
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

### 3. Access the Application

Open your browser and navigate to:
- **Frontend**: http://localhost:5173 (or the port shown in terminal)
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

---

## 📊 Features & Usage

### Data Upload & Analysis
1. **Upload Files**: Drag & drop or browse to upload CSV, Excel, or ODF files
2. **Ask Questions**: Use natural language to query your data
3. **Get Insights**: Receive AI-powered analysis with automatic visualizations
4. **Export Results**: Download charts and data in various formats

### Supported File Formats
- **CSV**: Comma-separated values
- **Excel**: .xlsx, .xls, .xlsm, .xlsb
- **OpenDocument**: .ods (spreadsheets), .odt (documents)

### Chart Types
- **Bar Charts**: For categorical comparisons
- **Pie Charts**: For part-to-whole relationships
- **Line Charts**: For trends over time
- **Scatter Plots**: For correlation analysis
- **Doughnut Charts**: For hierarchical data

### Export Options
- **Charts**: PNG, PDF formats
- **Data**: CSV, JSON formats
- **Sessions**: Save and restore complete analysis sessions

### Slide-Level Visualization CLI

Use `auto_visualize.py` to quickly generate charts from a ZIP bundle of slide folders. Each folder name must follow the pattern `Slide-<n>-<Title>`.

```bash
python auto_visualize.py path/to/bundle.zip [--pptx]
```

The script extracts the bundle, automatically chooses a chart type based on the folder title, creates a PNG for each slide inside an `output` directory and optionally assembles them into a PowerPoint file.

---

## 🔧 API Endpoints

### Core Endpoints
- `GET /analyze` - Basic web form for manual testing
- `POST /analyze` - Submit data and query for AI analysis
- `POST /upload` - Upload data files (max 200MB per file)
- `POST /visualize/zip` - Generate slide images from a zipped bundle (accepts optional `session_id`)
- `POST /process` - Auto-route ZIP bundles to `/visualize/zip` or other files to `/analyze`; pass `session_id` to persist slide info
- `GET /session/{session_id}` - Retrieve saved session data
- `GET /health` - Health check endpoint

Example request:

```bash
curl -F "file=@slides.zip" -F "pptx=true" -F "session_id=1234" \
  http://localhost:8000/visualize/zip
```

### Export Endpoints
- `POST /export/chart` - Export chart as image or PDF
- `POST /export/data` - Export data as CSV or JSON

---
### Backend test plan (CI matrix)

| Layer | Tool | Trigger |
|-------|------|---------|
| Static/spec | jest-openapi | every push |
| Unit | Jest + Supertest | every push |
| Contract | Pact provider verify | every push |
| Integration | Jest (vercel dev) | local pre-commit |
| Preview Smoke | Playwright (FE repo) | PR build |
| Load | k6 (50 vus 60 s) | release branch |
| Nightly Prod | Playwright + health check | cron |
| Security | Jest (OWASP strings) | weekly |

---

## 🎨 UI/UX Features

### Chat Interface
- **Persistent History**: All conversations saved and retrievable
- **Smart Suggestions**: Context-aware follow-up question prompts
- **Loading States**: Graceful loading indicators during processing
- **Responsive Design**: Works seamlessly on desktop and mobile

### Visualization
- **Static Rendering**: Charts render once and remain stable
- **Interactive Elements**: Hover effects and data point details
- **Export Integration**: One-click export from any chart
- **Theme Support**: Automatic dark/light mode switching

### Session Management
- **Auto-Save**: Sessions automatically saved during analysis
- **Session History**: Browse and restore previous analysis sessions
- **File Persistence**: Uploaded files linked to sessions

---

## 🧪 Development

### Running Tests

**Frontend Tests:**
```bash
cd frontend
npm run test
```

**Backend Tests:**
```bash
cd backend
python -m pytest  # If you have tests
```

### Development Commands

**Frontend:**
```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run preview  # Preview production build
npm run lint     # Run ESLint
```

**Backend:**
```bash
uvicorn main:app --reload  # Development server with auto-reload
uvicorn main:app --host 0.0.0.0 --port 8000  # Production server
```

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory for local development.
When deploying on Vercel, set these variables via the Vercel dashboard:

```env
# Required
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional
DATABASE_URL=sqlite:///./data/app.db
MAX_FILE_SIZE=209715200  # 200MB in bytes
UPLOAD_DIR=./uploads
EXPORT_DIR=./exports
```

### Customization

**Chart Styling**: Modify chart options in `frontend/src/components/ChatScreen.jsx`
**API Configuration**: Update settings in `backend/main.py`
**UI Themes**: Customize styles in `frontend/src/styles/`

## Deploying on Vercel

1. Install the Vercel CLI if you haven't already and log in:

```bash
npm install -g vercel
vercel login
```

2. Ensure the `requirements.txt` file is in the repository root. Vercel's Python
   runtime will install dependencies from this location when building your
   serverless function.

3. In your Vercel project settings configure the environment variables listed in
   the **Environment Variables** section above. At a minimum set
   `ANTHROPIC_API_KEY`.

4. Deploy the application:

```bash
vercel deploy
```

5. If you are also serving a built frontend, adjust `vercel.json` so requests to
   `/api/` go to the backend and other paths serve static assets. A simple
   example:

```json
{
  "routes": [
    { "src": "/api/(.*)", "dest": "api/index.py" },
    { "src": "/(.*)", "dest": "frontend/dist/$1" }
  ]
}
```

---

## 🚨 Troubleshooting

### Common Issues

**Backend not starting:**
- Verify Python version (3.8+)
- Check if port 8000 is available
- Ensure Anthropic API key is valid

**Frontend not loading:**
- Verify Node.js version (16+)
- Clear npm cache: `npm cache clean --force`
- Check if port 5173 is available

**Charts not displaying:**
- Ensure backend is running and accessible
- Check browser console for JavaScript errors
- Verify data format compatibility

**File upload failures:**
 - Check file size (max 200MB)
 - Verify file format is supported
 - Ensure sufficient disk space

### Performance Tips

- **Large Files**: Consider splitting very large datasets
- **Memory Usage**: Monitor system resources during processing
- **Network**: Ensure stable connection for API calls

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Commit with descriptive messages
5. Push to your fork and create a Pull Request

### Development Branch
- Main development happens on the `development` branch
- Create feature branches from `development`
- Merge back to `development` via Pull Request

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🆘 Support

For issues, questions, or contributions:
- **GitHub Issues**: [Create an issue](https://github.com/SREERAM-YASHASVI/LLM-GEN-REP/issues)
- **Documentation**: Check this README and API docs at `/docs`
- **Community**: Join discussions in GitHub Discussions

---

## 🔮 Roadmap

- [ ] **Real-time Collaboration**: Multi-user session sharing
- [ ] **Advanced Analytics**: Statistical analysis tools
- [ ] **Custom Visualizations**: User-defined chart types
- [ ] **API Integration**: Connect to external data sources
- [ ] **Mobile App**: Native mobile application
- [ ] **Enterprise Features**: SSO, audit logs, advanced security

---

*Built with ❤️ using FastAPI, React, and Anthropic Claude*
