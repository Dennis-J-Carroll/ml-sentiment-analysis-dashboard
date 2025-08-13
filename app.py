"""
Real-Time Sentiment Analysis Dashboard
Target Market: Brand monitoring, crisis management, investment sentiment
Value Prop: "Monitor brand sentiment across all platforms in real-time"
Pricing: $29-99/month SaaS model
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
from datetime import datetime, timedelta
import json
import asyncio
import time
from dataclasses import dataclass
from typing import List, Dict, Optional
import re
import random

# Mock APIs for demo (replace with real APIs in production)
class MockSentimentAnalyzer:
    def __init__(self):
        self.sentiment_words = {
            'positive': ['great', 'excellent', 'amazing', 'love', 'fantastic', 'wonderful', 'awesome', 'good', 'happy', 'satisfied'],
            'negative': ['terrible', 'awful', 'hate', 'bad', 'horrible', 'disappointing', 'worst', 'annoying', 'frustrated', 'angry'],
            'neutral': ['okay', 'fine', 'average', 'normal', 'standard', 'regular', 'typical']
        }
    
    def analyze_sentiment(self, text: str) -> Dict:
        """Simple rule-based sentiment analysis for demo"""
        text_lower = text.lower()
        
        positive_score = sum(1 for word in self.sentiment_words['positive'] if word in text_lower)
        negative_score = sum(1 for word in self.sentiment_words['negative'] if word in text_lower)
        neutral_score = sum(1 for word in self.sentiment_words['neutral'] if word in text_lower)
        
        total_score = positive_score + negative_score + neutral_score
        
        if total_score == 0:
            return {'compound': 0.0, 'sentiment': 'neutral', 'confidence': 0.5}
        
        # Calculate compound score (-1 to 1)
        compound = (positive_score - negative_score) / max(total_score, 1)
        compound += np.random.normal(0, 0.1)  # Add some noise for realism
        compound = max(-1, min(1, compound))  # Clamp to [-1, 1]
        
        # Determine sentiment label
        if compound >= 0.05:
            sentiment = 'positive'
        elif compound <= -0.05:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        confidence = min(0.95, 0.6 + abs(compound))
        
        return {
            'compound': compound,
            'sentiment': sentiment,
            'confidence': confidence
        }

class MockDataCollector:
    def __init__(self):
        self.sentiment_analyzer = MockSentimentAnalyzer()
        
        # Mock content templates
        self.tweet_templates = [
            "Just tried {brand} and it's {sentiment_word}! #{brand}",
            "{brand} customer service is {sentiment_word}. #CustomerService",
            "Can't believe how {sentiment_word} {brand} products are!",
            "{brand}'s new update is {sentiment_word}. What do you think?",
            "My experience with {brand} was {sentiment_word}. Would {recommend}.",
            "{brand} vs competitors? {brand} is {sentiment_word}!",
            "Breaking: {brand} announces new features. This is {sentiment_word}!",
            "Anyone else think {brand} is getting {sentiment_word} lately?",
            "Daily reminder that {brand} is {sentiment_word} ✨",
            "{brand} support team is {sentiment_word}. Thank you!"
        ]
        
        self.news_templates = [
            "{brand} reports {sentiment_word} quarterly earnings",
            "Market analysts say {brand} performance is {sentiment_word}",
            "{brand} stock outlook remains {sentiment_word} according to experts",
            "Industry report: {brand}'s strategy is {sentiment_word}",
            "{brand} launches new product line to {sentiment_word} reviews",
            "Consumer confidence in {brand} is {sentiment_word}, survey shows",
            "{brand} faces {sentiment_word} market conditions",
            "Investors react {sentiment_word} to {brand}'s announcement",
            "{brand}'s sustainability efforts receive {sentiment_word} feedback",
            "Competition heats up as {brand} shows {sentiment_word} growth"
        ]
        
        self.reddit_templates = [
            "DAE think {brand} is {sentiment_word}?",
            "PSA: {brand} is having a {sentiment_word} sale!",
            "Unpopular opinion: {brand} is {sentiment_word}",
            "LPT: {brand} products are {sentiment_word} for...",
            "TIFU by not knowing how {sentiment_word} {brand} is",
            "AMA request: Someone who thinks {brand} is {sentiment_word}",
            "TIL that {brand} is {sentiment_word} because...",
            "ELI5: Why is {brand} so {sentiment_word}?",
            "CMV: {brand} is the most {sentiment_word} company",
            "Discussion: Is {brand} really that {sentiment_word}?"
        ]
    
    def generate_mock_mention(self, brand: str, platform: str = 'twitter') -> Dict:
        """Generate a realistic mock mention for demo purposes"""
        templates = {
            'twitter': self.tweet_templates,
            'news': self.news_templates,
            'reddit': self.reddit_templates
        }
        
        template = np.random.choice(templates.get(platform, self.tweet_templates))
        
        # Choose sentiment and corresponding words
        sentiment_type = np.random.choice(['positive', 'negative', 'neutral'], p=[0.4, 0.3, 0.3])
        sentiment_word = np.random.choice(self.sentiment_analyzer.sentiment_words[sentiment_type])
        
        recommend_words = {
            'positive': 'definitely recommend it',
            'negative': 'not recommend it', 
            'neutral': 'maybe recommend it'
        }
        
        content = template.format(
            brand=brand,
            sentiment_word=sentiment_word,
            recommend=recommend_words.get(sentiment_type, 'maybe recommend it')
        )
        
        # Analyze sentiment
        sentiment_result = self.sentiment_analyzer.analyze_sentiment(content)
        
        # Generate realistic metadata
        engagement = max(1, int(np.random.exponential(10)))
        if sentiment_result['sentiment'] == 'positive':
            engagement *= np.random.uniform(1.5, 3.0)  # Positive content gets more engagement
        
        return {
            'content': content,
            'platform': platform,
            'author': f"user_{np.random.randint(1000, 9999)}",
            'timestamp': datetime.now() - timedelta(minutes=np.random.randint(0, 1440)),
            'sentiment_score': sentiment_result['compound'],
            'sentiment_label': sentiment_result['sentiment'],
            'confidence': sentiment_result['confidence'],
            'engagement': int(engagement),
            'reach': int(engagement * np.random.uniform(3, 15)),
            'location': np.random.choice(['US', 'UK', 'CA', 'AU', 'DE', 'FR', 'JP'])
        }

@dataclass
class SentimentAlert:
    alert_type: str
    severity: str
    message: str
    timestamp: datetime
    brand: str
    threshold_value: float
    current_value: float

class SentimentAnalysisPlatform:
    def __init__(self, db_path="sentiment_data.db"):
        self.db_path = db_path
        self.data_collector = MockDataCollector()
        self.init_database()
        
        # Alert thresholds
        self.alert_thresholds = {
            'sentiment_drop': -0.3,  # Alert if sentiment drops below -0.3
            'volume_spike': 200,     # Alert if mention volume exceeds 200% of average
            'negative_spike': 0.4    # Alert if negative sentiment exceeds 40%
        }
    
    def init_database(self):
        """Initialize database for storing sentiment data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand TEXT NOT NULL,
                content TEXT NOT NULL,
                platform TEXT NOT NULL,
                author TEXT,
                timestamp TEXT NOT NULL,
                sentiment_score REAL NOT NULL,
                sentiment_label TEXT NOT NULL,
                confidence REAL,
                engagement INTEGER DEFAULT 0,
                reach INTEGER DEFAULT 0,
                location TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sentiment_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                threshold_value REAL,
                current_value REAL,
                timestamp TEXT NOT NULL,
                acknowledged BOOLEAN DEFAULT FALSE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS brand_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand_name TEXT NOT NULL UNIQUE,
                tracking_keywords TEXT,
                created_at TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_brand_tracking(self, brand_name: str, keywords: List[str] = None):
        """Add a brand for sentiment tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        keywords_json = json.dumps(keywords if keywords else [brand_name])
        
        cursor.execute('''
            INSERT OR REPLACE INTO brand_tracking (brand_name, tracking_keywords, created_at, is_active)
            VALUES (?, ?, ?, ?)
        ''', (brand_name, keywords_json, datetime.now().isoformat(), True))
        
        conn.commit()
        conn.close()
    
    def collect_mentions(self, brand: str, count: int = 50) -> List[Dict]:
        """Collect mentions for a brand (mock data for demo)"""
        mentions = []
        
        platforms = ['twitter', 'news', 'reddit']
        platform_weights = [0.6, 0.2, 0.2]  # Twitter is more common
        
        for _ in range(count):
            platform = np.random.choice(platforms, p=platform_weights)
            mention = self.data_collector.generate_mock_mention(brand, platform)
            mentions.append(mention)
        
        return mentions
    
    def store_mentions(self, brand: str, mentions: List[Dict]):
        """Store mentions in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for mention in mentions:
            cursor.execute('''
                INSERT INTO mentions 
                (brand, content, platform, author, timestamp, sentiment_score, 
                 sentiment_label, confidence, engagement, reach, location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                brand, mention['content'], mention['platform'], mention['author'],
                mention['timestamp'].isoformat(), mention['sentiment_score'],
                mention['sentiment_label'], mention['confidence'], 
                mention['engagement'], mention['reach'], mention['location']
            ))
        
        conn.commit()
        conn.close()
    
    def get_sentiment_summary(self, brand: str, hours: int = 24) -> Dict:
        """Get sentiment summary for the last N hours"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT 
                AVG(sentiment_score) as avg_sentiment,
                COUNT(*) as total_mentions,
                SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive_count,
                SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative_count,
                SUM(CASE WHEN sentiment_label = 'neutral' THEN 1 ELSE 0 END) as neutral_count,
                AVG(engagement) as avg_engagement,
                SUM(reach) as total_reach
            FROM mentions 
            WHERE brand = ? AND timestamp > datetime('now', '-{} hours')
        '''.format(hours)
        
        result = pd.read_sql_query(query, conn, params=(brand,))
        conn.close()
        
        if result.iloc[0]['total_mentions'] == 0:
            return {
                'avg_sentiment': 0.0,
                'total_mentions': 0,
                'positive_pct': 0,
                'negative_pct': 0,
                'neutral_pct': 0,
                'avg_engagement': 0,
                'total_reach': 0
            }
        
        row = result.iloc[0]
        total = row['total_mentions']
        
        return {
            'avg_sentiment': row['avg_sentiment'] or 0,
            'total_mentions': int(total),
            'positive_pct': (row['positive_count'] / total) * 100,
            'negative_pct': (row['negative_count'] / total) * 100, 
            'neutral_pct': (row['neutral_count'] / total) * 100,
            'avg_engagement': row['avg_engagement'] or 0,
            'total_reach': int(row['total_reach'] or 0)
        }
    
    def check_alerts(self, brand: str) -> List[SentimentAlert]:
        """Check for sentiment alerts"""
        summary = self.get_sentiment_summary(brand, hours=4)  # Last 4 hours
        alerts = []
        
        # Sentiment drop alert
        if summary['avg_sentiment'] < self.alert_thresholds['sentiment_drop']:
            alerts.append(SentimentAlert(
                alert_type='sentiment_drop',
                severity='high',
                message=f"Sentiment for {brand} dropped to {summary['avg_sentiment']:.2f}",
                timestamp=datetime.now(),
                brand=brand,
                threshold_value=self.alert_thresholds['sentiment_drop'],
                current_value=summary['avg_sentiment']
            ))
        
        # Negative sentiment spike
        if summary['negative_pct'] > (self.alert_thresholds['negative_spike'] * 100):
            alerts.append(SentimentAlert(
                alert_type='negative_spike',
                severity='medium',
                message=f"Negative sentiment for {brand} spiked to {summary['negative_pct']:.1f}%",
                timestamp=datetime.now(),
                brand=brand,
                threshold_value=self.alert_thresholds['negative_spike'],
                current_value=summary['negative_pct'] / 100
            ))
        
        return alerts

class SentimentDashboardApp:
    def __init__(self):
        self.platform = SentimentAnalysisPlatform()
        self.setup_page_config()
    
    def setup_page_config(self):
        st.set_page_config(
            page_title="Sentiment Analysis Dashboard",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def sidebar_controls(self):
        """Sidebar controls for dashboard"""
        st.sidebar.title("Dashboard Controls")
        
        # Brand management
        st.sidebar.subheader("🏢 Brand Tracking")
        
        # Add new brand
        new_brand = st.sidebar.text_input("Add Brand to Track:")
        if st.sidebar.button("➕ Add Brand") and new_brand:
            self.platform.add_brand_tracking(new_brand.strip())
            st.sidebar.success(f"Added {new_brand} to tracking!")
        
        # Get tracked brands
        conn = sqlite3.connect(self.platform.db_path)
        brands_df = pd.read_sql_query("SELECT brand_name FROM brand_tracking WHERE is_active = 1", conn)
        conn.close()
        
        if len(brands_df) == 0:
            # Add some demo brands
            demo_brands = ["Apple", "Google", "Tesla", "Amazon", "Microsoft"]
            for brand in demo_brands:
                self.platform.add_brand_tracking(brand)
            brands_df = pd.DataFrame({'brand_name': demo_brands})
        
        selected_brand = st.sidebar.selectbox("Select Brand:", brands_df['brand_name'].tolist())
        
        # Time range
        time_ranges = {
            "Last Hour": 1,
            "Last 4 Hours": 4,
            "Last 24 Hours": 24,
            "Last 3 Days": 72,
            "Last Week": 168
        }
        selected_time_range = st.sidebar.selectbox("Time Range:", list(time_ranges.keys()))
        hours = time_ranges[selected_time_range]
        
        # Data refresh
        if st.sidebar.button("🔄 Collect New Mentions"):
            with st.spinner(f"Collecting mentions for {selected_brand}..."):
                mentions = self.platform.collect_mentions(selected_brand, count=100)
                self.platform.store_mentions(selected_brand, mentions)
            st.sidebar.success("Data refreshed!")
        
        return selected_brand, hours
    
    def create_sentiment_gauge(self, sentiment_score: float):
        """Create sentiment gauge chart"""
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=sentiment_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Overall Sentiment"},
            delta={'reference': 0},
            gauge={
                'axis': {'range': [-1, 1]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [-1, -0.5], 'color': "red"},
                    {'range': [-0.5, 0.5], 'color': "yellow"},
                    {'range': [0.5, 1], 'color': "green"}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 4},
                    'thickness': 0.75,
                    'value': sentiment_score
                }
            }
        ))
        fig.update_layout(height=300)
        return fig
    
    def sentiment_trend_chart(self, brand: str, hours: int):
        """Create sentiment trend over time"""
        conn = sqlite3.connect(self.platform.db_path)
        
        query = '''
            SELECT 
                datetime(timestamp) as datetime,
                AVG(sentiment_score) as avg_sentiment,
                COUNT(*) as mention_count
            FROM mentions 
            WHERE brand = ? AND timestamp > datetime('now', '-{} hours')
            GROUP BY datetime(timestamp, 'start of hour')
            ORDER BY datetime
        '''.format(hours)
        
        trend_data = pd.read_sql_query(query, conn, params=(brand,))
        conn.close()
        
        if len(trend_data) == 0:
            st.warning("No data available for the selected time range")
            return
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Sentiment Score Over Time', 'Mention Volume'),
            specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
        )
        
        # Sentiment trend
        fig.add_trace(
            go.Scatter(x=trend_data['datetime'], y=trend_data['avg_sentiment'],
                      mode='lines+markers', name='Sentiment Score',
                      line=dict(color='blue', width=3)),
            row=1, col=1
        )
        
        # Volume trend  
        fig.add_trace(
            go.Bar(x=trend_data['datetime'], y=trend_data['mention_count'],
                  name='Mentions', marker_color='lightblue'),
            row=2, col=1
        )
        
        fig.update_layout(height=500, showlegend=False)
        fig.update_yaxes(title_text="Sentiment Score", row=1, col=1)
        fig.update_yaxes(title_text="Mention Count", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
    
    def platform_breakdown_chart(self, brand: str, hours: int):
        """Platform breakdown visualization"""
        conn = sqlite3.connect(self.platform.db_path)
        
        query = '''
            SELECT 
                platform,
                AVG(sentiment_score) as avg_sentiment,
                COUNT(*) as mention_count,
                SUM(engagement) as total_engagement
            FROM mentions 
            WHERE brand = ? AND timestamp > datetime('now', '-{} hours')
            GROUP BY platform
        '''.format(hours)
        
        platform_data = pd.read_sql_query(query, conn, params=(brand,))
        conn.close()
        
        if len(platform_data) == 0:
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Platform mention distribution
            fig_pie = px.pie(platform_data, values='mention_count', names='platform',
                           title='Mentions by Platform')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Sentiment by platform
            fig_bar = px.bar(platform_data, x='platform', y='avg_sentiment',
                           title='Average Sentiment by Platform',
                           color='avg_sentiment',
                           color_continuous_scale='RdYlGn',
                           color_continuous_midpoint=0)
            st.plotly_chart(fig_bar, use_container_width=True)
    
    def recent_mentions_table(self, brand: str, limit: int = 10):
        """Show recent mentions"""
        conn = sqlite3.connect(self.platform.db_path)
        
        query = '''
            SELECT content, platform, sentiment_label, sentiment_score, 
                   engagement, timestamp
            FROM mentions 
            WHERE brand = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        '''
        
        recent = pd.read_sql_query(query, conn, params=(brand, limit))
        conn.close()
        
        if len(recent) > 0:
            # Format for display
            recent['timestamp'] = pd.to_datetime(recent['timestamp']).dt.strftime('%H:%M:%S')
            recent['sentiment_score'] = recent['sentiment_score'].round(3)
            
            # Color code sentiment
            def color_sentiment(val):
                if val == 'positive':
                    return 'background-color: #d4edda'
                elif val == 'negative':
                    return 'background-color: #f8d7da'
                else:
                    return 'background-color: #fff3cd'
            
            styled_df = recent.style.applymap(color_sentiment, subset=['sentiment_label'])
            st.dataframe(styled_df, use_container_width=True)
    
    def alerts_section(self, brand: str):
        """Display alerts and monitoring"""
        alerts = self.platform.check_alerts(brand)
        
        if alerts:
            st.subheader("🚨 Active Alerts")
            
            for alert in alerts:
                severity_colors = {
                    'high': 'error',
                    'medium': 'warning', 
                    'low': 'info'
                }
                
                alert_color = severity_colors.get(alert.severity, 'info')
                
                if alert_color == 'error':
                    st.error(f"🔴 **{alert.alert_type.upper()}**: {alert.message}")
                elif alert_color == 'warning':
                    st.warning(f"🟡 **{alert.alert_type.upper()}**: {alert.message}")
                else:
                    st.info(f"🔵 **{alert.alert_type.upper()}**: {alert.message}")
        else:
            st.success("✅ No active alerts")
    
    def competitor_comparison(self, primary_brand: str):
        """Compare sentiment with competitors"""
        st.subheader("🥊 Competitor Comparison")
        
        # Get all tracked brands for comparison
        conn = sqlite3.connect(self.platform.db_path)
        brands_df = pd.read_sql_query("SELECT brand_name FROM brand_tracking WHERE is_active = 1", conn)
        
        comparison_data = []
        for brand in brands_df['brand_name']:
            summary = self.platform.get_sentiment_summary(brand, hours=24)
            comparison_data.append({
                'Brand': brand,
                'Avg Sentiment': summary['avg_sentiment'],
                'Total Mentions': summary['total_mentions'],
                'Positive %': summary['positive_pct'],
                'Negative %': summary['negative_pct']
            })
        
        conn.close()
        
        if comparison_data:
            comp_df = pd.DataFrame(comparison_data)
            
            # Highlight primary brand
            def highlight_primary(row):
                if row.name == primary_brand or row['Brand'] == primary_brand:
                    return ['background-color: yellow'] * len(row)
                return [''] * len(row)
            
            st.dataframe(
                comp_df.style.apply(lambda x: highlight_primary(x), axis=1),
                use_container_width=True
            )
            
            # Visualization
            fig = px.scatter(comp_df, x='Total Mentions', y='Avg Sentiment', 
                           size='Positive %', color='Brand',
                           title='Brand Sentiment vs Volume',
                           hover_data=['Negative %'])
            st.plotly_chart(fig, use_container_width=True)
    
    def run_dashboard(self):
        """Main dashboard interface"""
        st.title("📊 Real-Time Sentiment Analysis Dashboard")
        st.markdown("*Monitor brand sentiment across all platforms in real-time*")
        
        # Sidebar controls
        selected_brand, hours = self.sidebar_controls()
        
        if not selected_brand:
            st.warning("Please add and select a brand to track.")
            return
        
        # Get current sentiment summary
        summary = self.platform.get_sentiment_summary(selected_brand, hours)
        
        # Main metrics row
        st.markdown("---")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Overall Sentiment", 
                f"{summary['avg_sentiment']:.2f}",
                delta=f"{np.random.uniform(-0.1, 0.1):.2f}"  # Mock delta
            )
        
        with col2:
            st.metric(
                "Total Mentions", 
                f"{summary['total_mentions']:,}",
                delta=f"+{np.random.randint(5, 25)}"
            )
        
        with col3:
            st.metric(
                "Positive %", 
                f"{summary['positive_pct']:.1f}%",
                delta=f"{np.random.uniform(-5, 5):.1f}%"
            )
        
        with col4:
            st.metric(
                "Negative %", 
                f"{summary['negative_pct']:.1f}%", 
                delta=f"{np.random.uniform(-3, 3):.1f}%"
            )
        
        with col5:
            st.metric(
                "Total Reach", 
                f"{summary['total_reach']:,}",
                delta=f"+{np.random.randint(100, 1000):,}"
            )
        
        # Alerts section
        st.markdown("---")
        self.alerts_section(selected_brand)
        
        # Main charts
        st.markdown("---")
        
        # Sentiment gauge and trends
        col1, col2 = st.columns([1, 2])
        
        with col1:
            gauge_fig = self.create_sentiment_gauge(summary['avg_sentiment'])
            st.plotly_chart(gauge_fig, use_container_width=True)
        
        with col2:
            st.subheader("📈 Sentiment Trends")
            self.sentiment_trend_chart(selected_brand, hours)
        
        # Platform breakdown
        st.markdown("---")
        st.subheader("📱 Platform Analysis")
        self.platform_breakdown_chart(selected_brand, hours)
        
        # Recent mentions
        st.markdown("---")
        st.subheader("💬 Recent Mentions")
        self.recent_mentions_table(selected_brand)
        
        # Competitor comparison
        st.markdown("---")
        self.competitor_comparison(selected_brand)

if __name__ == "__main__":
    app = SentimentDashboardApp()
    app.run_dashboard()