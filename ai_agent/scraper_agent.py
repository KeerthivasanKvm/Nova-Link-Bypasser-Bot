"""
Web Scraping AI Agent
=====================
AI-powered agent for intelligent web scraping and bypass.
Based on: https://github.com/Shubhamsaboo/awesome-llm-apps
"""

import json
import re
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from openai import AsyncOpenAI

from config import ai_config
from utils.logger import get_logger

logger = get_logger(__name__)


class WebScrapingAgent:
    """
    AI-powered web scraping agent.
    Uses LLM to analyze pages and extract information intelligently.
    """
    
    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        if ai_config.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=ai_config.OPENAI_API_KEY)
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    async def analyze_page(self, url: str, html_content: str) -> Dict[str, Any]:
        """
        Analyze a webpage using AI.
        
        Args:
            url: Page URL
            html_content: HTML content
            
        Returns:
            Analysis result
        """
        if not self.client:
            return {'error': 'AI not configured'}
        
        try:
            # Truncate content if too long
            max_length = 8000
            if len(html_content) > max_length:
                html_content = html_content[:max_length] + "..."
            
            system_prompt = """You are an expert web scraping and bypass specialist AI agent.

Your task is to analyze HTML content from link shortener/protected pages and extract the final destination URL.

Analyze the provided HTML and:
1. Identify the type of protection (countdown, CAPTCHA, hidden elements, JavaScript obfuscation, etc.)
2. Look for any URLs in the HTML, JavaScript, or meta tags
3. Identify patterns that reveal the destination URL
4. Provide extraction strategy if URL not directly visible

Respond in JSON format:
{
    "success": boolean,
    "url": "destination URL if found",
    "confidence": 0-1,
    "protection_type": "type of protection detected",
    "reasoning": "explanation of findings",
    "extraction_strategy": "strategy to extract URL if not directly found",
    "selectors": ["CSS selectors to try"],
    "scripts": ["JavaScript patterns to look for"]
}

Be thorough and look for hidden/obfuscated content."""
            
            user_prompt = f"""URL: {url}

HTML Content:
```html
{html_content}
```

Analyze this page and extract the destination URL."""
            
            response = await self.client.chat.completions.create(
                model=ai_config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=ai_config.AI_TEMPERATURE,
                max_tokens=ai_config.AI_MAX_TOKENS,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            logger.info(f"AI analysis completed with confidence: {result.get('confidence', 0)}")
            return result
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {'error': str(e)}
    
    async def generate_bypass_strategy(
        self,
        url: str,
        page_content: str,
        previous_attempts: List[str]
    ) -> Dict[str, Any]:
        """
        Generate a bypass strategy using AI.
        
        Args:
            url: URL to bypass
            page_content: Page content
            previous_attempts: Previously tried methods
            
        Returns:
            Strategy dict
        """
        if not self.client:
            return {'error': 'AI not configured'}
        
        try:
            system_prompt = """You are a web scraping expert AI. Generate a bypass strategy for protected pages.

Respond in JSON format:
{
    "strategy": "description of approach",
    "selectors": ["CSS selectors to try"],
    "actions": [{"type": "click/wait/fill", "target": "selector", "value": "optional"}],
    "expected_result": "what to look for",
    "alternative_approaches": ["other methods to try"]
}"""
            
            user_prompt = f"""URL: {url}
Previously tried: {', '.join(previous_attempts)}

HTML Content:
```html
{page_content[:5000]}
```

Generate a bypass strategy."""
            
            response = await self.client.chat.completions.create(
                model=ai_config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Strategy generation failed: {e}")
            return {'error': str(e)}
    
    async def extract_with_strategy(
        self,
        url: str,
        strategy: Dict[str, Any]
    ) -> Optional[str]:
        """
        Extract URL using AI-generated strategy.
        
        Args:
            url: Page URL
            strategy: Bypass strategy
            
        Returns:
            Extracted URL or None
        """
        try:
            # Fetch page
            response = requests.get(url, headers=self.headers, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try selectors
            for selector in strategy.get('selectors', []):
                elements = soup.select(selector)
                for element in elements:
                    href = element.get('href')
                    if href:
                        full_url = urljoin(url, href)
                        if self._is_valid_url(full_url):
                            return full_url
            
            # Try actions (would need browser automation)
            # For now, just return None
            return None
            
        except Exception as e:
            logger.error(f"Strategy execution failed: {e}")
            return None
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False
    
    async def learn_pattern(
        self,
        domain: str,
        success_method: str,
        page_structure: str
    ) -> None:
        """
        Learn from successful bypass for future use.
        
        Args:
            domain: Domain that was bypassed
            success_method: Method that worked
            page_structure: Page structure signature
        """
        # This could be extended to store patterns
        # in a database for future similar sites
        logger.info(f"[AI Agent] Learned: {success_method} works for {domain}")
