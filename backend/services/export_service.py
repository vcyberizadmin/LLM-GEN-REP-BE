import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import io
import base64
import json
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class ExportService:
    """Service for exporting visualizations to various formats"""
    
    def __init__(self, export_dir: str = "exports"):
        self.export_dir = export_dir
        os.makedirs(export_dir, exist_ok=True)
        
        # Set up matplotlib style
        plt.style.use('default')
        sns.set_palette("husl")
    
    async def export_chart_to_png(self, chart_data: Dict[str, Any], 
                                 title: str = "", width: int = 10, height: int = 6) -> bytes:
        """Export chart data to PNG format"""
        try:
            # Debug logging
            logger.info(f"Received chart_data: {chart_data}")
            logger.info(f"Chart data type: {type(chart_data)}")
            logger.info(f"Chart data keys: {list(chart_data.keys()) if isinstance(chart_data, dict) else 'Not a dict'}")
            
            fig, ax = plt.subplots(figsize=(width, height))
            
            chart_type = chart_data.get('type', '').lower()
            labels = chart_data.get('labels', [])
            datasets = chart_data.get('datasets', [])
            
            logger.info(f"Extracted - type: {chart_type}, labels: {labels}, datasets: {datasets}")
            
            if not datasets:
                raise ValueError("No datasets found in chart data")
            
            dataset = datasets[0]  # Use first dataset
            data = dataset.get('data', [])
            
            if chart_type == 'bar':
                bars = ax.bar(labels, data, color=dataset.get('backgroundColor', '#8884d8'))
                ax.set_xlabel('Categories')
                ax.set_ylabel('Values')
                
                # Add value labels on bars
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:.1f}', ha='center', va='bottom')
                
            elif chart_type == 'line':
                ax.plot(labels, data, marker='o', linewidth=2, 
                       color=dataset.get('backgroundColor', '#8884d8'))
                ax.set_xlabel('Categories')
                ax.set_ylabel('Values')
                ax.grid(True, alpha=0.3)
                
            elif chart_type in ['pie', 'doughnut']:
                colors = dataset.get('backgroundColor', plt.cm.Set3.colors)
                wedges, texts, autotexts = ax.pie(data, labels=labels, autopct='%1.1f%%',
                                                 colors=colors, startangle=90)
                
                # Make percentage text more readable
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')
                    
            elif chart_type == 'scatter':
                # For scatter plots, data should be in format [{"x": val, "y": val}, ...]
                if data and isinstance(data[0], dict):
                    x_vals = [point.get('x', 0) for point in data]
                    y_vals = [point.get('y', 0) for point in data]
                    ax.scatter(x_vals, y_vals, alpha=0.6, 
                             color=dataset.get('backgroundColor', '#8884d8'))
                    ax.set_xlabel('X Values')
                    ax.set_ylabel('Y Values')
                    ax.grid(True, alpha=0.3)
                else:
                    raise ValueError("Invalid scatter plot data format")
            else:
                raise ValueError(f"Unsupported chart type: {chart_type}")
            
            # Set title and styling
            if title:
                ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
            
            # Rotate x-axis labels if they're too long
            if labels and max(len(str(label)) for label in labels) > 10:
                plt.xticks(rotation=45, ha='right')
            
            # Adjust layout to prevent label cutoff
            plt.tight_layout()
            
            # Save to bytes
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
            img_buffer.seek(0)
            img_bytes = img_buffer.getvalue()
            
            plt.close(fig)  # Clean up
            
            logger.info(f"Successfully exported {chart_type} chart to PNG")
            return img_bytes
            
        except Exception as e:
            logger.error(f"Error exporting chart to PNG: {e}")
            plt.close('all')  # Clean up any open figures
            raise
    
    async def export_chart_to_base64(self, chart_data: Dict[str, Any], 
                                   title: str = "") -> str:
        """Export chart to base64 encoded PNG"""
        try:
            img_bytes = await self.export_chart_to_png(chart_data, title)
            base64_str = base64.b64encode(img_bytes).decode('utf-8')
            return f"data:image/png;base64,{base64_str}"
        except Exception as e:
            logger.error(f"Error exporting chart to base64: {e}")
            raise
    
    async def save_chart_to_file(self, chart_data: Dict[str, Any], 
                               filename: str, title: str = "") -> str:
        """Save chart to file and return file path"""
        try:
            img_bytes = await self.export_chart_to_png(chart_data, title)
            
            # Ensure filename has .png extension
            if not filename.endswith('.png'):
                filename += '.png'
            
            file_path = os.path.join(self.export_dir, filename)
            
            with open(file_path, 'wb') as f:
                f.write(img_bytes)
            
            logger.info(f"Chart saved to {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving chart to file: {e}")
            raise
    
    async def export_multiple_charts(self, charts: list, 
                                   title: str = "Dashboard") -> bytes:
        """Export multiple charts to a single PNG image"""
        try:
            num_charts = len(charts)
            if num_charts == 0:
                raise ValueError("No charts provided")
            
            # Calculate grid layout
            cols = min(2, num_charts)
            rows = (num_charts + cols - 1) // cols
            
            fig, axes = plt.subplots(rows, cols, figsize=(12 * cols, 8 * rows))
            
            # Handle single chart case
            if num_charts == 1:
                axes = [axes]
            elif rows == 1:
                axes = [axes] if cols == 1 else axes
            else:
                axes = axes.flatten()
            
            for i, chart_info in enumerate(charts):
                chart_data = chart_info.get('chart_data', {})
                chart_title = chart_info.get('title', f'Chart {i+1}')
                
                ax = axes[i]
                await self._render_chart_on_axis(ax, chart_data, chart_title)
            
            # Hide unused subplots
            for i in range(num_charts, len(axes)):
                axes[i].set_visible(False)
            
            # Set main title
            fig.suptitle(title, fontsize=16, fontweight='bold')
            
            plt.tight_layout()
            
            # Save to bytes
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
            img_buffer.seek(0)
            img_bytes = img_buffer.getvalue()
            
            plt.close(fig)
            
            logger.info(f"Successfully exported {num_charts} charts to single PNG")
            return img_bytes
            
        except Exception as e:
            logger.error(f"Error exporting multiple charts: {e}")
            plt.close('all')
            raise
    
    async def _render_chart_on_axis(self, ax, chart_data: Dict[str, Any], title: str):
        """Helper method to render a chart on a specific axis"""
        chart_type = chart_data.get('type', '').lower()
        labels = chart_data.get('labels', [])
        datasets = chart_data.get('datasets', [])
        
        if not datasets:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', 
                   transform=ax.transAxes)
            ax.set_title(title)
            return
        
        dataset = datasets[0]
        data = dataset.get('data', [])
        
        if chart_type == 'bar':
            ax.bar(labels, data, color=dataset.get('backgroundColor', '#8884d8'))
            
        elif chart_type == 'line':
            ax.plot(labels, data, marker='o', linewidth=2,
                   color=dataset.get('backgroundColor', '#8884d8'))
            ax.grid(True, alpha=0.3)
            
        elif chart_type in ['pie', 'doughnut']:
            colors = dataset.get('backgroundColor', plt.cm.Set3.colors)
            ax.pie(data, labels=labels, autopct='%1.1f%%', colors=colors)
            
        elif chart_type == 'scatter':
            if data and isinstance(data[0], dict):
                x_vals = [point.get('x', 0) for point in data]
                y_vals = [point.get('y', 0) for point in data]
                ax.scatter(x_vals, y_vals, alpha=0.6,
                          color=dataset.get('backgroundColor', '#8884d8'))
                ax.grid(True, alpha=0.3)
        
        ax.set_title(title, fontsize=12, fontweight='bold')
        
        # Rotate labels if needed
        if labels and max(len(str(label)) for label in labels) > 8:
            ax.tick_params(axis='x', rotation=45)
    
    def get_supported_formats(self) -> list:
        """Get list of supported export formats"""
        return ['png', 'base64']
    
    async def cleanup_old_exports(self, days_old: int = 7):
        """Clean up export files older than specified days"""
        try:
            cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
            
            for filename in os.listdir(self.export_dir):
                file_path = os.path.join(self.export_dir, filename)
                if os.path.isfile(file_path):
                    file_time = os.path.getmtime(file_path)
                    if file_time < cutoff_time:
                        os.remove(file_path)
                        logger.info(f"Cleaned up old export: {filename}")
                        
        except Exception as e:
            logger.error(f"Error cleaning up old exports: {e}")
    
    def get_chart_stats(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get statistics about the chart data"""
        try:
            datasets = chart_data.get('datasets', [])
            if not datasets:
                return {}
            
            data = datasets[0].get('data', [])
            if not data:
                return {}
            
            # Handle different data formats
            if isinstance(data[0], dict):  # Scatter plot format
                values = [point.get('y', 0) for point in data]
            else:
                values = data
            
            stats = {
                'count': len(values),
                'min': min(values) if values else 0,
                'max': max(values) if values else 0,
                'mean': sum(values) / len(values) if values else 0,
                'total': sum(values) if values else 0
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating chart stats: {e}")
            return {} 