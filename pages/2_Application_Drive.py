
import streamlit as st
from google.cloud import bigquery
import os
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2 import service_account




credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)


st.set_page_config(page_title="Space Report", layout="wide")



st.markdown("""
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
    <style>
        .registration-card {
            background: #0f1924;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            padding: 3rem;
            max-width: 95%;
            margin: 2rem auto;
        }
        .metric-card {
            background: linear-gradient(135deg, #1e3a5f 0%, #2d5a8c 100%);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }
        .metric-icon {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
        .section-header {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin: 1.5rem 0 1rem 0;
        }
        .section-header i {
            font-size: 1.5rem;
        }
        .drive-card {
            background: #1e293b;
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 0.5rem;
        }
        .status-healthy { background-color: #51cf66; }
        .status-warning { background-color: #ffd43b; }
        .status-critical { background-color: #ff8787; }
        .status-emergency { background-color: #ff6b6b; }
        .progress-bar {
            background: #0f172a;
            border-radius: 10px;
            height: 20px;
            overflow: hidden;
            margin-top: 0.5rem;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #3b82f6, #8b5cf6);
            transition: width 0.3s ease;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="registration-card">
        <div style="text-align:center">
            <h1 style="color:white"><i class="bi bi-hdd-stack"></i> Database Disk Space Analysis Report</h1>
            <p style="color: #adb5bd; margin-top: 0.5rem;">Comprehensive storage monitoring and analytics</p>
        </div>
    </div>
""", unsafe_allow_html=True)



# -------------------------------
# Database Functions
# -------------------------------
@st.cache_data(ttl=300)
def get_space_data():
    """Fetch all space report data from BigQuery"""
    query = """
    SELECT * 
    FROM `spacereport-477420.SpaceReportDB.Application` 
    ORDER BY Date DESC
    LIMIT 1000
    """
    df = client.query(query).to_dataframe()
    
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
    
    return df

def get_date_range(df):
    """Get min and max dates from the data"""
    if df.empty:
        return date.today(), date.today()
    return df['Date'].min().date(), df['Date'].max().date()

def get_latest_stats(df, selected_drives=None):
    """Calculate latest statistics for selected drives"""
    if df.empty:
        return None
    
    if selected_drives:
        df = df[df['Drive'].isin(selected_drives)]
    
    if df.empty:
        return None
    
    latest = df.sort_values('Date', ascending=False).groupby('Drive').first().reset_index()
    
    total_size = latest['TotalSizeGB'].sum()
    total_used = latest['UsedSpaceGB'].sum()
    total_free = latest['FreeSpaceGB'].sum()
    avg_free_percent = latest['FreeSpacePercent'].mean()
    critical_drives = len(latest[latest['FreeSpacePercent'] < 10])
    
    return {
        'total_size': total_size,
        'total_used': total_used,
        'total_free': total_free,
        'avg_free_percent': avg_free_percent,
        'critical_drives': critical_drives,
        'latest_data': latest
    }

def get_status_class(free_percent):
    """Return status class based on free space percentage"""
    if free_percent < 5:
        return 'status-emergency'
    elif free_percent < 10:
        return 'status-critical'
    elif free_percent < 20:
        return 'status-warning'
    else:
        return 'status-healthy'

def get_status_text(free_percent):
    """Return status text based on free space percentage"""
    if free_percent < 5:
        return 'Emergency'
    elif free_percent < 10:
        return 'Critical'
    elif free_percent < 20:
        return 'Warning'
    else:
        return 'Healthy'

def get_border_color(free_percent):
    """Return border color based on free space percentage"""
    if free_percent < 5:
        return '#ff6b6b'
    elif free_percent < 10:
        return '#ff8787'
    elif free_percent < 20:
        return '#ffd43b'
    else:
        return '#51cf66'

def main():

    
    with st.spinner("Loading space report data..."):
        df = get_space_data()
    
    if df.empty:
        st.warning("⚠️ No space report data available.")
        return
    
    min_date, max_date = get_date_range(df)
    
    all_drives = sorted(df['Drive'].unique().tolist())
    
    st.markdown('<div class="section-header"><i class="bi bi-sliders"></i><h3>Filters</h3></div>', unsafe_allow_html=True)
    
    f1, f2, f3 = st.columns(3)
    
    with f1:
        st.markdown('<i class="bi bi-calendar-event"></i> **From Date**', unsafe_allow_html=True)
        start_date = st.date_input("From", value=min_date, label_visibility="collapsed", key="start_date")
    
    with f2:
        st.markdown('<i class="bi bi-calendar-event-fill"></i> **To Date**', unsafe_allow_html=True)
        end_date = st.date_input("To", value=max_date, label_visibility="collapsed", key="end_date")
    
    with f3:
        st.markdown('<i class="bi bi-hdd"></i> **Select Drives**', unsafe_allow_html=True)
        selected_drives = st.multiselect("Drives", all_drives, default=all_drives, label_visibility="collapsed")
    
    filtered_df = df[(df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)]
    
    if selected_drives:
        filtered_df = filtered_df[filtered_df['Drive'].isin(selected_drives)]
    
    if filtered_df.empty:
        st.warning("⚠️ No data available for selected filters.")
        return
    
    stats = get_latest_stats(filtered_df, selected_drives)
    
    if stats is None:
        st.error("Unable to calculate statistics.")
        return
    
    st.markdown('<div class="section-header"><i class="bi bi-bar-chart-line"></i><h3>Key Metrics</h3></div>', unsafe_allow_html=True)
    
    m1, m2, m3, m4, m5 = st.columns(5)
    
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon"><i class="bi bi-hdd-stack" style="color: #4dabf7;"></i></div>
            <h2 style="color: white; margin: 0;">{stats['total_size']:.2f} GB</h2>
            <p style="color: #adb5bd; margin: 0;">Total Capacity</p>
        </div>
        """, unsafe_allow_html=True)
    
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon"><i class="bi bi-pie-chart-fill" style="color: #a78bfa;"></i></div>
            <h2 style="color: white; margin: 0;">{stats['total_used']:.2f} GB</h2>
            <p style="color: #adb5bd; margin: 0;">Space Used</p>
        </div>
        """, unsafe_allow_html=True)
    
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon"><i class="bi bi-check-circle-fill" style="color: #51cf66;"></i></div>
            <h2 style="color: white; margin: 0;">{stats['total_free']:.2f} GB</h2>
            <p style="color: #adb5bd; margin: 0;">Available Space</p>
        </div>
        """, unsafe_allow_html=True)
    
    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon"><i class="bi bi-percent" style="color: #ffd43b;"></i></div>
            <h2 style="color: white; margin: 0;">{stats['avg_free_percent']:.1f}%</h2>
            <p style="color: #adb5bd; margin: 0;">Avg Free Space</p>
        </div>
        """, unsafe_allow_html=True)
    
    with m5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon"><i class="bi bi-exclamation-triangle-fill" style="color: #ff6b6b;"></i></div>
            <h2 style="color: white; margin: 0;">{stats['critical_drives']}</h2>
            <p style="color: #adb5bd; margin: 0;">Critical Drives</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Trends", 
        "💾 Drive Status", 
        "📊 Distribution", 
        "📋 Data Table"
    ])
    
    with tab1:
        st.markdown('<div class="section-header"><i class="bi bi-graph-up-arrow"></i><h3>Space Usage Trends</h3></div>', unsafe_allow_html=True)
        
        fig_trend = go.Figure()
        
        for drive in filtered_df['Drive'].unique():
            drive_data = filtered_df[filtered_df['Drive'] == drive].sort_values('Date')
            fig_trend.add_trace(go.Scatter(
                x=drive_data['Date'],
                y=drive_data['UsedSpaceGB'],
                mode='lines+markers',
                name=f'{drive} Used Space',
                hovertemplate='<b>%{fullData.name}</b><br>Date: %{x}<br>Used: %{y:.2f} GB<extra></extra>'
            ))
        
        fig_trend.update_layout(
            template="plotly_dark",
            xaxis_title="Date",
            yaxis_title="Used Space (GB)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig_trend, use_container_width=True)
        
        st.markdown('<div class="section-header"><i class="bi bi-activity"></i><h3>Free Space Percentage Trend</h3></div>', unsafe_allow_html=True)
        
        fig_free = go.Figure()
        
        for drive in filtered_df['Drive'].unique():
            drive_data = filtered_df[filtered_df['Drive'] == drive].sort_values('Date')
            fig_free.add_trace(go.Scatter(
                x=drive_data['Date'],
                y=drive_data['FreeSpacePercent'],
                mode='lines+markers',
                name=f'{drive} Free %',
                hovertemplate='<b>%{fullData.name}</b><br>Date: %{x}<br>Free: %{y:.2f}%<extra></extra>'
            ))
        
        fig_free.add_hline(y=10, line_dash="dash", line_color="red", 
                          annotation_text="Critical Threshold (10%)")
        
        fig_free.update_layout(
            template="plotly_dark",
            xaxis_title="Date",
            yaxis_title="Free Space (%)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig_free, use_container_width=True)
    
    with tab2:
        st.markdown('<div class="section-header"><i class="bi bi-hdd"></i><h3>Current Drive Status</h3></div>', unsafe_allow_html=True)
        
        latest_status = stats['latest_data']
        
        fig_bar = go.Figure()
        
        fig_bar.add_trace(go.Bar(
            name='Used Space',
            x=latest_status['Drive'],
            y=latest_status['UsedSpaceGB'],
            marker_color='#3b82f6',
            text=latest_status['UsedSpaceGB'].round(2),
            textposition='inside'
        ))
        
        fig_bar.add_trace(go.Bar(
            name='Free Space',
            x=latest_status['Drive'],
            y=latest_status['FreeSpaceGB'],
            marker_color='#10b981',
            text=latest_status['FreeSpaceGB'].round(2),
            textposition='inside'
        ))
        
        fig_bar.update_layout(
            barmode='stack',
            template="plotly_dark",
            xaxis_title="Drive",
            yaxis_title="Space (GB)",
            height=400
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)
        
        st.markdown('<div class="section-header"><i class="bi bi-list-check"></i><h4>Drive Details</h4></div>', unsafe_allow_html=True)
        
        for _, row in latest_status.iterrows():
            status_class = get_status_class(row['FreeSpacePercent'])
            status_text = get_status_text(row['FreeSpacePercent'])
            used_percent = 100 - row['FreeSpacePercent']
            border_color = get_border_color(row['FreeSpacePercent'])
            
            st.markdown(f"""
            <div style="background: #1e293b; border-radius: 10px; padding: 1.5rem; margin-bottom: 1rem; border-left: 4px solid {border_color};">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <h3 style="color: white; margin: 0;"><i class="bi bi-hdd"></i> Drive {row['Drive']}</h3>
                        <p style="color: #94a3b8; margin: 0.5rem 0 0 0;">Total: {row['TotalSizeGB']:.2f} GB</p>
                    </div>
                    <div style="text-align: right;">
                        <span class="status-dot {status_class}"></span>
                        <span style="color: white; font-weight: 600;">{status_text}</span>
                    </div>
                </div>
                <div style="margin-top: 1rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span style="color: #94a3b8;">Used: {row['UsedSpaceGB']:.2f} GB ({used_percent:.1f}%)</span>
                        <span style="color: #94a3b8;">Free: {row['FreeSpaceGB']:.2f} GB ({row['FreeSpacePercent']:.1f}%)</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {used_percent}%;"></div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with tab3:

        st.markdown('<div class="section-header"><i class="bi bi-graph-up"></i><h3>Space Growth Analysis</h3></div>', unsafe_allow_html=True)
        
        growth_data = []
        for drive in selected_drives:
            drive_df = filtered_df[filtered_df['Drive'] == drive].sort_values('Date')
            if len(drive_df) >= 2:
                first_used = drive_df.iloc[0]['UsedSpaceGB']
                last_used = drive_df.iloc[-1]['UsedSpaceGB']
                growth = last_used - first_used
                days = (drive_df.iloc[-1]['Date'] - drive_df.iloc[0]['Date']).days
                avg_daily_growth = growth / days if days > 0 else 0
                
                growth_data.append({
                    'Drive': drive,
                    'Initial': first_used,
                    'Current': last_used,
                    'Growth': growth,
                    'Avg Daily Growth': avg_daily_growth
                })
        
        if growth_data:
            growth_df = pd.DataFrame(growth_data)
            
            fig_growth = go.Figure()
            fig_growth.add_trace(go.Bar(
                x=growth_df['Drive'],
                y=growth_df['Growth'],
                marker_color=['#ff6b6b' if x > 0 else '#51cf66' for x in growth_df['Growth']],
                text=growth_df['Growth'].round(2),
                textposition='outside',
                name='Growth (GB)'
            ))
            
            fig_growth.update_layout(
                template="plotly_dark",
                xaxis_title="Drive",
                yaxis_title="Growth (GB)",
                height=400
            )
            
            st.plotly_chart(fig_growth, use_container_width=True)
    
    with tab4:
        st.markdown('<div class="section-header"><i class="bi bi-table"></i><h3>All Space Report Data</h3></div>', unsafe_allow_html=True)
        
        st.markdown('<i class="bi bi-search"></i> **Search Data**', unsafe_allow_html=True)
        search_query = st.text_input("Search", placeholder="Type to search...", label_visibility="collapsed")
        
        display_df = filtered_df.copy()
        
        if search_query:
            mask = display_df.apply(lambda row: row.astype(str).str.contains(search_query, case=False, na=False).any(), axis=1)
            display_df = display_df[mask]
        
        display_df = display_df.sort_values('Date', ascending=False)
        display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d %H:%M')
        display_df['UsedSpaceGB'] = display_df['UsedSpaceGB'].round(2)
        display_df['FreeSpaceGB'] = display_df['FreeSpaceGB'].round(2)
        display_df['TotalSizeGB'] = display_df['TotalSizeGB'].round(2)
        display_df['FreeSpacePercent'] = display_df['FreeSpacePercent'].round(2)
        
        st.dataframe(
            display_df[['Date', 'Drive', 'TotalSizeGB', 'UsedSpaceGB', 'FreeSpaceGB', 'FreeSpacePercent']],
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("""
        <div style="margin-top: 1rem; padding: 1rem; background: #1e293b; border-radius: 10px;">
            <h4 style="color: white; margin-bottom: 1rem;"><i class="bi bi-info-circle"></i> Status Legend</h4>
            <div style="display: flex; gap: 2rem; flex-wrap: wrap;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span class="status-dot status-healthy"></span>
                    <span style="color: #94a3b8;">Healthy (>20% free)</span>
                </div>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span class="status-dot status-warning"></span>
                    <span style="color: #94a3b8;">Warning (10-20% free)</span>
                </div>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span class="status-dot status-critical"></span>
                    <span style="color: #94a3b8;">Critical (5-10% free)</span>
                </div>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span class="status-dot status-emergency"></span>
                    <span style="color: #94a3b8;">Emergency (<5% free)</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()