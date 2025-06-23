from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import os
import logging
from dotenv import find_dotenv, load_dotenv
from pathlib import Path
import pandas as pd
import io
import anthropic
import json
import re
import difflib
import importlib
import uuid
from datetime import datetime
import base64
import logging

# Attempt to import heavy optional dependencies; fallback to stubs during testing.
try:
    from backend.services.export_service import ExportService  # pragma: no cover
except ImportError as e:  # pragma: no cover
    logging.warning(
        "Optional dependency failed to import during startup (likely in test environment): %s."
        "\nFalling back to stubbed ExportService.",
        e,
    )

    class ExportService:  # type: ignore
        """Stubbed export service used in environments without matplotlib/seaborn."""

        async def export_chart_to_png(self, *args, **kwargs):
            raise NotImplementedError("Chart export is disabled in this environment")

        async def export_chart_to_base64(self, *args, **kwargs):
            raise NotImplementedError("Chart export is disabled in this environment")

        async def save_chart_to_file(self, *args, **kwargs):
            raise NotImplementedError("Chart export is disabled in this environment")

        async def export_multiple_charts(self, *args, **kwargs):
            raise NotImplementedError("Chart export is disabled in this environment")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Simple in-memory session storage (replace with database in production)
sessions_store = {}

# Configure CORS to echo back the request Origin and restrict allowed methods/headers
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",  # match any origin and echo it back
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Attempt to locate a .env file automatically. If not found, fall back to a path
# relative to the project root (one directory up from this backend package).
_env_path_str = find_dotenv()
_env_path = Path(_env_path_str) if _env_path_str else Path()
if not _env_path_str or not _env_path.exists():
    _env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path, override=True)

# Determine the directory used for file uploads. In serverless environments like Vercel
# only `/tmp` is writable, so default to that location. Users can override this via the
# `UPLOAD_DIR` environment variable configured in the Vercel dashboard.
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"  # Example endpoint

def check_excel_dependencies():
    missing = []
    for pkg in ['openpyxl', 'xlrd', 'odfpy', 'pyxlsb']:
        if importlib.util.find_spec(pkg) is None:
            missing.append(pkg)
    return missing

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI server is starting up...")
    missing = check_excel_dependencies()
    if missing:
        logger.warning(f"Missing Excel dependencies: {missing}. Excel file support may be limited.")

@app.get("/")
def root():
    return {"message": "Your backend is working. Or is it?"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Retrieve session data for chat history persistence"""
    try:
        logger.info(f"Session retrieval requested for: {session_id}")
        
        # Check if session exists in memory
        if session_id in sessions_store:
            session_data = sessions_store[session_id]
            logger.info(f"Found session {session_id} with {len(session_data.get('chatHistory', []))} chat entries")
            return session_data
        else:
            # Return empty session data for new sessions
            logger.info(f"Session {session_id} not found, returning empty session")
            return {
                "session": {
                    "id": session_id,
                    "dataset_info": {
                        "columns": [],
                        "file_names": []
                    }
                },
                "chatHistory": [],
                "visualizations": []
            }
    except Exception as e:
        logger.error(f"Error retrieving session {session_id}: {e}")
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    logger.info(f"/upload endpoint called with {len(files)} file(s)")
    max_size_mb = 100  # Example: 100MB per file
    uploaded = []
    for file in files:
        logger.info(f"Processing file: {file.filename}")
        contents = await file.read()
        size_mb = len(contents) / (1024 * 1024)
        if size_mb > max_size_mb:
            logger.warning(f"File {file.filename} exceeds size limit: {size_mb:.2f}MB")
            raise HTTPException(status_code=413, detail=f"File {file.filename} exceeds {max_size_mb}MB limit.")
        save_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(save_path, "wb") as f:
            f.write(contents)
        uploaded.append({
            "filename": file.filename,
            "size_mb": round(size_mb, 2),
            "content_type": file.content_type
        })
    logger.info(f"Successfully uploaded {len(uploaded)} file(s)")
    return JSONResponse(content={"uploaded": uploaded})

@app.get("/analyze", include_in_schema=False)
async def analyze_form() -> Response:
    """Return a tiny HTML form for the POST /analyze endpoint."""
    html_content = """
    <html>
        <body>
            <h3>/analyze test form</h3>
            <form action="/analyze" method="post" enctype="multipart/form-data">
                <input type="text" name="query" placeholder="Query" required />
                <input type="file" name="files" multiple required />
                <button type="submit">Submit</button>
            </form>
        </body>
    </html>
    """
    return Response(content=html_content, media_type="text/html")


@app.post("/analyze")
async def analyze(
    query: str = Form(...),
    files: List[UploadFile] = File(...),
    chat_history: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None)
):
    logger.info(f"/analyze endpoint called with query: {query} and {len(files)} file(s)")
    logger.debug(f"Session ID: {session_id}")
    logger.debug(f"Files received: {[f.filename for f in files]}")
    logger.debug(f"Chat history length: {len(chat_history) if chat_history else 0}")
    # Filter out empty files that frontend sends to satisfy FastAPI requirements
    valid_files = [f for f in files if f.filename and f.filename.strip() != '']
    
    if not valid_files or len(valid_files) == 0:
        raise HTTPException(status_code=400, detail="No valid files uploaded.")
    dfs = []
    all_columns = set()
    file_previews = []
    excel_sheets_info = []
    for file in valid_files:
        try:
            file_content = await file.read()
            file_text = file_content.decode(errors="ignore")
            file_ext = file.filename.lower().split('.')[-1]
            if file_ext == 'csv':
                df = pd.read_csv(io.StringIO(file_text))
                dfs.append(df)
                all_columns.update([str(col) for col in df.columns])
                file_previews.append(f"{file.filename}:\n" + df.head(10).to_csv(index=False))
            elif file_ext in ['xlsx', 'xls', 'xlsm', 'xlsb', 'odf', 'ods', 'odt']:
                excel_bytes = io.BytesIO(file_content)
                try:
                    df = pd.read_excel(excel_bytes, engine='openpyxl')
                    sheets = pd.ExcelFile(excel_bytes, engine='openpyxl').sheet_names
                    excel_sheets_info.append(f"{file.filename}: {sheets}")
                except Exception:
                    try:
                        df = pd.read_excel(excel_bytes, engine='xlrd')
                        sheets = pd.ExcelFile(excel_bytes, engine='xlrd').sheet_names
                        excel_sheets_info.append(f"{file.filename}: {sheets}")
                    except Exception:
                        try:
                            df = pd.read_excel(excel_bytes, engine='odf')
                            sheets = pd.ExcelFile(excel_bytes, engine='odf').sheet_names
                            excel_sheets_info.append(f"{file.filename}: {sheets}")
                        except Exception:
                            try:
                                df = pd.read_excel(excel_bytes, engine='pyxlsb')
                                sheets = pd.ExcelFile(excel_bytes, engine='pyxlsb').sheet_names
                                excel_sheets_info.append(f"{file.filename}: {sheets}")
                            except Exception as e4:
                                logger.error(f"Excel parsing failed for {file.filename}: {e4}")
                                continue
                dfs.append(df)
                all_columns.update([str(col) for col in df.columns])
                file_previews.append(f"{file.filename}:\n" + df.head(10).to_csv(index=False))
            else:
                logger.warning(f"Unsupported file type: {file.filename}")
                continue
        except Exception as e:
            logger.warning(f"Could not load file {file.filename}: {e}")
            continue
    if not dfs:
        raise HTTPException(status_code=400, detail="No valid CSV or Excel files uploaded.")
    # Merge all DataFrames (outer join on columns)
    try:
        df_merged = pd.concat(dfs, ignore_index=True, sort=False)
    except Exception as e:
        logger.error(f"Error merging DataFrames: {e}")
        raise HTTPException(status_code=400, detail="Failed to merge uploaded files.")
    csv_columns = list(all_columns)
    file_preview = "\n\n".join(file_previews)
    excel_sheets = ", ".join(excel_sheets_info) if excel_sheets_info else None

    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set. Returning placeholder response.")
        return {"response": f"[Placeholder] Would analyze: '{query}' on file '{valid_files[0].filename}'", "chartData": None, "chatHistory": chat_history, "sessionId": session_id}

    logger.info("ANTHROPIC_API_KEY is present. Preparing to call Anthropic API.")
    # Parse chat history if provided
    history_list = []
    if chat_history:
        try:
            history_list = json.loads(chat_history)
        except Exception as e:
            logger.warning(f"Could not parse chat_history: {e}")
            history_list = []
    # Build Anthropic messages context
    anthropic_messages = []
    for item in history_list:
        if 'query' in item:
            anthropic_messages.append({"role": "user", "content": item['query']})
        if 'response' in item:
            anthropic_messages.append({"role": "assistant", "content": item['response']})
    # Add the new user query with explicit chart spec instructions and CSV/Excel columns
    chart_spec_instructions = (
        "If the user's query requests a chart or visualization, "
        "please output a JSON chart specification after your answer. "
        "The JSON should be delimited by triple backticks and 'json', and include: "
        "type (bar, pie, line, doughnut, scatter), x (column for x-axis or labels), y (column for y-axis or values), "
        "labels (for legend), and any other relevant options. "
        "Example:\n"
        "```json\n"
        "{\n  \"type\": \"bar\", \"x\": \"Month\", \"y\": \"Sales\", \"labels\": [\"Jan\", \"Feb\", \"Mar\"] }\n"
        "```\n"
        "If no chart is needed, do not output any JSON.\n"
        f"\nThe columns available are: {csv_columns}"
        + (f"\nExcel sheets in this file: {excel_sheets}" if excel_sheets else "")
    )
    anthropic_messages.append({
        "role": "user",
        "content": f"{query}\n\nFile preview (first 10 rows):\n{file_preview}\n\n{chart_spec_instructions}"
    })
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        logger.info("Anthropic client initialized.")
        message = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1024,
            messages=anthropic_messages
        )
        logger.info(f"Received response from Anthropic SDK: {str(message)[:300]}")
        content_text = message.content[0].text if hasattr(message.content[0], 'text') else str(message.content)
        logger.info(f"Anthropic response content: {content_text[:300]}")

        # Step 2: Extract JSON chart spec from LLM response
        chart_spec = None
        chart_spec_match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", content_text)
        if chart_spec_match:
            try:
                chart_spec = json.loads(chart_spec_match.group(1))
                logger.info(f"Extracted chart spec: {chart_spec}")
            except Exception as e:
                logger.warning(f"Failed to parse chart spec JSON: {e}")
        else:
            logger.info("No chart spec found in LLM response.")

        # Step 3: Generate chart data from CSV using chart_spec if present
        chart_data = None  # Initialize chart_data to avoid UnboundLocalError
        
        def fuzzy_match(col, columns):
            # Try exact, case-insensitive, and close matches
            if not col or not columns:
                return None
            col_lower = col.lower().replace(' ', '').replace('_', '')
            for c in columns:
                if col_lower == c.lower().replace(' ', '').replace('_', ''):
                    return c
            # Use difflib for close matches
            matches = difflib.get_close_matches(col, columns, n=1, cutoff=0.7)
            if matches:
                return matches[0]
            return None

        if chart_spec and df_merged is not None:
            try:
                chart_type = chart_spec.get('type', '').lower()
                x_col = chart_spec.get('x')
                y_col = chart_spec.get('y')
                labels = chart_spec.get('labels')
                values = chart_spec.get('values')
                colors = chart_spec.get('colors')
                title = chart_spec.get('title', '')
                # Fuzzy match columns
                x_col_actual = fuzzy_match(x_col, csv_columns) if x_col else None
                y_col_actual = fuzzy_match(y_col, csv_columns) if y_col else None
                if chart_type in ['pie', 'doughnut'] and labels and values:
                    chart_data = {
                        "type": chart_type,
                        "labels": labels,
                        "datasets": [{
                            "data": values,
                            "backgroundColor": colors if colors else ["#8884d8"] * len(labels),
                            "label": title
                        }],
                        "options": chart_spec.get('options', {})
                    }
                elif chart_type in ['bar', 'line', 'doughnut', 'pie']:
                    if x_col_actual and y_col_actual and x_col_actual in df_merged.columns and y_col_actual in df_merged.columns:
                        grouped = df_merged.groupby(x_col_actual)[y_col_actual].sum()
                        chart_data = {
                            "type": chart_type,
                            "labels": grouped.index.tolist(),
                            "datasets": [{
                                "label": y_col_actual,
                                "data": grouped.values.tolist(),
                                "backgroundColor": "#8884d8"
                            }]
                        }
                    elif x_col_actual and x_col_actual in df_merged.columns:
                        value_counts = df_merged[x_col_actual].value_counts().head(20)
                        chart_data = {
                            "type": chart_type,
                            "labels": value_counts.index.tolist(),
                            "datasets": [{
                                "label": x_col_actual,
                                "data": value_counts.values.tolist(),
                                "backgroundColor": "#8884d8"
                            }]
                        }
                    else:
                        # User-friendly error with suggestions
                        error_msg = f"Could not find required columns for chart.\nRequested: x='{x_col}', y='{y_col}'.\nAvailable columns: {csv_columns}."
                        # Suggest closest matches
                        suggestions = []
                        if x_col:
                            match = fuzzy_match(x_col, csv_columns)
                            if match:
                                suggestions.append(f"x: Did you mean '{match}'?")
                        if y_col:
                            match = fuzzy_match(y_col, csv_columns)
                            if match:
                                suggestions.append(f"y: Did you mean '{match}'?")
                        if suggestions:
                            error_msg += "\nSuggestions: " + ", ".join(suggestions)
                        logger.info(error_msg)
                        return {"response": content_text + "\n\n" + error_msg, "chartData": None, "chatHistory": history_list + [{"query": query, "response": content_text}], "sessionId": session_id}
                elif chart_type == 'scatter':
                    if x_col_actual and y_col_actual and x_col_actual in df_merged.columns and y_col_actual in df_merged.columns:
                        chart_data = {
                            "type": "scatter",
                            "datasets": [{
                                "label": f"{y_col_actual} vs {x_col_actual}",
                                "data": [{"x": float(row[x_col_actual]), "y": float(row[y_col_actual])} for _, row in df_merged[[x_col_actual, y_col_actual]].dropna().iterrows()],
                                "backgroundColor": "#8884d8"
                            }]
                        }
                    else:
                        error_msg = f"Could not find required columns for scatter plot.\nRequested: x='{x_col}', y='{y_col}'.\nAvailable columns: {csv_columns}."
                        suggestions = []
                        if x_col:
                            match = fuzzy_match(x_col, csv_columns)
                            if match:
                                suggestions.append(f"x: Did you mean '{match}'?")
                        if y_col:
                            match = fuzzy_match(y_col, csv_columns)
                            if match:
                                suggestions.append(f"y: Did you mean '{match}'?")
                        if suggestions:
                            error_msg += "\nSuggestions: " + ", ".join(suggestions)
                        logger.info(error_msg)
                        return {"response": content_text + "\n\n" + error_msg, "chartData": None, "chatHistory": history_list + [{"query": query, "response": content_text}], "sessionId": session_id}
                if chart_data:
                    logger.info(f"Generated chart data from chart_spec: {chart_data}")
            except Exception as e:
                logger.warning(f"Error generating chart data from chart_spec: {e}")
        # If no chart_spec or failed, fallback to previous chartData logic (device count)

        # Update chat history
        updated_history = history_list + [{"query": query, "response": content_text, "chartData": chart_data}]
        
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
            logger.info(f"Generated new session ID: {session_id}")
        
        # Save session data to memory
        sessions_store[session_id] = {
            "session": {
                "id": session_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "dataset_info": {
                    "columns": csv_columns,
                    "file_names": [f.filename for f in valid_files],
                    "totalRows": len(df_merged),
                    "totalColumns": len(csv_columns)
                }
            },
            "chatHistory": updated_history,
            "visualizations": [{"chart_data": chart_data, "created_at": datetime.now().isoformat()}] if chart_data else []
        }
        
        logger.info(f"Saved session {session_id} with {len(updated_history)} chat entries")
        
        return {
            "response": content_text, 
            "chartData": chart_data, 
            "chatHistory": updated_history,
            "csvColumns": csv_columns,  # Send columns directly to frontend
            "datasetInfo": {
                "totalRows": len(df_merged),
                "totalColumns": len(csv_columns),
                "fileNames": [f.filename for f in valid_files]
            },
            "sessionId": session_id  # Return session ID for frontend tracking
        }
    except Exception as e:
        logger.error(f"Error calling Anthropic SDK: {e}")
        api_error = getattr(anthropic, "APIError", Exception)
        auth_error = getattr(anthropic, "AuthenticationError", None)
        rate_error = getattr(anthropic, "RateLimitError", None)
        timeout_error = getattr(anthropic, "APITimeoutError", None)
        conn_error = getattr(anthropic, "APIConnectionError", None)

        if auth_error and isinstance(e, auth_error):
            raise HTTPException(status_code=401, detail="Invalid Anthropic API key")
        if rate_error and isinstance(e, rate_error):
            raise HTTPException(status_code=429, detail="Anthropic API rate limit exceeded")
        if timeout_error and isinstance(e, timeout_error):
            raise HTTPException(status_code=504, detail="Anthropic API request timed out")
        if conn_error and isinstance(e, conn_error):
            raise HTTPException(status_code=502, detail="Error connecting to Anthropic API")
        if isinstance(e, api_error):
            raise HTTPException(status_code=502, detail=str(e))

        raise HTTPException(status_code=502, detail=f"Error communicating with Anthropic API: {e}")

@app.post("/export/data")
async def export_data(request: dict):
    """Export chart data in various formats"""
    try:
        chart_data = request.get('chart_data')
        format_type = request.get('format', 'csv').lower()
        title = request.get('title', 'chart_data')
        
        if not chart_data:
            raise HTTPException(status_code=400, detail="No chart data provided")
        
        # Extract data from chart_data
        datasets = chart_data.get('datasets', [])
        labels = chart_data.get('labels', [])
        
        if not datasets:
            raise HTTPException(status_code=400, detail="No datasets found in chart data")
        
        if format_type == 'csv':
            # Create CSV content
            import io
            import csv
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            if labels:
                header = ['Label'] + [f"Dataset_{i+1}" for i in range(len(datasets))]
                writer.writerow(header)
                
                # Write data rows
                for i, label in enumerate(labels):
                    row = [label]
                    for dataset in datasets:
                        data = dataset.get('data', [])
                        value = data[i] if i < len(data) else ''
                        row.append(value)
                    writer.writerow(row)
            else:
                # If no labels, just export the data
                header = [f"Dataset_{i+1}" for i in range(len(datasets))]
                writer.writerow(header)
                
                max_length = max(len(dataset.get('data', [])) for dataset in datasets)
                for i in range(max_length):
                    row = []
                    for dataset in datasets:
                        data = dataset.get('data', [])
                        value = data[i] if i < len(data) else ''
                        row.append(value)
                    writer.writerow(row)
            
            csv_content = output.getvalue()
            output.close()
            
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={title}.csv"}
            )
            
        elif format_type == 'json':
            # Create JSON content
            json_data = {
                "title": title,
                "chart_data": chart_data,
                "exported_at": datetime.now().isoformat()
            }
            
            json_content = json.dumps(json_data, indent=2)
            
            return Response(
                content=json_content,
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={title}.json"}
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format_type}")
            
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/sessions")
async def get_sessions():
    """Get all available sessions"""
    try:
        sessions_list = []
        for session_id, session_data in sessions_store.items():
            session_info = session_data.get('session', {})
            chat_history = session_data.get('chatHistory', [])
            visualizations = session_data.get('visualizations', [])
            
            # Get the latest query as title
            latest_query = "Untitled Session"
            if chat_history:
                latest_query = chat_history[-1].get('query', 'Untitled Session')[:50]
            
            sessions_list.append({
                "id": session_id,
                "title": latest_query,
                "created_at": session_info.get('created_at'),
                "updated_at": session_info.get('updated_at'),
                "chat_count": len(chat_history),
                "visualization_count": len(visualizations),
                "dataset_info": session_info.get('dataset_info', {})
            })
        
        # Sort by updated_at (most recent first)
        sessions_list.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        
        return {"sessions": sessions_list}
        
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sessions: {str(e)}")

@app.post("/export/session/{session_id}/dashboard")
async def export_session_dashboard(session_id: str):
    """Export a session's visualizations as a dashboard"""
    try:
        if session_id not in sessions_store:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = sessions_store[session_id]
        visualizations = session_data.get('visualizations', [])
        
        if not visualizations:
            raise HTTPException(status_code=400, detail="No visualizations found in session")
        
        # Use the export service to create a dashboard
        export_service = ExportService()
        
        # Prepare charts for dashboard export
        charts = []
        for i, viz in enumerate(visualizations):
            chart_data = viz.get('chart_data')
            if chart_data:
                charts.append({
                    'chart_data': chart_data,
                    'title': f'Chart {i+1}'
                })
        
        if not charts:
            raise HTTPException(status_code=400, detail="No valid chart data found")
        
        # Export multiple charts as dashboard
        img_bytes = await export_service.export_multiple_charts(
            charts, 
            title=f"Session Dashboard - {session_id[:8]}"
        )
        
        # Convert to base64 for response
        base64_str = base64.b64encode(img_bytes).decode('utf-8')
        
        return {
            "success": True,
            "image": f"data:image/png;base64,{base64_str}",
            "session_id": session_id,
            "chart_count": len(charts)
        }
        
    except Exception as e:
        logger.error(f"Error exporting session dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard export failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
