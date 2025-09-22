import streamlit as st
import requests
import json
import pandas as pd
from typing import Dict, Any, List
import re
from urllib.parse import urlparse
import time

# Page configuration
st.set_page_config(
    page_title="RepoPilot - Repository Analysis Tool",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for improved UI
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .section-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
        border: 1px solid #e0e0e0;
        transition: all 0.3s ease;
    }
    
    .section-card:hover {
        box-shadow: 0 4px 20px rgba(0,0,0,0.12);
        transform: translateY(-2px);
    }
    
    .metric-container {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .search-box {
        background: #f8f9fa;
        border: 2px solid #e9ecef;
        border-radius: 8px;
        padding: 0.5rem;
        transition: border-color 0.3s ease;
    }
    
    .search-box:focus {
        border-color: #667eea;
        outline: none;
    }
    
    .json-tree {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        max-height: 600px;
        overflow-y: auto;
    }
    
    .diagram-container {
        background: white;
        border: 2px dashed #667eea;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }
    
    .diagram-container:hover {
        background: #f8f9ff;
        border-color: #764ba2;
    }
    
    .status-success {
        color: #28a745;
        background: #d4edda;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        border-left: 4px solid #28a745;
    }
    
    .status-error {
        color: #dc3545;
        background: #f8d7da;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        border-left: 4px solid #dc3545;
    }
    
    .status-info {
        color: #17a2b8;
        background: #d1ecf1;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        border-left: 4px solid #17a2b8;
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
</style>
""", unsafe_allow_html=True)

class RepoPilotApp:
    def __init__(self):
        self.api_base_url = "http://localhost:8000"  # Adjust as needed
        self.init_session_state()
    
    def init_session_state(self):
        """Initialize session state variables"""
        if 'analysis_results' not in st.session_state:
            st.session_state.analysis_results = None
        if 'search_query' not in st.session_state:
            st.session_state.search_query = ""
        if 'processing' not in st.session_state:
            st.session_state.processing = False
    
    def validate_github_url(self, url: str) -> bool:
        """Validate if the provided URL is a valid GitHub repository URL"""
        try:
            parsed = urlparse(url)
            return (
                parsed.netloc == 'github.com' and
                len(parsed.path.strip('/').split('/')) >= 2 and
                not parsed.path.endswith('.git')
            )
        except:
            return False
    
    def extract_repo_info(self, url: str) -> Dict[str, str]:
        """Extract owner and repo name from GitHub URL"""
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            return {
                'owner': path_parts[0],
                'repo': path_parts[1],
                'full_name': f"{path_parts[0]}/{path_parts[1]}"
            }
        except:
            return {}
    
    def create_gitdiagram_url(self, github_url: str) -> str:
        """Convert GitHub URL to GitDiagram URL"""
        return github_url.replace('github.com', 'gitdiagram.com')
    
    def analyze_repository(self, url: str) -> Dict[str, Any]:
        """Send repository URL to FastAPI analyze endpoint"""
        try:
            payload = {"repository_url": url}
            response = requests.post(
                f"{self.api_base_url}/analyze",
                json=payload,
                timeout=300  # 5 minute timeout for large repos
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"API Error: {str(e)}")
            return None
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")
            return None
    
    def filter_json_data(self, data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Filter JSON data based on search query"""
        if not query:
            return data
        
        query = query.lower()
        filtered_data = {}
        
        for key, value in data.items():
            if isinstance(value, dict):
                filtered_value = self.filter_json_data(value, query)
                if filtered_value or query in key.lower():
                    filtered_data[key] = filtered_value
            elif isinstance(value, list):
                filtered_list = []
                for item in value:
                    if isinstance(item, str) and query in item.lower():
                        filtered_list.append(item)
                    elif isinstance(item, dict):
                        filtered_item = self.filter_json_data(item, query)
                        if filtered_item:
                            filtered_list.append(filtered_item)
                if filtered_list:
                    filtered_data[key] = filtered_list
            elif isinstance(value, str) and (query in value.lower() or query in key.lower()):
                filtered_data[key] = value
        
        return filtered_data
    
    def render_json_tree(self, data: Dict[str, Any], level: int = 0) -> None:
        """Render JSON data as an expandable tree structure"""
        for key, value in data.items():
            if isinstance(value, dict):
                with st.expander(f"📁 {key} ({len(value)} items)", expanded=level < 2):
                    self.render_json_tree(value, level + 1)
            elif isinstance(value, list):
                with st.expander(f"📋 {key} ({len(value)} items)", expanded=level < 1):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            st.write(f"**Item {i+1}:**")
                            self.render_json_tree(item, level + 2)
                        else:
                            st.write(f"- {item}")
            else:
                st.write(f"**{key}:** {value}")
    
    def render_metrics(self, data: Dict[str, Any]) -> None:
        """Render key metrics from the analysis"""
        col1, col2, col3, col4 = st.columns(4)
        
        # Extract metrics
        total_files = len(data.get('files', []))
        total_functions = sum(len(file.get('functions', [])) for file in data.get('files', []))
        total_imports = sum(len(file.get('imports', [])) for file in data.get('files', []))
        languages = set()
        
        for file in data.get('files', []):
            if 'language' in file:
                languages.add(file['language'])
        
        with col1:
            st.metric("📁 Files", total_files)
        
        with col2:
            st.metric("🔧 Functions", total_functions)
        
        with col3:
            st.metric("📦 Imports", total_imports)
        
        with col4:
            st.metric("💻 Languages", len(languages))
    
    def render_header(self):
        """Render the main header"""
        st.markdown("""
        <div class="main-header">
            <h1>🚁 RepoPilot</h1>
            <p>Intelligent Repository Analysis & Visualization</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_sidebar(self):
        """Render the sidebar with controls"""
        st.sidebar.title("🎛️ Controls")
        
        # Repository input section
        st.sidebar.subheader("Repository Input")
        
        input_type = st.sidebar.radio(
            "Choose input method:",
            ["GitHub URL", "Local Path"]
        )
        
        if input_type == "GitHub URL":
            repo_url = st.sidebar.text_input(
                "Enter GitHub Repository URL:",
                placeholder="https://github.com/owner/repository",
                help="Paste the full GitHub repository URL"
            )
            
            if repo_url:
                if self.validate_github_url(repo_url):
                    st.sidebar.success("✅ Valid GitHub URL")
                    repo_info = self.extract_repo_info(repo_url)
                    st.sidebar.info(f"Repository: {repo_info.get('full_name', 'Unknown')}")
                else:
                    st.sidebar.error("❌ Invalid GitHub URL")
                    repo_url = None
        else:
            repo_url = st.sidebar.text_input(
                "Enter Local Repository Path:",
                placeholder="/path/to/repository",
                help="Provide the full path to your local repository"
            )
        
        # Analysis button
        analyze_button = st.sidebar.button(
            "🔍 Analyze Repository",
            disabled=not repo_url or st.session_state.processing,
            use_container_width=True
        )
        
        # GitDiagram section
        if repo_url and self.validate_github_url(repo_url):
            st.sidebar.subheader("📊 GitDiagram")
            gitdiagram_url = self.create_gitdiagram_url(repo_url)
            st.sidebar.markdown(
                f"[🎨 Generate Architecture Diagram]({gitdiagram_url})",
                help="Click to generate an interactive system architecture diagram"
            )
        
        # Search section
        if st.session_state.analysis_results:
            st.sidebar.subheader("🔍 Search & Filter")
            search_query = st.sidebar.text_input(
                "Search files, functions, or content:",
                value=st.session_state.search_query,
                placeholder="Enter search term...",
                help="Filter the JSON tree by typing keywords"
            )
            st.session_state.search_query = search_query
        
        return repo_url, analyze_button
    
    def run(self):
        """Main application runner"""
        self.render_header()
        
        # Sidebar
        repo_url, analyze_button = self.render_sidebar()
        
        # Main content area
        if analyze_button and repo_url:
            st.session_state.processing = True
            
            # Show progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.markdown('<div class="status-info">🚀 Starting analysis...</div>', unsafe_allow_html=True)
            progress_bar.progress(20)
            
            # Analyze repository
            status_text.markdown('<div class="status-info">🔍 Analyzing repository structure...</div>', unsafe_allow_html=True)
            progress_bar.progress(60)
            
            results = self.analyze_repository(repo_url)
            
            if results:
                progress_bar.progress(100)
                status_text.markdown('<div class="status-success">✅ Analysis completed successfully!</div>', unsafe_allow_html=True)
                time.sleep(1)
                st.session_state.analysis_results = results
                progress_bar.empty()
                status_text.empty()
            else:
                status_text.markdown('<div class="status-error">❌ Analysis failed. Please check your URL and try again.</div>', unsafe_allow_html=True)
                progress_bar.empty()
            
            st.session_state.processing = False
        
        # Display results
        if st.session_state.analysis_results:
            self.display_results()
        else:
            self.display_welcome_message()
    
    def display_welcome_message(self):
        """Display welcome message and instructions"""
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("""
            ### How to Use RepoPilot
            
            1. **Enter Repository URL**: Paste a GitHub repository URL in the sidebar
            2. **Analyze**: Click the "Analyze Repository" button
            3. **Explore**: Browse the JSON structure and read the guided tour
            4. **Visualize**: Use GitDiagram for interactive architecture diagrams
            
            
            ### GitDiagram Integration
            
            Replace 'github.com' with 'gitdiagram.com' in any GitHub URL to generate:
            - Interactive system architecture diagrams
            - Clickable nodes for file navigation
            - Fast generation powered by Claude 3.5 Sonnet
            - Customizable diagram views
            """)
    
    def display_results(self):
        """Display analysis results in two main sections"""
        results = st.session_state.analysis_results
        
        # Metrics overview
        st.subheader("📊 Repository Overview")
        self.render_metrics(results)
        
        # Main content tabs
        tab1, tab2 = st.tabs(["🗂️ Repository Structure", "📖 Guided Tour"])
        
        with tab1:
            self.display_json_viewer(results)
        
        with tab2:
            self.display_markdown_viewer(results)
    
    def display_json_viewer(self, results: Dict[str, Any]):
        """Display the JSON structure viewer"""
        st.subheader("🗂️ Repository Structure")
        
        # Filter data based on search query
        filtered_data = self.filter_json_data(results, st.session_state.search_query)
        
        if not filtered_data and st.session_state.search_query:
            st.warning(f"No results found for '{st.session_state.search_query}'")
            st.info("Try different keywords or clear the search to see all results.")
        else:
            # Display filtered results
            if st.session_state.search_query:
                st.info(f"Showing results for: '{st.session_state.search_query}'")
            
            # Render the JSON tree
            self.render_json_tree(filtered_data)
            
            # Raw JSON expander
            with st.expander("🔧 Raw JSON Data", expanded=False):
                st.json(filtered_data if st.session_state.search_query else results)
    
    def display_markdown_viewer(self, results: Dict[str, Any]):
        """Display the markdown guided tour"""
        st.subheader("📖 Guided Repository Tour")
        
        # Check if guided tour exists
        tour_content = results.get('guided_tour', results.get('repotour.md', ''))
        
        if tour_content:
            # Render markdown content
            st.markdown(tour_content)
        else:
            st.warning("No guided tour available for this repository.")
            st.info("The guided tour is generated automatically during analysis and provides insights into the repository structure and key components.")
            
            # Show alternative content if available
            if 'summary' in results:
                st.subheader("📋 Repository Summary")
                st.write(results['summary'])

# Initialize and run the app
def main():
    app = RepoPilotApp()
    app.run()

if __name__ == "__main__":
    main()
